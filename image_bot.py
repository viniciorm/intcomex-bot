import os
import json
import time
import re
import requests
import pandas as pd
import glob
from pathlib import Path
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.chrome.options import Options as ChromeOptions
from webdriver_manager.chrome import ChromeDriverManager

# --- Configuración ---
DOWNLOAD_DIR = "downloads"
IMAGE_DIR = "product_images"
STATE_FILE = "estado_productos.json"
BASE_SEARCH_URL = "https://store.intcomex.com/es-XCL/Search?terms="

# Diccionario de categorías con URLs (igual que en sync_bot.py)
CATEGORY_URLS = {
    "Notebooks": "https://store.intcomex.com/es-XCL/Products/ByCategory/cpt.notebook?r=True",
    "Monitores": "https://store.intcomex.com/es-XCL/Products/ByCategory/mnt.monitor?r=True",
    "Monitores_TV": "https://store.intcomex.com/es-XCL/Products/ByCategory/mnt.tv?r=True",
    "Desktop": "https://store.intcomex.com/es-XCL/Products/ByCategory/cpt.desktop?r=True",
    "Tablets": "https://store.intcomex.com/es-XCL/Products/ByCategory/cpt.tablet?r=True",
    "Impresoras_Inkjet": "https://store.intcomex.com/es-XCL/Products/ByCategory/prt.inkjet?r=True",
    "Impresoras_Label": "https://store.intcomex.com/es-XCL/Products/ByCategory/prt.label?r=True",
    "Impresoras_Laser": "https://store.intcomex.com/es-XCL/Products/ByCategory/prt.laser?r=True",
    "Impresoras_MFP": "https://store.intcomex.com/es-XCL/Products/ByCategory/prt.mfp?r=True",
    "Scanners": "https://store.intcomex.com/es-XCL/Products/ByCategory/prt.scanner?r=True",
    "All_in_One": "https://store.intcomex.com/es-XCL/Products/ByCategory/cpt.allone?r=True"
}

# Crear carpetas necesarias
os.makedirs(IMAGE_DIR, exist_ok=True)

def load_state():
    """Carga el estado de los productos desde el archivo JSON."""
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"⚠ Error al cargar {STATE_FILE}: {e}")
            return {}
    return {}

def save_state(state):
    """Guarda el estado de los productos en el archivo JSON."""
    try:
        with open(STATE_FILE, 'w', encoding='utf-8') as f:
            json.dump(state, f, indent=4, ensure_ascii=False)
    except Exception as e:
        print(f"✗ Error al guardar {STATE_FILE}: {e}")

def get_skus_from_csvs():
    """Extrae todos los SKUs únicos de los archivos CSV con detección dinámica de encabezado."""
    skus = set()
    # MODO TEST: Solo procesar Monitores_TV.csv
    csv_files = [os.path.join(DOWNLOAD_DIR, "Monitores_TV.csv")]
    
    print(f"🔍 [TEST] Buscando SKUs en {os.path.basename(csv_files[0])}...")
    
    for file_path in csv_files:
        try:
            # 1. Detección dinámica del encabezado y enconding
            encoding = 'utf-16'
            header_row = -1
            
            try:
                with open(file_path, 'r', encoding=encoding) as f:
                    for i, line in enumerate(f):
                        if "sku" in line.lower():
                            header_row = i
                            break
            except (UnicodeDecodeError, UnicodeError):
                encoding = 'latin-1'
                with open(file_path, 'r', encoding=encoding) as f:
                    for i, line in enumerate(f):
                        if "sku" in line.lower():
                            header_row = i
                            break

            if header_row == -1:
                print(f"  ❌ Error: No se encontró la fila con 'SKU' en {os.path.basename(file_path)}")
                continue

            # 2. Carga del DataFrame con el separador correcto
            df = pd.read_csv(file_path, sep='\t', encoding=encoding, skiprows=header_row)
            
            # 3. Limpieza de nombres de columnas
            df.columns = [str(c).lower().strip() for c in df.columns]
            
            # 4. Extracción de SKUs
            if 'sku' in df.columns:
                file_skus = df['sku'].dropna().astype(str).str.strip().unique()
                # Filtrar valores vacíos
                file_skus = [s for s in file_skus if s and s.lower() != 'sku']
                skus.update(file_skus)
                print(f"  ✓ {os.path.basename(file_path)}: {len(file_skus)} SKUs encontrados.")
            else:
                print(f"  ❌ Error: No se encontró la columna SKU en {os.path.basename(file_path)}")
                print(f"     Columnas detectadas: {df.columns.tolist()}")
                
        except Exception as e:
            print(f"  ⚠ Error crítico al leer {os.path.basename(file_path)}: {e}")
                
    print(f"✅ Total de SKUs únicos para procesar: {len(skus)}")
    return list(skus)

