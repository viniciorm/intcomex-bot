import os
import json
from datetime import datetime

DATA_PATH = "./data_activa"
LOG_FILE = os.path.join(DATA_PATH, "actividades.json")
MAX_LOGS = 50  # Mantener solo las últimas 50 actividades para no saturar frontend

def _load_logs():
    if os.path.exists(LOG_FILE):
        try:
            with open(LOG_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return []
    return []

def _save_logs(logs):
    os.makedirs(DATA_PATH, exist_ok=True)
    with open(LOG_FILE, 'w', encoding='utf-8') as f:
        json.dump(logs, f, indent=4, ensure_ascii=False)

def log_activity(message, categoria="Sistema", icon="fa-robot"):
    """
    Registra una nueva actividad en el dashboard.
    
    Categorías sugeridas: Sincronización, WooCommerce, IA Enrichment, Media, Sistema
    Iconos sugeridos (FontAwesome): 
        - fa-rocket (Lanzamientos/IA)
        - fa-sync (Sincro general)
        - fa-image (Fotos)
        - fa-broom (Limpieza/Cleaner)
        - fa-envelope (Correos)
        - fa-exclamation-triangle (Errores)
    """
    logs = _load_logs()
    
    new_log = {
        "timestamp": datetime.now().isoformat(),
        "message": message,
        "categoria": categoria,
        "icon": icon
    }
    
    logs.insert(0, new_log)  # Insertar al principio
    
    # Mantener el límite
    if len(logs) > MAX_LOGS:
        logs = logs[:MAX_LOGS]
        
    _save_logs(logs)

# Pruebas:
if __name__ == "__main__":
    log_activity("Sistema de logging inicializado", "Sistema", "fa-check-circle")
    print("Log inicializado con éxito.")
