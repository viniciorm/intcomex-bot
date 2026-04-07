import os
import json
import time
import requests
from woocommerce import API
from datetime import datetime
import concurrent.futures
from woo_batch_manager import WooBatchManager

# --- Configuración y Carga de Credenciales ---
try:
    from credentials import (
        WC_URL,
        WC_CONSUMER_KEY,
        WC_CONSUMER_SECRET
    )
except ImportError:
    print("ERROR: No se encontró credentials.py")
    exit(1)

# URLs y Archivos
DATA_PATH = "data_activa"
STATE_FILE = os.path.join(DATA_PATH, "estado_productos.json")
N8N_WEBHOOK_URL = "http://localhost:5678/webhook/ia-transformer" 

# Inicializar API WooCommerce
wcapi = API(
    url=WC_URL,
    consumer_key=WC_CONSUMER_KEY,
    consumer_secret=WC_CONSUMER_SECRET,
    version="wc/v3",
    timeout=60
)

# Cache de IDs para evitar GETs repetidos (Se cargará al inicio)
SKU_ID_MAP = {}

def load_state():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

def save_state(state):
    with open(STATE_FILE, 'w', encoding='utf-8') as f:
        json.dump(state, f, indent=4, ensure_ascii=False)

def preload_wc_ids(pending_skus):
    """Carga todos los IDs de productos de una vez para evitar GETs individuales (Optimización Pro)."""
    print(f"    [Woo] Pre-cargando IDs para {len(pending_skus)} SKUs...")
    # WooCommerce no permite filtrar por múltiples SKUs en un solo GET de forma nativa fácil,
    # pero podemos paginar el catálogo completo o usar una búsqueda por SKU.
    # Por ahora haremos búsquedas rápidas pero concurrentes para llenar el mapa.
    
    def fetch_id(sku):
        try:
            res = wcapi.get("products", params={"sku": sku, "per_page": 1}).json()
            if isinstance(res, list) and len(res) > 0:
                return sku, res[0]['id']
        except: pass
        return sku, None

    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        results = list(executor.map(fetch_id, pending_skus))
        for sku, pid in results:
            if pid: SKU_ID_MAP[sku] = pid

def process_single_ia_request(sku, data):
    """Procesa una sola solicitud a n8n."""
    print(f"    [n8n] Solicitando transformación para {sku}...")
    payload = {
        "sku": sku,
        "nombre": data['nombre'],
        "descripcion": data.get("descripcion_original") or data['nombre']
    }
    try:
        response = requests.post(N8N_WEBHOOK_URL, json=payload, timeout=60)
        if response.status_code == 200:
            result = response.json()
            # Intentar varias rutas comunes de respuesta de n8n
            ia_content = None
            if isinstance(result, list) and len(result) > 0:
                result = result[0]
            
            # Ruta 1: Directo
            choices = result.get("choices", [])
            if isinstance(choices, list) and len(choices) > 0:
                ia_content = choices[0].get("message", {}).get("content")
            
            # Ruta 2: Dentro de 'body'
            if not ia_content and "body" in result:
                body = result["body"]
                if isinstance(body, dict):
                    choices = body.get("choices", [])
                    if isinstance(choices, list) and len(choices) > 0:
                        ia_content = choices[0].get("message", {}).get("content")
                        
            # Ruta 3: Output directo de algún sub-nodo (común en n8n)
            if not ia_content and "output" in result:
                ia_content = result.get("output")
            if not ia_content and "text" in result:
                ia_content = result.get("text")
                
            # Ruta 4: String plano
            if not ia_content and isinstance(result, str):
                ia_content = result
            
            if ia_content:
                return sku, ia_content, None
            else:
                print(f"    [!] n8n no devolvió el formato esperado para {sku}. Extracto: {str(result)[:80]}...")
                return sku, None, "formato_desconocido"
        else:
            print(f"    [!] HTTP {response.status_code} desde n8n para {sku}")
            return sku, None, "error_http"
            
    except requests.exceptions.Timeout:
        print(f"    [!] Timeout de 60s en n8n para {sku}")
        return sku, None, "timeout"
    except Exception as e:
        print(f"    [!] Error de conexión en n8n ({sku}): {e}")
        return sku, None, str(e)

def process_ai_enrichment(limit=None, max_workers=5):
    print("="*50)
    print("🧠 VINI-TURBO: IA ENRICHMENT (PARALLEL & BATCH)")
    print("="*50)
    
    state = load_state()
    
    # Pendientes: Que estén en woo, NO estén mejorados, y tengan menos de 3 intentos fallidos
    pending_skus = []
    for sku, data in state.items():
        if data.get("subido_a_woo") and not data.get("ia_mejorado", False):
            intentos = data.get("ia_intentos", 0)
            if intentos < 3:
                pending_skus.append(sku)
    
    if not pending_skus:
        print("✓ No hay productos pendientes/elegibles para enriquecimiento.")
        return 0

    if limit:
        pending_skus = pending_skus[:limit]
        print(f"ℹ Procesando límite de {limit} productos.")
    
    # 1. Pre-cargar IDs de WooCommerce
    preload_wc_ids(pending_skus)
    
    print(f"🚀 Procesando {len(pending_skus)} productos con {max_workers} hilos...")
    
    batch_manager = WooBatchManager(wcapi, chunk_size=50)
    success_count = 0
    results_to_save = []

    # 2. Ejecutar solicitudes n8n en paralelo
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_sku = {
            executor.submit(process_single_ia_request, sku, state[sku]): sku 
            for sku in pending_skus
        }
        
        for future in concurrent.futures.as_completed(future_to_sku):
            sku, content, error_reason = future.result()
            if content:
                # 3. Enqueue update to WooCommerce
                pid = SKU_ID_MAP.get(sku)
                if pid:
                    batch_manager.add_update(pid, {
                        "description": content,
                        "meta_data": [{"key": "n8n_mejorado", "value": "true"}]
                    })
                    results_to_save.append((sku, content, "success"))
                    success_count += 1
                else:
                    print(f"    [!] No se pudo encontrar el ID en Woo para {sku}, saltando batch.")
                    results_to_save.append((sku, None, "no_wc_id"))
            else:
                results_to_save.append((sku, None, error_reason))

    # 4. Asegurar que todo se envíe a Woo
    batch_manager.flush()

    # 5. Guardar estado local (Una sola vez al final para mayor velocidad)
    if results_to_save:
        print(f"\n💾 Actualizando estado local para {len(results_to_save)} productos...")
        for sku, content, status in results_to_save:
            if status == "success":
                state[sku]["ia_mejorado"] = True
                state[sku]["ia_intentos"] = 0
                state[sku]["ultima_ia"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                # Limpiar error anterior si existía
                if "ultimo_error_ia" in state[sku]: del state[sku]["ultimo_error_ia"]
            else:
                # Incrementar fallitos
                actual_intentos = state[sku].get("ia_intentos", 0)
                state[sku]["ia_intentos"] = actual_intentos + 1
                state[sku]["ultimo_error_ia"] = status
        save_state(state)

    print("\n" + "="*50)
    print(f"✅ VINI-TURBO FINALIZADO")
    print(f"Éxitos: {success_count} / {len(pending_skus)}")
    print("="*50)
    return success_count

def run_ia_webhook_trigger():
    return process_ai_enrichment()

if __name__ == "__main__":
    process_ai_enrichment()
