import json
import os

STATE_FILE = r"C:\Users\marco\Documents\GitHub\intcomex-bot\data_activa\estado_productos.json"
if os.path.exists(STATE_FILE):
    with open(STATE_FILE, 'r', encoding='utf-8') as f:
        state = json.load(f)
    
    count = 0
    for sku, data in state.items():
        # Si no esta en woo pero el flag dice que no hay nada pendiente, corregimos
        if not data.get("subido_a_woo") and not data.get("pendiente_sync_woo"):
            data["pendiente_sync_woo"] = True
            count += 1
            
    if count > 0:
        with open(STATE_FILE, 'w', encoding='utf-8') as f:
            json.dump(state, f, indent=4, ensure_ascii=False)
        print(f"✅ Reset completado: {count} productos vuelven a estar pendientes de sincronización.")
    else:
        print("✓ No se encontraron productos en estado inconsistente.")
else:
    print("No state file!")
