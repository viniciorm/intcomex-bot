import os
import json
import time
import requests
from woocommerce import API
from requests.auth import HTTPBasicAuth

# --- Configuración y Carga de Credenciales ---
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

DATA_PATH = "data_activa"
STATE_FILE = os.path.join(DATA_PATH, "estado_productos.json")

# URL entregada por el usuario
CUSTOM_PLACEHOLDER_URL = "https://tupartnerti.cl/tienda/wp-content/uploads/2026/03/Flow_6f1163a766.jpeg"

wcapi = API(
    url=WC_URL,
    consumer_key=WC_CONSUMER_KEY,
    consumer_secret=WC_CONSUMER_SECRET,
    version="wc/v3",
    timeout=60
)

def load_json(filepath):
    if os.path.exists(filepath):
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

def save_json(filepath, data):
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

def get_placeholder_media_id():
    """Obtiene el ID del medio en WordPress o lo sube si no existe / no se encuentra."""
    print(" Buscando Media ID para el placeholder personalizado...")
    endpoint = f"{WC_URL}/wp-json/wp/v2/media?search=Flow_6f1163a766"
    auth = HTTPBasicAuth(WP_USER, WP_APP_PASS)
    try:
        # Added User-Agent because standard requests without one might be blocked by hosts
        response = requests.get(endpoint, auth=auth, headers={"User-Agent": "Mozilla/5.0"}, timeout=30)
        if response.status_code == 200:
            items = response.json()
            if items:
                media_id = items[0]["id"]
                print(f" [OK] Media ID encontrado: {media_id}")
                return media_id
    except Exception as e:
        print(f" [!] Error buscando media ID en WP API: {e}")
        
    print(" [!] No se pudo obtener el ID vía API de forma limpia. Usaremos la URL (src) directamente, WooCommerce lo gestionará.")
    return None

def assign_custom_placeholders():
    print("="*60)
    print("🎨 ASIGNANDO PLACEHOLDER PERSONALIZADO A PRODUCTOS SIN IMAGEN")
    print("="*60)
    
    state = load_json(STATE_FILE)
    if not state:
        print("✗ No se encontraron datos de estado.")
        return
        
    # Identificamos productos activos que no tienen imagen local 
    # y que NO se les ha asignado aún el placeholder personalizado.
    skus_to_update = []
    for sku, data in state.items():
        if data.get("stock", 0) > 0 and not data.get("tiene_imagen", False):
            if not data.get("placeholder_personalizado", False):
                skus_to_update.append(sku)
                
    if not skus_to_update:
        print("✅ No hay productos pendientes de asignar placeholder.")
        return
        
    print(f"📦 Encontrados {len(skus_to_update)} productos para asignar placeholder.")
    
    media_id = get_placeholder_media_id()
    image_payload = [{"id": media_id}] if media_id else [{"src": CUSTOM_PLACEHOLDER_URL}]
    
    success_count = 0
    
    for i, sku in enumerate(skus_to_update, 1):
        print(f"[{i}/{len(skus_to_update)}] Asignando a SKU: {sku}...")
        
        try:
            res = wcapi.get("products", params={"sku": sku}).json()
            if res and len(res) > 0:
                product_id = res[0]['id']
                
                payload = {"images": image_payload}
                update_res = wcapi.put(f"products/{product_id}", data=payload)
                
                if update_res.status_code == 200:
                    print("    [✓] Placeholder asignado en WooCommerce.")
                    state[sku]["placeholder_personalizado"] = True
                    # Set subido_a_woo to True to avoid image_uploader trying to override this
                    state[sku]["subido_a_woo"] = True 
                    save_json(STATE_FILE, state)
                    success_count += 1
                else:
                    print(f"    [✗] Error WooCommerce {update_res.status_code}: {update_res.text[:100]}")
            else:
                print("    [!] Producto no encontrado.")
        except Exception as e:
            print(f"    [✗] Excepción: {e}")
            
        time.sleep(1)
        
    print(f"\\n✅ Proceso completado. Asignados {success_count} de {len(skus_to_update)} productos.")
        
if __name__ == "__main__":
    assign_custom_placeholders()
