import json
import os

STATE_FILE = r"C:\Users\marco\Documents\GitHub\intcomex-bot\data_activa\estado_productos.json"
if os.path.exists(STATE_FILE):
    with open(STATE_FILE, 'r', encoding='utf-8') as f:
        state = json.load(f)
    
    total = len(state)
    en_woo = sum(1 for p in state.values() if p.get("subido_a_woo"))
    con_imagen = sum(1 for p in state.values() if p.get("tiene_imagen"))
    con_ia = sum(1 for p in state.values() if p.get("ia_mejorado"))
    
    print(f"Total: {total}")
    print(f"En Woo: {en_woo}")
    print(f"Con Imagen: {con_imagen}")
    print(f"Con IA: {con_ia}")
    print(f"Pendientes Sync: {total - en_woo}")
else:
    print("No state file!")
