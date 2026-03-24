import os
import json
import time
import hashlib
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

DATA_PATH = "data_activa"
STATE_FILE = os.path.join(DATA_PATH, "estado_productos.json")
IMAGE_DIR = "product_images"
CUSTOM_PLACEHOLDER_URL = "https://tupartnerti.cl/tienda/wp-content/uploads/2026/03/Flow_6f1163a766.jpeg"
GENERIC_FILE_HASH = "a280946523d04c60eba5c478cfb2cb5c"

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

def get_hash(path):
    try:
        with open(path, 'rb') as f:
            return hashlib.md5(f.read()).hexdigest()
    except Exception:
        return None

def fix_bad_images():
    print("="*60)
    print("🔍 BUSCANDO Y LIMPIANDO IMÁGENES GENÉRICAS POR HASH DE ARCHIVO")
    print("="*60)
    
    state = load_json(STATE_FILE)
    if not state:
        print("✗ No se encontraron datos de estado.")
        return
        
    skus_to_fix = []
    
    # Buscar por archivo fisico 
    if os.path.exists(IMAGE_DIR):
        for file in os.listdir(IMAGE_DIR):
            file_path = os.path.join(IMAGE_DIR, file)
            if os.path.isfile(file_path):
                if get_hash(file_path) == GENERIC_FILE_HASH:
                    sku = file.split('_')[0]
                    skus_to_fix.append((sku, file_path))
                    
    # Buscar por SKUs que el usuario reportó que fallan y quizas no están bien mapeados
    reported_skus = ['PC001ASU14', 'NT104ASU17', 'PC001ASU66', 'PC001ASU67', 'ID001BRO39', 'CP991AMD85']
    for row in skus_to_fix.copy():
        if row[0] in reported_skus:
            reported_skus.remove(row[0])
    for s in reported_skus:
         skus_to_fix.append((s, None))
                    
    if not skus_to_fix:
        print("✅ No se encontraron más archivos genéricos localmente.")
        return
        
    print(f"📦 Encontrados {len(skus_to_fix)} productos para arreglar.")
    
    image_payload = [{"src": CUSTOM_PLACEHOLDER_URL}]
    success_count = 0
    
    for i, (sku, file_path) in enumerate(skus_to_fix, 1):
        print(f"[{i}/{len(skus_to_fix)}] Arreglando SKU: {sku}...")
        
        # Eliminar archivo físico para que no lo vuelva a intentar subir
        if file_path and os.path.exists(file_path):
            try:
                os.remove(file_path)
                print(f"    [✓] Archivo genérico físico eliminado.")
            except Exception as e:
                print(f"    [!] Error al eliminar {file_path}: {e}")
                
        # Actualizar en WooCommerce inyectando el placeholder
        try:
            res = wcapi.get("products", params={"sku": sku}).json()
            if res and len(res) > 0:
                product_id = res[0]['id']
                
                payload = {"images": image_payload}
                update_res = wcapi.put(f"products/{product_id}", data=payload)
                
                if update_res.status_code == 200:
                    print("    [✓] Placeholder de Tu Partner TI forzado en WooCommerce.")
                    
                    if sku in state:
                        state[sku]["tiene_imagen"] = False
                        state[sku]["imagenes_locales"] = []
                        state[sku]["subido_a_woo"] = True
                        state[sku]["placeholder_personalizado"] = True
                        save_json(STATE_FILE, state)
                        
                    success_count += 1
                else:
                    print(f"    [✗] Error WooCommerce {update_res.status_code}: {update_res.text[:100]}")
            else:
                print("    [!] Producto no encontrado en WooCommerce.")
        except Exception as e:
            print(f"    [✗] Excepción: {e}")
            
        time.sleep(1)
        
    print(f"\\n✅ Limpieza profunda completada. Arreglados {success_count} de {len(skus_to_fix)} productos.")
        
if __name__ == "__main__":
    fix_bad_images()
