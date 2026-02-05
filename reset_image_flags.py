import os
import json

STATE_FILE = "data_activa/estado_productos.json"
IMAGE_DIR = "product_images"

def reset_image_flags():
    if not os.path.exists(STATE_FILE):
        return

    with open(STATE_FILE, 'r', encoding='utf-8') as f:
        state = json.load(f)

    reset_count = 0
    for sku, data in state.items():
        # Posibles extensiones
        found = False
        for ext in ['.jpg', '.png', '.webp', '.jpeg']:
            if os.path.exists(os.path.join(IMAGE_DIR, f"{sku}_L{ext}")):
                found = True
                break
            if os.path.exists(os.path.join(IMAGE_DIR, f"{sku}_001{ext}")):
                found = True
                break
        
        if not found and data.get("tiene_imagen"):
            data["tiene_imagen"] = False
            data["imagenes_locales"] = []
            reset_count += 1

    with open(STATE_FILE, 'w', encoding='utf-8') as f:
        json.dump(state, f, indent=4, ensure_ascii=False)

    print(f"Reset {reset_count} products to tiene_imagen = False")

if __name__ == "__main__":
    reset_image_flags()
