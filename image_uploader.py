import os
import json
import time
import requests
from woocommerce import API
from requests.auth import HTTPBasicAuth

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
    print("ERROR: No se encontró el archivo 'credentials.py' con WP_USER y WP_APP_PASS")
    exit(1)

# Configuración
STATE_FILE = "estado_productos.json"

# Inicializar WooCommerce API para vinculación
wcapi = API(
    url=WC_URL,
    consumer_key=WC_CONSUMER_KEY,
    consumer_secret=WC_CONSUMER_SECRET,
    version="wc/v3",
    timeout=60
)

def load_state():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

def save_state(state):
    with open(STATE_FILE, 'w', encoding='utf-8') as f:
        json.dump(state, f, indent=4, ensure_ascii=False)

def upload_image_binary(image_path, sku):
    """
    Sube un archivo de imagen como binario a la biblioteca de medios de WordPress.
    Requiere Application Password para autenticación básica.
    """
    print(f"    [SUBIENDO] Imagen binaria: {image_path}")
    
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
            
            # Autenticación usando Application Password
            auth = HTTPBasicAuth(WP_USER, WP_APP_PASS)
            
            response = requests.post(
                endpoint,
                data=binary_data,
                headers=headers,
                auth=auth,
                timeout=60,
                verify=True
            )
            
            if response.status_code in [200, 201]:
                media_info = response.json()
                media_id = media_info.get("id")
                media_url = media_info.get("source_url")
                print(f"      [OK] Imagen subida a Mediateca (ID: {media_id})")
                return media_id, media_url
            else:
                print(f"      [ERROR] Al subir (HTTP {response.status_code}): {response.text[:200]}")
                return None, None
    except Exception as e:
        print(f"      [EXCEPTION] En subida binaria: {e}")
        return None, None

def find_product_id_by_sku(sku):
    """Busca el ID de producto en WooCommerce por SKU."""
    try:
        response = wcapi.get("products", params={"sku": sku})
        if response.status_code == 200:
            products = response.json()
            if products:
                return products[0].get("id"), products[0].get("images", [])
        return None, None
    except Exception as e:
        print(f"    [ERROR] Buscando SKU {sku}: {e}")
        return None, None

def link_image_to_product(product_id, media_id, sku):
    """Vincula una imagen (por ID de medio) a un producto usando WooCommerce API."""
    print(f"    [LINKING] Imagen ID {media_id} al producto ID {product_id}")
    try:
        data = {
            "images": [{"id": media_id}]
        }
        response = wcapi.put(f"products/{product_id}", data=data)
        if response.status_code == 200:
            print(f"      [OK] Producto actualizado con éxito para SKU {sku}")
            return True
        else:
            print(f"      [ERROR] Al vincular (HTTP {response.status_code}): {response.text[:200]}")
            return False
    except Exception as e:
        print(f"      [EXCEPTION] Al vincular: {e}")
        return False

def main():
    print("="*60)
    print("IMAGE UPLOADER: DEFINITIVO (APP PASSWORD + BINARY POST)")
    print("="*60)
    
    state = load_state()
    if not state:
        print("[!] No hay productos en estado_productos.json")
        return

    # Solo procesamos los que tienen imagen local y no han sido subidos con éxito
    skus_to_process = [sku for sku, data in state.items() 
                      if data.get("tiene_imagen") and not data.get("subido_a_woo")]
    
    if not skus_to_process:
        print("[OK] No hay imágenes pendientes de subir.")
        return

    print(f"    [INFO] Encontrados {len(skus_to_process)} productos pendientes.")

    for sku in skus_to_process:
        print(f"\n[PROCESANDO] SKU: {sku}")
        
        # 1. Buscar producto en WooCommerce
        product_id, existing_images = find_product_id_by_sku(sku)
        
        if not product_id:
            print(f"    [!] El producto {sku} no existe en WooCommerce todavía. Saltando...")
            continue

        # 2. Subida física
        local_images = state[sku].get("imagenes_locales", [])
        if not local_images:
            continue
            
        local_path = local_images[0]
        if not os.path.exists(local_path):
            print(f"    [ERROR] Archivo no encontrado: {local_path}")
            continue

        media_id, media_url = upload_image_binary(local_path, sku)
        
        if media_id:
            # 3. Vinculación
            if link_image_to_product(product_id, media_id, sku):
                state[sku]["subido_a_woo"] = True
                state[sku]["woo_media_id"] = media_id
                state[sku]["woo_image_url"] = media_url
                save_state(state)
                # Pausa breve de estabilidad
                time.sleep(1)

    print("\n" + "="*60)
    print("[OK] PROCESO DE CARGA Y VINCULACIÓN FINALIZADO")
    print("="*60)

if __name__ == "__main__":
    main()
