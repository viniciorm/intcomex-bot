import json
import os

STATE_FILE = r"C:\Users\marco\Documents\GitHub\intcomex-bot\data_activa\estado_productos.json"
if os.path.exists(STATE_FILE):
    with open(STATE_FILE, 'r', encoding='utf-8') as f:
        state = json.load(f)
    
    pending = [sku for sku, data in state.items() if not data.get("subido_a_woo")]
    print(f"Total Pendientes: {len(pending)}")
    for sku in pending[:5]:
        data = state[sku]
        print(f"SKU: {sku} | Stock: {data.get('stock')} | Tiene Img: {data.get('tiene_imagen')} | Pendiente Sync: {data.get('pendiente_sync_woo')}")
else:
    print("No state file!")
