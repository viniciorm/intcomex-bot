import os
import json
import time
import requests
import concurrent.futures
from woocommerce import API
from requests.auth import HTTPBasicAuth
from woo_batch_manager import WooBatchManager

# Importar credenciales
try:
    from credentials import (
        WC_URL,
        WC_CONSUMER_KEY,
        WC_CONSUMER_SECRET,
        WP_USER,
        WP_APP_PASS
    )
except ImportError:
    print("ERROR: No se encontró credentials.py")
    exit(1)

# Configuración
DATA_PATH = "data_activa"
STATE_FILE = os.path.join(DATA_PATH, "estado_productos.json")
IMAGE_DIR = "product_images"

# Inicializar WooCommerce API
wcapi = API(
    url=WC_URL,
    consumer_key=WC_CONSUMER_KEY,
    consumer_secret=WC_CONSUMER_SECRET,
    version="wc/v3",
    timeout=60
)

SKU_ID_MAP = {}

def load_state():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

def save_state(state):
    with open(STATE_FILE, 'w', encoding='utf-8') as f:
        json.dump(state, f, indent=4, ensure_ascii=False)

def preload_wc_ids(skus):
    """Carga IDs de productos en paralelo."""
    print(f"    [Woo] Pre-cargando IDs para {len(skus)} SKUs...")
    def fetch_id(sku):
        try:
            res = wcapi.get("products", params={"sku": sku, "per_page": 1}).json()
            if isinstance(res, list) and len(res) > 0:
                return sku, res[0]['id']
        except: pass
        return sku, None

    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        results = list(executor.map(fetch_id, skus))
        for sku, pid in results:
            if pid: SKU_ID_MAP[sku] = pid

def upload_single_image(sku, image_path):
    """Sube imagen binaria a WP Mediateca."""
    endpoint = f"{WC_URL}/wp-json/wp/v2/media"
    filename = os.path.basename(image_path)
    try:
        with open(image_path, "rb") as img_file:
            binary_data = img_file.read()
            headers = {
                "Content-Type": "image/jpeg",
                "Content-Disposition": f'attachment; filename="{filename}"',
                "User-Agent": "IntcomexBot/1.0"
            }
            auth = HTTPBasicAuth(WP_USER, WP_APP_PASS)
            response = requests.post(endpoint, data=binary_data, headers=headers, auth=auth, timeout=60)
            if response.status_code in [200, 201]:
                media_info = response.json()
                return sku, media_info.get("id"), media_info.get("source_url")
    except Exception as e:
        print(f"      [!] Error subiendo {sku}: {e}")
    return sku, None, None

def run_image_uploader(max_workers=5):
    print("="*60)
    print("🚀 VINI-TURBO: IMAGE UPLOADER (PARALLEL & BATCH)")
    print("="*60)
    
    state = load_state()
    skus_to_sync = []
    for sku, data in state.items():
        if data.get("pendiente_sync_woo") or (data.get("tiene_imagen") and not data.get("subido_a_woo")):
            skus_to_sync.append(sku)
    
    if not skus_to_sync:
        print("[OK] Todo sincronizado.")
        return 0

    # 1. Pre-cargar IDs
    preload_wc_ids(skus_to_sync)
    
    # 2. Subir imágenes en paralelo
    images_to_upload = []
    for sku in skus_to_sync:
        data = state.get(sku, {})
        if data.get("tiene_imagen") and not data.get("subido_a_woo"):
            local_list = data.get("imagenes_locales") or [None]
            local_path = local_list[0]
            if not local_path or not os.path.exists(local_path):
                # Auto-discovery
                for ext in ['.jpg', '.png', '.webp']:
                    p = os.path.join(IMAGE_DIR, f"{sku}_001{ext}")
                    if os.path.exists(p):
                        local_path = p; break
            if local_path and os.path.exists(local_path):
                images_to_upload.append((sku, local_path))

    media_results = {}
    if images_to_upload:
        print(f"    [WP] Subiendo {len(images_to_upload)} imágenes en paralelo...")
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = [executor.submit(upload_single_image, sku, path) for sku, path in images_to_upload]
            for f in concurrent.futures.as_completed(futures):
                sku, mid, url = f.result()
                if mid: media_results[sku] = {"id": mid, "url": url}

    # 3. Batch Update WooCommerce
    batch_manager = WooBatchManager(wcapi, chunk_size=50)
    success_count = 0
    
    for sku in skus_to_sync:
        pid = SKU_ID_MAP.get(sku)
        if not pid: continue
        
        data = state[sku]
        payload = {
            "regular_price": str(data.get("sale_price")),
            "stock_quantity": data.get("stock"),
            "manage_stock": True,
            "status": "publish"
        }
        
        # Vincular imagen si acabamos de subirla
        if sku in media_results:
            payload["images"] = [{"id": media_results[sku]["id"]}]
        elif not data.get("tiene_imagen") and not data.get("placeholder_personalizado"):
            # Placeholder
            payload["images"] = [{"src": "https://tupartnerti.cl/tienda/wp-content/uploads/2026/03/Flow_6f1163a766.jpeg"}]
            state[sku]["placeholder_personalizado"] = True

        batch_manager.add_update(pid, payload)
        
        # Marcar estado local
        if sku in media_results:
            state[sku]["subido_a_woo"] = True
            state[sku]["woo_media_id"] = media_results[sku]["id"]
            state[sku]["woo_image_url"] = media_results[sku]["url"]
        state[sku]["pendiente_sync_woo"] = False
        success_count += 1

    batch_manager.flush()
    save_state(state)
    
    print(f"✅ Uploader finalizado: {success_count} productos actualizados.")
    return success_count

if __name__ == "__main__":
    run_image_uploader()
