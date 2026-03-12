import os
import json
import time
import requests
import pandas as pd
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.chrome.options import Options as ChromeOptions
from webdriver_manager.chrome import ChromeDriverManager

# --- Configuración ---
DATA_PATH = "data_activa"
DOWNLOAD_DIR = "downloads"
IMAGE_DIR = "product_images"
STATE_FILE = os.path.join(DATA_PATH, "estado_productos.json")
MAPA_IMAGENES_PATH = os.path.join(DATA_PATH, "mapa_imagenes.json")

# Diccionario de categorías con URLs (Públicas)
CATEGORY_URLS = {
    "Notebooks": "https://store.intcomex.com/es-XCL/Products/ByCategory/cpt.notebook?r=True",
    # "Monitores": "https://store.intcomex.com/es-XCL/Products/ByCategory/mnt.monitor?r=True",
    # "Monitores_TV": "https://store.intcomex.com/es-XCL/Products/ByCategory/mnt.tv?r=True",
    # "Desktop": "https://store.intcomex.com/es-XCL/Products/ByCategory/cpt.desktop?r=True",
    # "Tablets": "https://store.intcomex.com/es-XCL/Products/ByCategory/cpt.tablet?r=True",
    # "Impresoras_Inkjet": "https://store.intcomex.com/es-XCL/Products/ByCategory/prt.inkjet?r=True",
    # "Impresoras_Label": "https://store.intcomex.com/es-XCL/Products/ByCategory/prt.label?r=True",
    # "Impresoras_Laser": "https://store.intcomex.com/es-XCL/Products/ByCategory/prt.laser?r=True",
    # "Impresoras_MFP": "https://store.intcomex.com/es-XCL/Products/ByCategory/prt.mfp?r=True",
    # "Scanners": "https://store.intcomex.com/es-XCL/Products/ByCategory/prt.scanner?r=True",
    # "All_in_One": "https://store.intcomex.com/es-XCL/Products/ByCategory/cpt.allone?r=True",
    # "Discos_Duros_Internos": "https://store.intcomex.com/es-XCL/Products/ByCategory/sto.inthd?r=True",
    # "Discos_Duros_Externos": "https://store.intcomex.com/es-XCL/Products/ByCategory/sto.exthd?r=True",
    # "Discos_SSD_Internos": "https://store.intcomex.com/es-XCL/Products/ByCategory/sto.ssd?r=True",
    # "Discos_SSD_Externos": "https://store.intcomex.com/es-XCL/Products/ByCategory/sto.ssdext?r=True",
    # "Procesadores": "https://store.intcomex.com/es-XCL/Products/ByCategory/cco.cpu?r=True"
}

# Crear carpetas necesarias
os.makedirs(IMAGE_DIR, exist_ok=True)

def load_state():
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"⚠ Error al cargar {STATE_FILE}: {e}")
            return {}
    return {}

def save_state(state):
    try:
        with open(STATE_FILE, 'w', encoding='utf-8') as f:
            json.dump(state, f, indent=4, ensure_ascii=False)
    except Exception as e:
        print(f"✗ Error al guardar {STATE_FILE}: {e}")

def setup_driver(headless=True):
    """Configura el driver de Selenium para navegación pública."""
    chrome_options = ChromeOptions()
    if headless:
        chrome_options.add_argument("--headless=new")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--window-size=1920,1080")
    # User-Agent para evitar bloqueos
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
    
    service = ChromeService(ChromeDriverManager().install())
    return webdriver.Chrome(service=service, options=chrome_options)

def download_image(url, sku):
    """Descarga una imagen y la guarda localmente con reintento de calidad."""
    # Definir lista de URLs a probar (HQ primero, luego original)
    hq_url = url.replace("M.jpg", "L.jpg").replace("S.jpg", "L.jpg")
    urls_to_try = [hq_url]
    if hq_url != url:
        urls_to_try.append(url)
    
    headers = {"User-Agent": "Mozilla/5.0"}
    
    for final_url in urls_to_try:
        try:
            if final_url.startswith("/"):
                final_url = f"https://store.intcomex.com{final_url}"
                
            response = requests.get(final_url, timeout=10, stream=True, headers=headers)
            
            if response.status_code == 200:
                ext = ".jpg"
                if "png" in final_url.lower(): ext = ".png"
                elif "webp" in final_url.lower(): ext = ".webp"
                
                filename = f"{sku}_001{ext}"
                filepath = os.path.join(IMAGE_DIR, filename)
                
                with open(filepath, 'wb') as f:
                    for chunk in response.iter_content(1024):
                        f.write(chunk)
                return filepath
        except Exception:
            continue
            
    return None

def scroll_all_the_way(driver, timeout=30):
    """
    Realiza scroll dinámico hasta que no se carguen más productos.
    Ideal para activar el lazy-load de imágenes y cargar catálogos extensos.
    """
    last_height = driver.execute_script("return document.body.scrollHeight")
    start_time = time.time()
    
    while True:
        # Scroll hasta el final
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(2) # Espera a que cargue el contenido
        
        new_height = driver.execute_script("return document.body.scrollHeight")
        if new_height == last_height or (time.time() - start_time) > timeout:
            break
        last_height = new_height

