import os
import json

STATE_FILE = "data_activa/estado_productos.json"
MAPA_IMAGENES_PATH = "data_activa/mapa_imagenes.json"

def force_sync():
    if not os.path.exists(STATE_FILE) or not os.path.exists(MAPA_IMAGENES_PATH):
        return

    with open(STATE_FILE, 'r', encoding='utf-8') as f:
        state = json.load(f)

    with open(MAPA_IMAGENES_PATH, 'r', encoding='utf-8') as f:
        image_map = json.load(f)

    count = 0
    for sku, img_url in image_map.items():
        if "noimage.jpg" in img_url:
            continue
            
        if sku in state:
            if not state[sku].get("pendiente_sync_woo"):
                state[sku]["tiene_imagen"] = True
                state[sku]["pendiente_sync_woo"] = True
                count += 1

    with open(STATE_FILE, 'w', encoding='utf-8') as f:
        json.dump(state, f, indent=4, ensure_ascii=False)

    print(f"Forced sync flag for {count} products.")

if __name__ == "__main__":
    force_sync()
