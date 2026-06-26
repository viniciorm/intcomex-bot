import os
import json
import time
import requests
import concurrent.futures
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options as ChromeOptions
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service as ChromeService

# --- Configuración ---
try:
    from credentials import INTCOMEX_USERNAME, INTCOMEX_PASSWORD
except ImportError:
    INTCOMEX_USERNAME = None
    INTCOMEX_PASSWORD = None
from sync_bot import login_intcomex

DATA_PATH = "data_activa"
DOWNLOAD_DIR = "downloads"
IMAGE_DIR = "product_images"
STATE_FILE = os.path.join(DATA_PATH, "estado_productos.json")
MAPA_IMAGENES_PATH = os.path.join(DATA_PATH, "mapa_imagenes.json")

# URL de búsqueda directa
SEARCH_URL_TEMPLATE = "https://store.intcomex.com/es-XCL/Products/ByKeyword?term=+{sku}&typeSearch=&r=true"

# Crear carpetas necesarias
os.makedirs(IMAGE_DIR, exist_ok=True)

def load_state():
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except: return {}
    return {}

def save_state(state):
    with open(STATE_FILE, 'w', encoding='utf-8') as f:
        json.dump(state, f, indent=4, ensure_ascii=False)

def download_image(url, sku):
    """Descarga una imagen y la guarda localmente."""
    if not url or not isinstance(url, str): return None
    hq_url = url.replace("M.jpg", "L.jpg").replace("S.jpg", "L.jpg")
    urls_to_try = [hq_url, url]
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"}
    
    for final_url in urls_to_try:
        try:
            if final_url.startswith("/"):
                final_url = f"https://store.intcomex.com{final_url}"
            response = requests.get(final_url, timeout=10, stream=True, headers=headers)
            if response.status_code == 200:
                ext = ".jpg"
                filename = f"{sku}_001{ext}"
                filepath = os.path.join(IMAGE_DIR, filename)
                with open(filepath, 'wb') as f:
                    for chunk in response.iter_content(1024): f.write(chunk)
                return filepath
        except: continue
    return None

def setup_driver():
    is_headless = os.getenv("HEADLESS", "true").lower() == "true"
    options = ChromeOptions()
    if is_headless:
        options.add_argument("--headless=new")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
    service = ChromeService(ChromeDriverManager().install())
    return webdriver.Chrome(service=service, options=options)

def extract_image_from_html(html, sku, current_url=""):
    """
    Extrae la URL de la imagen principal desde el HTML de la página de detalle
    o sigue el enlace de detalle si estamos en la página de resultados.
    """
    import re
    
    # 1. Comprobar si ya estamos en la página de detalle
    # Si la URL contiene /Product/Detail/ o si el html tiene la clase mainImageDiv
    is_detail = "/Product/Detail/" in current_url or "mainImageDiv" in html
    
    if is_detail:
        return parse_detail_page_image(html, sku)
        
    # 2. Si es página de resultados, buscar el enlace del detalle
    patterns = [
        r'<a[^>]+data-sku\s*=\s*[\'"]' + re.escape(sku) + r'[\'"][^>]*href\s*=\s*[\'"]([^\'"]+)[\'"]',
        r'<a[^>]+href\s*=\s*[\'"]([^\'"]+)[\'"][^>]*data-sku\s*=\s*[\'"]' + re.escape(sku) + r'[\'"]'
    ]
    
    detail_path = None
    for pattern in patterns:
        match = re.search(pattern, html, re.IGNORECASE)
        if match:
            detail_path = match.group(1)
            break
            
    if detail_path:
        detail_url = detail_path if detail_path.startswith("http") else f"https://store.intcomex.com{detail_path}"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        try:
            resp = requests.get(detail_url, headers=headers, timeout=10)
            if resp.status_code == 200:
                return parse_detail_page_image(resp.text, sku)
        except Exception as e:
            print(f"      [!] Error al obtener página de detalle {detail_url}: {e}")
            
    return None

def parse_detail_page_image(html, sku):
    """Analiza la página de detalle y obtiene el src de la imagen principal."""
    import re
    
    # Intento 1: Imagen dentro de mainImageDiv (soporta clase separada por espacios 'text center')
    match = re.search(
        r'class\s*=\s*[\'"][^\'"]*mainImageDiv[^\'"]*[\'"][^>]*>.*?<img[^>]+(?:src|data-src|data-original|data-lazy)\s*=\s*[\'"]([^\'"]+)[\'"]',
        html, re.IGNORECASE | re.DOTALL
    )
    if match:
        img_src = match.group(1)
        if "noimage" not in img_src.lower():
            return img_src
            
    # Intento 2: Imagen con clase img-products
    match = re.search(
        r'<img[^>]+class\s*=\s*[\'"][^\'"]*img-products[^\'"]*[\'"][^>]+(?:src|data-src|data-original|data-lazy)\s*=\s*[\'"]([^\'"]+)[\'"]',
        html, re.IGNORECASE
    )
    if match:
        img_src = match.group(1)
        if "noimage" not in img_src.lower():
            return img_src
            
    # Intento 3: Cualquier imagen con ruta /images/products/
    match = re.search(
        r'<img[^>]+(?:src|data-src|data-original|data-lazy)\s*=\s*[\'"]([^\'"]*?/images/products/[^\'"]+)[\'"]',
        html, re.IGNORECASE
    )
    if match:
        img_src = match.group(1)
        if "noimage" not in img_src.lower():
            return img_src
            
    # Intento 4: Si no hay nada, buscar cualquier imagen que contenga el SKU y termine en jpg/png
    match = re.search(
        r'(?:src|data-src|data-original|data-lazy)\s*=\s*[\'"]([^\'"]*?' + re.escape(sku) + r'[^\'"]*?\.(?:jpg|jpeg|png|gif|webp))[\'"]',
        html, re.IGNORECASE
    )
    if match:
        return match.group(1)
        
    return None

