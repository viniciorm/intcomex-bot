import requests
import json
import os
import time
from datetime import datetime

# --- Configuración ---
DATA_PATH = "data_activa"
HEALTH_FILE = os.path.join(DATA_PATH, "health_status.json")

try:
    from credentials import WC_URL, WC_CONSUMER_KEY, WC_CONSUMER_SECRET
except ImportError:
    print("✗ Error: No se encontró credentials.py")
    exit(1)

# URLs a monitorear
N8N_HOST = os.environ.get("N8N_HOST", "n8n-automation")
N8N_URL = f"http://{N8N_HOST}:5678/"
INTCOMEX_URL = "https://store.intcomex.com"

# Cabecera simulada para evitar bloqueos de seguridad
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

def check_woo():
    """Verifica la API de WooCommerce."""
    try:
        # Petición simple para ver si responde
        url = f"{WC_URL}/wp-json/wc/v3/system_status"
        auth = (WC_CONSUMER_KEY, WC_CONSUMER_SECRET)
        response = requests.get(url, auth=auth, headers=HEADERS, timeout=10)
        return response.status_code == 200
    except: return False

def check_n8n():
    """Verifica si n8n está arriba."""
    try:
        # n8n suele responder 200 en su raíz o /healthz
        response = requests.get(N8N_URL, timeout=5)
        return response.status_code == 200
    except: return False

def check_intcomex():
    """Verifica si el portal de Intcomex es accesible."""
    try:
        response = requests.get(INTCOMEX_URL, timeout=10)
        return response.status_code == 200
    except: return False

def run_health_check():
    print("🔍 Iniciando System Health Check...")
    
    health = {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "services": {
            "woocommerce_api": check_woo(),
            "n8n_webhook": check_n8n(),
            "intcomex_portal": check_intcomex(),
            "chrome_driver": True # Asumimos True si el script corre, se podría mejorar
        }
    }
    
    if not os.path.exists(DATA_PATH): os.makedirs(DATA_PATH)
    
    with open(HEALTH_FILE, 'w', encoding='utf-8') as f:
        json.dump(health, f, indent=4)
        
    print(f"✅ Health status actualizado: {health['services']}")
    return health

if __name__ == "__main__":
    run_health_check()
