import os
import json
import time
from woocommerce import API

# --- Configuración y Carga de Credenciales ---
try:
    from credentials import (
        WC_URL,
        WC_CONSUMER_KEY,
        WC_CONSUMER_SECRET
    )
except ImportError:
    print("ERROR: No se encontró credentials.py")
    exit(1)

# URLs y Archivos
DATA_PATH = "data_activa"
STATE_FILE = os.path.join(DATA_PATH, "estado_productos.json")
MAP_FILE = os.path.join(DATA_PATH, "mapa_imagenes.json")
IMAGE_DIR = "product_images"

# Inicializar API WooCommerce
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

def clean_generic_images():
    print("="*60)
    print("🧹 LIMPIEZA DE IMÁGENES GENÉRICAS (NOIMAGE)")
    print("="*60)
    
    state = load_json(STATE_FILE)
    image_map = load_json(MAP_FILE)
    
    if not state or not image_map:
        print("✗ No se encontraron datos de estado o mapa de imágenes.")
        return
        
    skus_to_clean = []
    
    # Identificar SKUs con imágenes genéricas
    for sku, url in image_map.items():
        if "noimage" in url.lower() or "no-image" in url.lower():
            if sku in state and state[sku].get("tiene_imagen", False):
                skus_to_clean.append(sku)
                
    if not skus_to_clean:
        print("✅ No se encontraron productos con imágenes genéricas para limpiar.")
        return
        
    print(f"📦 Encontrados {len(skus_to_clean)} productos para limpiar.")
    
    success_count = 0
    
    for i, sku in enumerate(skus_to_clean, 1):
        print(f"[{i}/{len(skus_to_clean)}] Limpiando SKU: {sku}...")
        
        # 1. Eliminar imagen en WooCommerce
        try:
            res = wcapi.get("products", params={"sku": sku}).json()
            if res and len(res) > 0:
                product_id = res[0]['id']
                
                # Enviar payload con array de imagenes vacio para borrar la imagen asignada
                payload = {"images": []}
                update_res = wcapi.put(f"products/{product_id}", data=payload)
                
                if update_res.status_code == 200:
                    print("    [✓] Imagen eliminada en WooCommerce.")
                    
                    # 2. Eliminar archivo local físico
                    local_files = state[sku].get("imagenes_locales", [])
                    for file_path in local_files:
                        if os.path.exists(file_path):
                            try:
                                os.remove(file_path)
                                print(f"    [✓] Archivo físico eliminado: {file_path}")
                            except Exception as e:
                                print(f"    [!] No se pudo eliminar el archivo local: {e}")
                                
                    # 3. Actualizar estado local
                    state[sku]["tiene_imagen"] = False
                    state[sku]["imagenes_locales"] = []
                    # Eliminamos para que no vuelva a intentar subir la imagen genérica
                    
                    # Guardamos progreso
                    save_json(STATE_FILE, state)
                    success_count += 1
                else:
                    print(f"    [✗] Error WooCommerce al limpiar imagen: {update_res.status_code}")
            else:
                print("    [!] Producto no encontrado en WooCommerce.")
        except Exception as e:
            print(f"    [✗] Excepción procesando {sku}: {e}")
            
        time.sleep(1) # Pequeña pausa para no saturar la API
        
    print(f"\n✅ Proceso completado. Limpiados {success_count} de {len(skus_to_clean)} productos.")
        
if __name__ == "__main__":
    clean_generic_images()
