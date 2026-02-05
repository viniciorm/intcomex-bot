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
DATA_PATH = "data_activa"
STATE_FILE = os.path.join(DATA_PATH, "estado_productos.json")

# Inicializar WooCommerce API para vinculación
wcapi = API(
    url=WC_URL,
    consumer_key=WC_CONSUMER_KEY,
    consumer_secret=WC_CONSUMER_SECRET,
    version="wc/v3",
    timeout=60
)

# --- Funciones de Utilidad WooCommerce ---
category_cache = {}

def woocommerce_request(wcapi, method, endpoint, data=None, params=None, max_retries=3):
    for attempt in range(max_retries):
        try:
            if method.lower() == 'get': response = wcapi.get(endpoint, params=params)
            elif method.lower() == 'post': response = wcapi.post(endpoint, data=data)
            elif method.lower() == 'put': response = wcapi.put(endpoint, data=data)
            else: return None
            return response
        except Exception as e:
            if attempt < max_retries - 1: time.sleep(2)
            else: print(f"✗ Fallo tras {max_retries} reintentos: {e}")
    return None

def get_or_create_woo_category(wcapi, category_name, parent_id=None):
    cache_key = f"{category_name}_{parent_id}"
    if cache_key in category_cache: return category_cache[cache_key]
    try:
        params = {"search": category_name, "per_page": 20}
        if parent_id: params["parent"] = parent_id
        response = woocommerce_request(wcapi, "get", "products/categories", params=params)
        if response and response.status_code == 200:
            for cat in response.json():
                if cat['name'].lower() == category_name.lower():
                    category_cache[cache_key] = cat['id']
                    return cat['id']
        new_cat_data = {"name": category_name}
        if parent_id: new_cat_data["parent"] = parent_id
        create_res = woocommerce_request(wcapi, "post", "products/categories", data=new_cat_data)
        if create_res and create_res.status_code in [200, 201]:
            new_id = create_res.json().get('id')
            category_cache[cache_key] = new_id
            return new_id
    except: pass
    return None

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


def sync_product_data_to_woo(sku, data):
    """Sincroniza datos base a WooCommerce."""
    print(f"    [SYNC] Datos para SKU: {sku}")
    product_id, _ = find_product_id_by_sku(sku)
    
    # Gestionar categorías
    categories_list = []
    cat_name = data.get("categoria_csv") or data.get("categoria_principal")
    if cat_name:
        cat_id = get_or_create_woo_category(wcapi, cat_name)
        if cat_id:
            categories_list.append({"id": cat_id})
            subcat_name = data.get("subcategoria_csv")
            if subcat_name:
                sub_id = get_or_create_woo_category(wcapi, subcat_name, parent_id=cat_id)
                if sub_id:
                    categories_list.append({"id": sub_id})

    payload = {
        "name": data.get("nombre"),
        "type": "simple",
        "regular_price": str(data.get("sale_price")),
        "description": data.get("nombre"),
        "short_description": data.get("nombre"),
        "sku": sku,
        "manage_stock": True,
        "stock_quantity": data.get("stock"),
        "status": "publish",
        "categories": categories_list
    }

    try:
        if product_id:
            response = wcapi.put(f"products/{product_id}", data=payload)
            if response.status_code == 200:
                print(f"      [OK] Precio/Stock/Cat actualizados.")
                return product_id
        else:
            response = wcapi.post("products", data=payload)
            if response.status_code == 201:
                new_id = response.json().get("id")
                print(f"      [OK] Producto creado con ID: {new_id}")
                return new_id
        print(f"      [ERROR] Sync falló (HTTP {response.status_code})")
    except Exception as e:
        print(f"      [EXCEPTION] Sync error: {e}")
    return None

def run_image_uploader():
    """
    Fase C: Sincronización final con WordPress/WooCommerce.
    Sincroniza Datos (Precio/Stock) e Imágenes.
    """
    print("\n" + "="*60)
    print("🚀 FASE C: ACTUALIZACIÓN FINAL WOOCOMMERCE")
    print("="*60)
    
    state = load_state()
    if not state:
        print("[!] No hay datos en el estado local.")
        return 0

    # 1. Detectar qué necesita ser sincronizado
    # - Productos con pendiente_sync_woo=True
    # - Productos con tiene_imagen=True y subido_a_woo=False
    skus_to_sync = [sku for sku, data in state.items() if data.get("pendiente_sync_woo") or (data.get("tiene_imagen") and not data.get("subido_a_woo"))]
    
    if not skus_to_sync:
        print("[OK] Todo el estado local ya está sincronizado con WooCommerce.")
        return 0

    print(f"    [INFO] Procesando {len(skus_to_sync)} SKUs pendientes.")
    
    success_count = 0

    for sku in skus_to_sync:
        print(f"\n[PROCESANDO] SKU: {sku}")
        data = state[sku]
        
        # A. Sincronizar Datos (Precio/Stock)
        product_id = sync_product_data_to_woo(sku, data)
        
        if not product_id:
            print(f"    [!] No se pudo sincronizar datos base. Saltando...")
            continue
            
        # B. Sincronizar Imagen si tiene una local y no está subida
        if data.get("tiene_imagen") and not data.get("subido_a_woo"):
            local_path = data.get("imagenes_locales", [None])[0]
            if local_path and os.path.exists(local_path):
                media_id, media_url = upload_image_binary(local_path, sku)
                if media_id:
                    if link_image_to_product(product_id, media_id, sku):
                        state[sku]["subido_a_woo"] = True
                        state[sku]["woo_media_id"] = media_id
                        state[sku]["woo_image_url"] = media_url
            else:
                print(f"    [!] Imagen local no encontrada para {sku}")

        # Marcar como sincronizado
        state[sku]["pendiente_sync_woo"] = False
        save_state(state)
        success_count += 1
        
        # Pausa de seguridad (Requisito: proteger hosting tupartnerti.cl)
        time.sleep(2.0)

    print(f"\n✅ Fase C finalizada: {success_count} productos impactados en WooCommerce.")
    return success_count

if __name__ == "__main__":
    run_image_uploader()