def download_image(url, sku, sequence):
    """Descarga una imagen y la guarda con el formato SKU_001.xxx"""
    try:
        response = requests.get(url, timeout=15, stream=True)
        if response.status_code == 200:
            # Obtener extensión
            ext = ".jpg"
            if "png" in url.lower(): ext = ".png"
            elif "webp" in url.lower(): ext = ".webp"
            
            filename = f"{sku}_{str(sequence).zfill(3)}{ext}"
            filepath = os.path.join(IMAGE_DIR, filename)
            
            with open(filepath, 'wb') as f:
                for chunk in response.iter_content(1024):
                    f.write(chunk)
            
            return filepath
    except Exception as e:
        print(f"    ✗ Error descargando {url}: {e}")
    return None

def setup_driver():
    """Configura el driver de Selenium."""
    chrome_options = ChromeOptions()
    chrome_options.add_argument("--headless=new")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--window-size=1920,1080")
    # Añadir User-Agent para evitar bloqueos básicos
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
    
    service = ChromeService(ChromeDriverManager().install())
    return webdriver.Chrome(service=service, options=chrome_options)

def main():
    print("🚀 Iniciando Bot de Descarga de Imágenes (Modo Escaneo por Categoría)")
    
    state = load_state()
    # SKUs que necesitamos descargar (pendientes)
    target_skus = set(get_skus_from_csvs())
    
    # Filtrar los que ya tenemos
    skus_to_download = []
    for sku in target_skus:
        if sku in state and state[sku].get("tiene_imagen") and state[sku].get("imagenes_locales"):
            continue
        skus_to_download.append(sku)
    
    print(f"📦 SKUs pendientes de imagen: {len(skus_to_download)}")
    if not skus_to_download:
        print("✅ No hay imágenes pendientes para descargar.")
        return

    driver = setup_driver()
    
    try:
        for cat_name, cat_url in CATEGORY_URLS.items():
            print(f"\n📂 Escaneando Categoría: {cat_name}")
            driver.get(cat_url)
            
            while True:
                # Scroll progresivo para cargar lazy loading
                driver.execute_script("window.scrollTo(0, 500);")
                time.sleep(2)
                driver.execute_script("window.scrollTo(0, 1000);")
                time.sleep(2)
                
                # Encontrar todos los productos en la página actual
                all_product_anchors = driver.find_elements(By.CSS_SELECTOR, "a[data-sku]")
                print(f"  🔍 {len(all_product_anchors)} productos encontrados en esta página.")
                
                found_in_page = 0
                for anchor in all_product_anchors:
                    sku = anchor.get_attribute("data-sku")
                    if sku in target_skus:
                        # Verificar si todavía lo necesitamos
                        if sku in state and state[sku].get("tiene_imagen"):
                            continue
                            
                        print(f"    ⭐ Match encontrado: {sku}")
                        try:
                            img_el = anchor.find_element(By.TAG_NAME, "img")
                            src = img_el.get_attribute("data-src") or img_el.get_attribute("src")
                            
                            if src:
                                if src.startswith("/"):
                                    src = f"https://store.intcomex.com{src}"
                                
                                # Forzar alta resolución
                                src = src.replace("M.jpg", "L.jpg").replace("S.jpg", "L.jpg")
                                
                                local_path = download_image(src, sku, 1) # Solo una imagen por ahora en escaneo rápido
                                if local_path:
                                    state[sku] = {
                                        "tiene_imagen": True,
                                        "imagenes_locales": [local_path],
                                        "last_updated": time.strftime("%Y-%m-%d %H:%M:%S")
                                    }
                                    print(f"      ✅ Imagen descargada.")
                                    found_in_page += 1
                                    save_state(state) # Guardar a cada hallazgo para no perder progreso
                        except Exception as e:
                            print(f"      ❌ Error extrayendo imagen para {sku}: {e}")

                # Lógica de Paginación: Buscar botón "Siguiente" o "Next"
                try:
                    next_button = driver.find_elements(By.XPATH, "//a[contains(@class, 'next') or contains(text(), 'Siguiente')]")
                    if next_button and next_button[0].is_displayed():
                        print("  ⏭️ Pasando a la siguiente página...")
                        driver.execute_script("arguments[0].click();", next_button[0])
                        time.sleep(4)
                    else:
                        print(f"  🏁 Fin de categoría {cat_name}.")
                        break
                except:
                    print(f"  🏁 No se encontró botón siguiente en {cat_name}.")
                    break

    finally:
        save_state(state)
        driver.quit()
        print("\n✅ Proceso de escaneo finalizado.")

if __name__ == "__main__":
    main()

if __name__ == "__main__":
    main()
