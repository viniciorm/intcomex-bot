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
    options = ChromeOptions()
    options.add_argument("--headless=new")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
    service = ChromeService(ChromeDriverManager().install())
    return webdriver.Chrome(service=service, options=options)

def harvest_single_sku(sku, state_entry):
    """
    Intenta obtener la imagen de un SKU usando una instancia de driver (o pronto usando requests).
    Para VINI-TURBO usaremos Selenium solo si es estrictamente necesario, 
    pero por ahora lo haremos paralelo creando drivers efímeros o reusando.
    """
    # En esta versión optimizada, crearemos un pool de drivers o usaremos requests.
    # Usemos requests + BeautifulSoup por velocidad si es posible.
    headers = {"User-Agent": "Mozilla/5.0"}
    search_url = SEARCH_URL_TEMPLATE.format(sku=sku)
    
    try:
        # Intento 1: Requests (Mucho más rápido)
        resp = requests.get(search_url, headers=headers, timeout=10)
        if resp.status_code == 200:
            if sku in resp.text:
                # Extraer URL simple si existe en el HTML (patrón común)
                import re
                images = re.findall(r'https?://[^\s<>"]+?/[^\s<>"]+?\.[jJ][pP][gG]', resp.text)
                for img in images:
                    if sku in img and ("intcomex" in img or "1worldsync" in img):
                        return sku, img
        
        # Intento 2: Si falla requests, reportamos para que el orquestador sepa (o use Selenium post-paralelo)
        return sku, None
    except:
        return sku, None

def run_image_bot(skus_to_process=None, max_workers=10):
    print("\n" + "="*60)
    print("🚀 VINI-TURBO: IMAGE BOT (PARALLEL HARVEST)")
    print("="*60)
    
    state = load_state()
    if skus_to_process:
        target_skus = [sku for sku in state.keys() if sku in skus_to_process]
    else:
        target_skus = [sku for sku, data in state.items() if not data.get("tiene_imagen") and data.get("stock", 0) > 0]

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
                    print(f"    ✅ Imagen OK: {sku}")

    # Actualizar estado global
    if results:
        for sku, path in results.items():
            state[sku].update({
                "tiene_imagen": True,
                "imagenes_locales": [path],
                "subido_a_woo": False,
                "pendiente_sync_woo": True,
                "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            })
        save_state(state)
        
    print(f"\n✅ Proceso finalizado. {downloaded_count} imágenes descargadas en paralelo.")
    return downloaded_count

if __name__ == "__main__":
    run_image_bot()
