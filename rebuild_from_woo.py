import os
import json
import time
from woocommerce import API
from datetime import datetime

# Importar credenciales
try:
    from credentials import (
        WC_URL,
        WC_CONSUMER_KEY,
        WC_CONSUMER_SECRET
    )
except ImportError:
    print("ERROR: No se encontró el archivo 'credentials.py'")
    exit(1)

# Configuración
DATA_PATH = "data_activa"
STATE_FILE = os.path.join(DATA_PATH, "estado_productos.json")
MAP_FILE = os.path.join(DATA_PATH, "mapa_imagenes.json")
FECHA_RECONSTRUCCION = "2026-02-03 18:00:00"

# Inicializar WooCommerce API
wcapi = API(
    url=WC_URL,
    consumer_key=WC_CONSUMER_KEY,
    consumer_secret=WC_CONSUMER_SECRET,
    version="wc/v3",
    timeout=60
)

def fetch_all_products():
    print(f"Buscando productos en {WC_URL}...")
    products = []
    page = 1
    while True:
        try:
            params = {"per_page": 100, "page": page}
            response = wcapi.get("products", params=params)
            if response.status_code != 200:
                print(f"Error HTTP {response.status_code}: {response.text}")
                break
            
            data = response.json()
            if not data:
                break
            
            products.extend(data)
            print(f"  Página {page} cargada. Total acumulado: {len(products)}")
            page += 1
            
            # Pequeña pausa para no saturar la API
            time.sleep(1)
        except Exception as e:
            print(f"Error en página {page}: {e}")
            break
    return products

def rebuild():
    print("="*60)
    print("RECONSTRUCTOR DE ESTADO DESDE WOOCOMMERCE (ENFOQUE IMÁGENES)")
    print("="*60)

    if not os.path.exists(DATA_PATH):
        os.makedirs(DATA_PATH)

    all_products = fetch_all_products()
    if not all_products:
        print("No se encontraron productos en WooCommerce.")
        return

    state = {}
    image_map = {}

    for p in all_products:
        sku = p.get("sku")
        if not sku:
            # Intentar usar el ID como SKU si no tiene (aunque no es ideal para Intcomex)
            sku = f"ID_{p.get('id')}"
        
        name = p.get("name")
        price = float(p.get("regular_price") or 0)
        stock = p.get("stock_quantity") or 0
        
        # Categorías
        categories = p.get("categories", [])
        cat_principal = categories[0].get("name") if categories else "Reconstruido"
        subcat = categories[1].get("name") if len(categories) > 1 else None
        
        # Imágenes
        images = p.get("images", [])
        tiene_imagen = len(images) > 0
        woo_image_url = images[0].get("src") if tiene_imagen else None
        woo_media_id = images[0].get("id") if tiene_imagen else None
        
        # Reconstruir estado
        state[sku] = {
            "sku": sku,
            "nombre": name,
            "cost_price": round(price * 0.8), # Estimación (se corregirá con sync)
            "sale_price": price,
            "stock": stock,
            "categoria_principal": cat_principal,
            "categoria_csv": cat_principal,
            "subcategoria_csv": subcat,
            "last_updated": FECHA_RECONSTRUCCION,
            "tiene_imagen": tiene_imagen,
            "imagenes_locales": [], # No sabemos la ruta local aquí
            "subido_a_woo": True,
            "pendiente_sync_woo": False,
            "procedencia": "reconstruccion_woo",
            "woo_media_id": woo_media_id,
            "woo_image_url": woo_image_url
        }
        
        # Poblar mapa de imágenes
        if tiene_imagen:
            image_map[sku] = woo_image_url

    print(f"Guardando {len(state)} productos en {STATE_FILE}...")
    with open(STATE_FILE, 'w', encoding='utf-8') as f:
        json.dump(state, f, indent=4, ensure_ascii=False)

    print(f"Guardando {len(image_map)} URLs en {MAP_FILE}...")
    with open(MAP_FILE, 'w', encoding='utf-8') as f:
        json.dump(image_map, f, indent=4, ensure_ascii=False)

    print("\n" + "="*60)
    print("RECONSTRUCCIÓN FINALIZADA")
    print("="*60)

if __name__ == "__main__":
    rebuild()
