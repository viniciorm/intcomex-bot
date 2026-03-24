import json
import os

def check(file):
    if os.path.exists(file):
        with open(file, 'r', encoding='utf-8') as f:
            state = json.load(f)
        return len(state), sum(1 for p in state.values() if p.get("subido_a_woo"))
    return 0, 0

prod = check(r"C:\Users\marco\Documents\GitHub\intcomex-bot\data_activa\estado_productos.json")
dev = check(r"C:\Users\marco\Documents\GitHub\intcomex-bot\desarrollo\data_activa\estado_productos.json")

print(f"PROD: Total {prod[0]}, Woo {prod[1]}")
print(f"DEV:  Total {dev[0]}, Woo {dev[1]}")
