import os
import json
from woocommerce import API

try:
    from credentials import WC_URL, WC_CONSUMER_KEY, WC_CONSUMER_SECRET
except ImportError:
    print("Error cargando credenciales.")
    exit(1)

DATA_PATH = "data_activa"
STATE_FILE = os.path.join(DATA_PATH, "estado_productos.json")

wcapi = API(
    url=WC_URL,
    consumer_key=WC_CONSUMER_KEY,
    consumer_secret=WC_CONSUMER_SECRET,
    version="wc/v3",
    timeout=60
)

def migrate():
    print("🔍 Iniciando migración de estado de IA desde WooCommerce...")
    if not os.path.exists(STATE_FILE):
        print("Error: No existe el archivo de estado local.")
        return

    with open(STATE_FILE, 'r', encoding='utf-8') as f:
        state = json.load(f)

    # Filtrar productos subidos
    subidos = [sku for sku, data in state.items() if data.get("subido_a_woo")]
    print(f"Productos subidos a Woo: {len(subidos)}")

    count = 0
    for i, sku in enumerate(subidos, 1):
        if i % 10 == 0: print(f"Procesando {i}/{len(subidos)}...")
        
        try:
            res = wcapi.get("products", params={"sku": sku}).json()
            if res:
                p = res[0]
                meta = p.get("meta_data", [])
                mejorado = any(m.get("key") == "n8n_mejorado" and str(m.get("value")).lower() == "true" for m in meta)
                
                if mejorado:
                    state[sku]["ia_mejorado"] = True
                    count += 1
        except:
            continue

    with open(STATE_FILE, 'w', encoding='utf-8') as f:
        json.dump(state, f, indent=4, ensure_ascii=False)
    
    print(f"✅ Migración finalizada. {count} productos marcados como IA_MEJORADO en el JSON local.")

if __name__ == "__main__":
    migrate()