def harvest_single_sku(sku, state_entry):
    """
    Intenta obtener la imagen de un SKU usando una petición rápida requests.
    Sigue el flujo búsqueda -> detalle -> extracción de imagen.
    """
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    search_url = SEARCH_URL_TEMPLATE.format(sku=sku)
    
    try:
        resp = requests.get(search_url, headers=headers, timeout=10)
        if resp.status_code == 200:
            img_url = extract_image_from_html(resp.text, sku, resp.url)
            if img_url:
                # Resolver URL relativa
                if img_url.startswith("/"):
                    img_url = f"https://store.intcomex.com{img_url}"
                return sku, img_url
        return sku, None
    except Exception as e:
        print(f"      [!] Error requests para {sku}: {e}")
        return sku, None

def run_image_bot(skus_to_process=None, max_workers=10):
    print("\n" + "="*60)
    print("🚀 VINI-TURBO: IMAGE BOT (PARALLEL HARVEST)")
    print("="*60)
    
    state = load_state()
    if skus_to_process:
        target_skus = [sku for sku in state.keys() if sku in skus_to_process]
    else:
        # Procesar SKUs que no tienen imagen o tienen placeholder personalizado
        target_skus = [sku for sku, data in state.items() 
                       if (not data.get("tiene_imagen") or data.get("placeholder_personalizado")) 
                       and data.get("stock", 0) > 0]

    if not target_skus:
        print("✅ No hay SKUs pendientes de imagen.")
        return 0

    print(f"📦 Procesando {len(target_skus)} SKUs con {max_workers} hilos...")
    
    downloaded_count = 0
    results = {}

    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_sku = {executor.submit(harvest_single_sku, sku, state[sku]): sku for sku in target_skus}
        for future in concurrent.futures.as_completed(future_to_sku):
            sku, img_url = future.result()
            if img_url:
                local_path = download_image(img_url, sku)
                if local_path:
                    results[sku] = local_path
                    downloaded_count += 1
                    print(f"    ✅ Imagen OK: {sku} -> {img_url}")

    # Fallback Selenium para SKUs que fallaron (ej: por bloqueo de Cloudflare en VPS o porque requieren login)
    failed_skus = [sku for sku in target_skus if sku not in results]
    if failed_skus:
        print(f"\n    ⚠️ {len(failed_skus)} SKUs fallaron vía rápida. Intentando con Selenium (Modo Seguro con Autenticación)...")
        driver = None
        try:
            driver = setup_driver()
            if INTCOMEX_USERNAME and INTCOMEX_PASSWORD:
                print("🔑 Iniciando sesión en Intcomex para acceder a productos protegidos...")
                try:
                    login_intcomex(driver, INTCOMEX_USERNAME, INTCOMEX_PASSWORD)
                    time.sleep(3) # Esperar a que se asiente la sesión
                    print("    ✅ Sesión iniciada con éxito en Selenium.")
                except Exception as le:
                    print(f"    ⚠️ Error de inicio de sesión en Selenium: {le}. Continuando sin autenticación...")
            for sku in failed_skus:
                search_url = SEARCH_URL_TEMPLATE.format(sku=sku)
                try:
                    driver.get(search_url)
                    time.sleep(3)
                    
                    img_url = extract_image_from_html(driver.page_source, sku, driver.current_url)
                    
                    # Intentos de selector directo en driver si falla el parser HTML
                    if not img_url:
                        try:
                            el = driver.find_element(By.CSS_SELECTOR, ".mainImageDiv img")
                            img_url = el.get_attribute("src")
                        except:
                            try:
                                el = driver.find_element(By.CSS_SELECTOR, "img.img-products")
                                img_url = el.get_attribute("src")
                            except:
                                pass
                                
                    if img_url and "noimage" not in img_url.lower():
                        if img_url.startswith("/"):
                            img_url = f"https://store.intcomex.com{img_url}"
                        local_path = download_image(img_url, sku)
                        if local_path:
                            results[sku] = local_path
                            downloaded_count += 1
                            print(f"    ✅ Imagen OK (Selenium): {sku} -> {img_url}")
                        else:
                            print(f"    ❌ Error al guardar imagen: {sku}")
                    else:
                        print(f"    ❌ Imagen no encontrada en portal (Selenium): {sku}")
                except Exception as e:
                    print(f"    ❌ Error de Selenium para {sku}: {str(e)[:50]}")
        except Exception as e:
            print(f"    ❌ No se pudo iniciar Selenium: {e}")
        finally:
            if driver:
                driver.quit()

    # Actualizar estado global
    if results:
        for sku, path in results.items():
            state[sku].update({
                "tiene_imagen": True,
                "imagenes_locales": [path],
                "placeholder_personalizado": False,  # Resetear flag de placeholder
                "subido_a_woo": False,
                "pendiente_sync_woo": True,
                "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            })
        save_state(state)
        
    print(f"\n✅ Proceso finalizado. {downloaded_count} imágenes descargadas en total.")
    return downloaded_count

if __name__ == "__main__":
    run_image_bot()
