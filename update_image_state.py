import os
import json

STATE_FILE = "data_activa/estado_productos.json"
MAP_FILE = "data_activa/mapa_imagenes.json"
IMAGE_DIR = "product_images"

def update_images():
    if not os.path.exists(STATE_FILE):
        print(f"No existe {STATE_FILE}")
        return

    with open(STATE_FILE, 'r', encoding='utf-8') as f:
        state = json.load(f)

    if os.path.exists(MAP_FILE):
        with open(MAP_FILE, 'r', encoding='utf-8') as f:
            try:
                img_map = json.load(f)
            except:
                img_map = {}
    else:
        img_map = {}

    images = [f for f in os.listdir(IMAGE_DIR) if f.lower().endswith('.jpg')]
    print(f"Encontradas {len(images)} imagenes en {IMAGE_DIR}")

    updated_count = 0
    for img_name in images:
        # Extraer SKU: usualmente SKU_001.jpg o SKU_L.jpg
        sku = img_name.split('_')[0]
        
        if sku in state:
            path = os.path.join(IMAGE_DIR, img_name)
            state[sku]["tiene_imagen"] = True
            state[sku]["imagenes_locales"] = [path]
            img_map[sku] = path
            updated_count += 1
            print(f"Asignado {img_name} a {sku}")
        else:
            # Reintento por si el SKU tiene guiones o algo raro
            # Por ahora probamos con el prefijo
            print(f"SKU {sku} no encontrado en estado para imagen {img_name}")

    with open(STATE_FILE, 'w', encoding='utf-8') as f:
        json.dump(state, f, indent=4, ensure_ascii=False)
    
    with open(MAP_FILE, 'w', encoding='utf-8') as f:
        json.dump(img_map, f, indent=4, ensure_ascii=False)

    print(f"Actualizacion finalizada. {updated_count} productos actualizados.")

if __name__ == "__main__":
    update_images()
