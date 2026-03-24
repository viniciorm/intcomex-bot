import json
import os

STATE_FILE = r"C:\Users\marco\Documents\GitHub\intcomex-bot\data_activa\estado_productos.json"
if os.path.exists(STATE_FILE):
    with open(STATE_FILE, 'r', encoding='utf-8') as f:
        state = json.load(f)
    
    count = 0
    for sku, data in state.items():
        if not data.get("subido_a_woo"):
            if not data.get("pendiente_sync_woo"):
                data["pendiente_sync_woo"] = True
                count += 1
            
    with open(STATE_FILE, 'w', encoding='utf-8') as f:
        json.dump(state, f, indent=4, ensure_ascii=False)
    print(f"✅ Reset forzado completado: {count} productos marcados como pendientes.")
else:
    print("No state file!")
