import os
import json

STATE_FILE = "data_activa/estado_productos.json"

def force_reset_upload_flags():
    if not os.path.exists(STATE_FILE):
        print("Estado no encontrado.")
        return

    with open(STATE_FILE, 'r', encoding='utf-8') as f:
        state = json.load(f)

    count = 0
    for sku, data in state.items():
        # Si tiene imagen pero NO tiene woo_media_id (o queremos forzarlo)
        # O si tiene imagen y está marcado como subido_a_woo=True (pero queremos re-subir para asegurar)
        if data.get("tiene_imagen") and not data.get("woo_media_id"):
            state[sku]["subido_a_woo"] = False
            state[sku]["pendiente_sync_woo"] = True
            count += 1

    with open(STATE_FILE, 'w', encoding='utf-8') as f:
        json.dump(state, f, indent=4, ensure_ascii=False)

    print(f"✅ Reset flags for {count} products. Ready to sync images.")

if __name__ == "__main__":
    force_reset_upload_flags()
