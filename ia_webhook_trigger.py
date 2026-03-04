import os
import json
import time
import requests
from woocommerce import API
from datetime import datetime

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
# URL de n8n (Usando localhost para evitar problemas de DNS local)
N8N_WEBHOOK_URL = "http://localhost:5678/webhook/ia-transformer" 

# Inicializar API WooCommerce
wcapi = API(
    url=WC_URL,
    consumer_key=WC_CONSUMER_KEY,
    consumer_secret=WC_CONSUMER_SECRET,
    version="wc/v3",
    timeout=60
)

def load_state():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

def save_state(state):
    with open(STATE_FILE, 'w', encoding='utf-8') as f:
        json.dump(state, f, indent=4, ensure_ascii=False)

def update_woo_description(sku, new_description):
    """Actualiza solo la descripción y marca el meta_data en Woo para redundancia."""
    print(f"    [WOO] Buscando ID para SKU: {sku}...")
    try:
        res = wcapi.get("products", params={"sku": sku}).json()
        if not res:
            print(f"    [!] SKU {sku} no encontrado en WooCommerce.")
            return False
        
        product_id = res[0]['id']
        payload = {
            "description": new_description,
            "meta_data": [
                {"key": "n8n_mejorado", "value": "true"}
            ]
        }
        
        update_res = wcapi.put(f"products/{product_id}", data=payload)
        if update_res.status_code == 200:
            print(f"    [✓] WooCommerce actualizado.")
            return True
        else:
            print(f"    [✗] Error WooCommerce ({update_res.status_code}): {update_res.text[:200]}")
            return False
    except Exception as e:
        print(f"    [!] Excepción en WooCommerce: {e}")
        return False

def process_ai_enrichment(limit=None):
    print("="*50)
    print("🧠 BOT DE ENRIQUECIMIENTO IA (V2 - LITE)")
    print("="*50)
    
    state = load_state()
    # Filtrar: Subidos a Woo Y NO mejorados por IA (o que no tengan el campo)
    pending_skus = [
        sku for sku, data in state.items() 
        if data.get("subido_a_woo") and not data.get("ia_mejorado", False)
    ]
    
    if not pending_skus:
        print("✓ No hay productos pendientes de enriquecimiento.")
        return

    if limit:
        pending_skus = pending_skus[:limit]
        print(f"ℹ Procesando límite de {limit} productos.")
    
    print(f"🚀 Iniciando proceso para {len(pending_skus)} productos...")
    
    success_count = 0
    
    for i, sku in enumerate(pending_skus, 1):
        data = state[sku]
        print(f"\n[{i}/{len(pending_skus)}] PROCESANDO: {sku}")
        print(f"    Nombre: {data['nombre']}")
        
        # 1. Llamar a n8n para transformar
        payload = {
            "sku": sku,
            "nombre": data['nombre'],
            "descripcion": data.get("descripcion_original") or data['nombre']
        }
        
        try:
            print(f"    [n8n] Solicitando transformación...")
            response = requests.post(N8N_WEBHOOK_URL, json=payload, timeout=60)
            
            if response.status_code == 200:
                result = response.json()
                # DEBUG: Ver respuesta real de n8n
                # print(f"    [DEBUG] Respuesta n8n: {json.dumps(result, indent=2)}")
                
                # Intentar varias rutas comunes de respuesta de n8n
                ia_content = None
                if isinstance(result, list) and len(result) > 0:
                    result = result[0]
                
                # Ruta 1: Directo (si n8n devuelve el objeto de OpenAI)
                ia_content = result.get("choices", [{}])[0].get("message", {}).get("content")
                
                # Ruta 2: Dentro de 'body' (si n8n lo envuelve)
                if not ia_content and "body" in result:
                    ia_content = result["body"].get("choices", [{}])[0].get("message", {}).get("content")
                
                if ia_content:
                    print(f"    [✓] IA respondió correctamente.")
                    
                    # 2. Actualizar WooCommerce
                    if update_woo_description(sku, ia_content):
                        # 3. Guardar estado local
                        state[sku]["ia_mejorado"] = True
                        state[sku]["ultima_ia"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        save_state(state)
                        success_count += 1
                        print(f"    [★] OK!")
                else:
                    print(f"    [!] Respuesta de IA vacía.")
            else:
                print(f"    [✗] Error en n8n ({response.status_code}): {response.text[:200]}")
        
        except Exception as e:
            print(f"    [!] Error crítico procesando {sku}: {e}")
        
        # Pausa de seguridad para no saturar OpenAI ni WooCommerce
        time.sleep(3)

    print("\n" + "="*50)
    print(f"✅ PROCESO TERMINADO")
    print(f"Éxitos: {success_count} / {len(pending_skus)}")
    print("="*50)
    return success_count

def run_ia_webhook_trigger():
    """Función de compatibilidad para el Orquestador principal."""
    return process_ai_enrichment()

if __name__ == "__main__":
    # Puedes pasar un límite para pruebas, ej: process_ai_enrichment(limit=5)
    process_ai_enrichment()