SEARCH_URL_TEMPLATE = "https://store.intcomex.com/es-XCL/Products/ByKeyword?term=+{sku}&typeSearch=&r=true"

def run_image_bot(skus_to_process=None):
    """
    Ejecuta el Targeted Search Harvesting:
    Navega SKU por SKU directamente a la página de resultados/producto.
    """
    print("\n" + "="*60)
    print("🚀 IMAGE BOT: TARGETED SEARCH HARVEST (BY SKU)")
    print("="*60)
    
    state = load_state()
    if not state:
        print("✗ No se pudo cargar el estado. Abortando.")
        return 0

    # Cargar mapa existente si existe
    image_map = {}
    if os.path.exists(MAPA_IMAGENES_PATH):
        try:
            with open(MAPA_IMAGENES_PATH, 'r', encoding='utf-8') as f:
                image_map = json.load(f)
        except: pass

    # Determinar qué SKUs procesar (Orden del JSON)
    if skus_to_process:
        target_skus = [sku for sku in state.keys() if sku in skus_to_process]
    else:
        # Pendientes con stock, ignorando fallidos si se desea (o reintentando todos)
        target_skus = [sku for sku, data in state.items() 
                      if not data.get("tiene_imagen") 
                      and data.get("stock", 0) > 0]

    if not target_skus:
        print("✅ No hay SKUs con stock pendientes de imagen.")
        return 0

    print(f"📦 Procesando {len(target_skus)} SKUs mediante búsqueda directa...")
    
    driver = setup_driver(headless=True)
    downloaded_count = 0
    wait = WebDriverWait(driver, 10)

    try:
        for idx, sku in enumerate(target_skus):
            print(f"[{idx+1}/{len(target_skus)}] Buscando SKU: {sku}...")
            
            search_url = SEARCH_URL_TEMPLATE.format(sku=sku)
            driver.get(search_url)
            time.sleep(3) # Aumentado para permitir carga dinámica
            
            try:
                # Caso A: Estamos en una lista de resultados
                # Caso B: Redireccionó directamente a la ficha del producto
                
                img_src = None
                
                # 1. Intentar encontrar el producto en una lista (data-sku)
                try:
                    product_anchor = driver.find_element(By.CSS_SELECTOR, f"a[data-sku='{sku}']")
                    img_el = product_anchor.find_element(By.TAG_NAME, "img")
                    img_src = img_el.get_attribute("data-src") or img_el.get_attribute("src")
                except:
                    # 2. Intentar buscar cualquier imagen que parezca la principal si redirigió
                    # Incluimos selectores del detalle y el CDN externo
                    selectors = [
                        "img#product-main-large-image", # Detalle
                        "img.ws_images_style",           # Detalle (CDN)
                        "img.product-image",             # Genérico
                        "img[alt*='" + sku + "']",
                        ".product-view-container img",
                        "a[data-sku] img",
                        ".img-tag img"                   # Grilla
                    ]
                    for sel in selectors:
                        try:
                            els = driver.find_elements(By.CSS_SELECTOR, sel)
                            for el in els:
                                src = el.get_attribute("data-src") or el.get_attribute("src")
                                if src and "http" in src:
                                    img_src = src
                                    break
                            if img_src: break
                        except: continue

                # Validación relajada: cualquier URL válida que no sea un placeholder genérico
                # Excluir imágenes genéricas de Intcomex (ej: "noimage.jpg")
                is_valid_img = img_src and any(domain in img_src for domain in ["intcomex", "1worldsync", "cs.1worldsync", "cdn"])
                if is_valid_img and any(blocked in img_src.lower() for blocked in ["noimage", "no-image"]):
                    is_valid_img = False
                    print(f"    ⚠ Imagen ignorada por ser un placeholder genérico: {img_src}")
                
                if img_src and is_valid_img:
                    local_path = download_image(img_src, sku)
                    if local_path:
                        state[sku].update({
                            "tiene_imagen": True,
                            "imagenes_locales": [local_path],
                            "subido_a_woo": False,      # Forzar re-subida para incluir imagen
                            "pendiente_sync_woo": True, # Forzar sincronización en Fase C
                            "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        })
                        image_map[sku] = img_src
                        downloaded_count += 1
                        print(f"    ✅ Imagen encontrada: {img_src}")
                        
                        # Guardar progreso
                        save_state(state)
                        with open(MAPA_IMAGENES_PATH, 'w', encoding='utf-8') as f:
                            json.dump(image_map, f, indent=4, ensure_ascii=False)
                    else:
                        print(f"    ✗ Error al descargar imagen encontrada: {img_src}")
                else:
                    print(f"    ✗ No se encontró imagen válida para {sku}. (Detectado: {img_src if img_src else 'Nada'})")
                    state[sku]["estado_subida"] = "no_encontrado_en_busqueda"
                    save_state(state)

            except Exception as e:
                print(f"    ✗ Error procesando {sku}: {e}")

    except Exception as e:
        print(f"❌ Error crítico en Image Bot: {e}")
    finally:
        driver.quit()
        
    print(f"\n✅ Proceso de búsqueda finalizado. {downloaded_count} imágenes nuevas.")
    return downloaded_count

if __name__ == "__main__":
    run_image_bot()
