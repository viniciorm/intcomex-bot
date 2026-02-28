# inventory_cleaner.py
# Gestor de Inventario Inteligente v1.0

import os
import json
import time
from datetime import datetime
from woocommerce import API
from sync_bot import init_woocommerce_api

# Configuración de Rutas
DATA_PATH = "data_activa"
STATE_FILE = os.path.join(DATA_PATH, "estado_productos.json")

def load_state():
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return {}
    return {}

def save_state(state):
    try:
        with open(STATE_FILE, 'w', encoding='utf-8') as f:
            json.dump(state, f, indent=4, ensure_ascii=False)
    except Exception as e:
        print(f"✗ Error al guardar {STATE_FILE}: {e}")

def get_all_woo_products(wcapi):
    """Obtiene todos los productos publicados de WooCommerce."""
    print("🔍 Obteniendo lista de productos desde WooCommerce...")
    all_products = []
    page = 1
    while True:
        try:
            response = wcapi.get("products", params={"per_page": 100, "page": page, "status": "publish"})
            if response.status_code != 200:
                break
            products = response.json()
            if not products:
                break
            all_products.extend(products)
            page += 1
            if len(products) < 100:
                break
        except Exception as e:
            print(f"  ✗ Error al obtener productos (página {page}): {e}")
            break
    print(f"  ✓ {len(all_products)} productos encontrados en WooCommerce.")
    return all_products

def run_inventory_cleaner():
    """Ejecuta la lógica de limpieza y gestión de inventario."""
    print("\n" + "="*50)
    print("🧹 INICIANDO CLEANER BOT (Gestión de Inventario)")
    print("="*50)
    
    wcapi = init_woocommerce_api()
    state = load_state()
    woo_products = get_all_woo_products(wcapi)
    
    skus_in_woo = {p['sku']: p['id'] for p in woo_products if p.get('sku')}
    skus_in_csv = {sku for sku, data in state.items() if data.get('en_csv_reciente', True)}
    
    updates = []
    counters = {
        "reactivados": 0,
        "stock_bajo": 0,
        "fuera_catalogo": 0
    }
    
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # 1. Regla de Ausencia y Stock Bajo para productos en Woo
    for sku, woo_id in skus_in_woo.items():
        if sku not in skus_in_csv:
            # Fuera de catálogo
            print(f"  📉 SKU {sku} fuera de catálogo. Pasando a borrador.")
            updates.append({"id": woo_id, "status": "draft"})
            if sku in state:
                state[sku].update({
                    "status_web": "borrador",
                    "motivo_estado": "fuera_de_catalogo",
                    "ultima_sincronizacion": now_str
                })
            counters["fuera_catalogo"] += 1
            
        elif sku in state:
            stock = state[sku].get("stock", 0)
            if stock <= 2:
                # Stock bajo
                print(f"  🛡️ SKU {sku} stock crítico ({stock}). Pasando a borrador.")
                updates.append({"id": woo_id, "status": "draft"})
                state[sku].update({
                    "status_web": "borrador",
                    "motivo_estado": "stock_seguro",
                    "ultima_sincronizacion": now_str
                })
                counters["stock_bajo"] += 1
            else:
                # Todo normal
                state[sku].update({
                    "status_web": "publicado",
                    "motivo_estado": "disponible",
                    "ultima_sincronizacion": now_str
                })

    # 2. Regla de Re-activación para SKUs en el estado (que podrían estar en draft)
    for sku, data in state.items():
        if sku in skus_in_csv and data.get("stock", 0) > 2:
            if data.get("status_web") == "borrador" or (sku not in skus_in_woo and data.get("woo_id")):
                woo_id = data.get("woo_id")
                if woo_id:
                    print(f"  🚀 SKU {sku} recuperó stock. Re-publicando.")
                    updates.append({"id": woo_id, "status": "publish"})
                    data.update({
                        "status_web": "publicado",
                        "motivo_estado": "disponible",
                        "ultima_sincronizacion": now_str
                    })
                    counters["reactivados"] += 1

    # 3. Aplicar actualizaciones en Batch
    if updates:
        print(f"\n📦 Aplicando {len(updates)} cambios en WooCommerce...")
        # Lote de 20 para evitar límites de headers del servidor/proxy
        batch_size = 20
        for i in range(0, len(updates), batch_size):
            batch = updates[i:i+batch_size]
            try:
                print(f"  ⏳ Procesando lote {i//batch_size + 1} ({len(batch)} productos)...")
                res = wcapi.post("products/batch", data={"update": batch})
                if res.status_code in [200, 201]:
                    print(f"  ✓ Lote {i//batch_size + 1} procesado con éxito.")
                else:
                    print(f"  ✗ Error en lote {i//batch_size + 1}: {res.text[:200]}")
                
                # Pausa de seguridad
                time.sleep(1)
            except Exception as e:
                print(f"  ✗ Excepción en lote {i//batch_size + 1}: {e}")
    else:
        print("\n✨ No hay cambios de inventario necesarios.")

    save_state(state)
    print("\n✅ Cleaner bot finalizado.")
    return counters

if __name__ == "__main__":
    run_inventory_cleaner()
