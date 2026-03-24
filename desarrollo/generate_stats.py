import os
import json
from datetime import datetime

# --- Configuración ---
DATA_PATH = "data_activa"
STATE_FILE = os.path.join(DATA_PATH, "estado_productos.json")
HISTORICO_FILE = os.path.join(DATA_PATH, "historico_stats.json")

# Lógica de HH (Horas Hombre) ahorradas por producto
HH_SYNC = 5 / 60   # 5 min
HH_IMG = 3 / 60    # 3 min
HH_IA = 10 / 60    # 10 min

def load_json(filepath):
    if os.path.exists(filepath):
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                return json.load(f)
        except: return {}
    return {}

def save_json(filepath, data):
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

def generate_daily_snapshot(nuevos_count=0, duration=0):
    print("📊 Generando Snapshot de Estadísticas...")
    
    state = load_json(STATE_FILE)
    if not state:
        print("✗ No se encontró estado_productos.json")
        return

    total_productos = len(state)
    en_woo = sum(1 for p in state.values() if p.get("subido_a_woo"))
    con_imagen = sum(1 for p in state.values() if p.get("tiene_imagen"))
    con_ia = sum(1 for p in state.values() if p.get("ia_mejorado"))
    agotados = sum(1 for p in state.values() if p.get("stock", 0) <= 0)
    
    # Cálculo de HH Ahorradas
    hh_totales = (en_woo * HH_SYNC) + (con_imagen * HH_IMG) + (con_ia * HH_IA)
    
    today = datetime.now().strftime("%Y-%m-%d")
    
    # Cargar histórico existente
    historico = load_json(HISTORICO_FILE)
    if not isinstance(historico, list): historico = []
    
    # Crear nueva entrada
    snapshot = {
        "fecha": today,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "total_productos": total_productos,
        "en_woo": en_woo,
        "con_imagen": con_imagen,
        "con_ia": con_ia,
        "agotados": agotados,
        "hh_ahorradas": round(hh_totales, 2),
        "nuevos_productos": nuevos_count,
        "duracion_segundos": round(duration, 2)
    }
    
    # Evitar duplicados del mismo día (actualizar si ya existe)
    historico = [s for s in historico if s["fecha"] != today]
    historico.append(snapshot)
    
    # Mantener ordenado por fecha
    historico.sort(key=lambda x: x["fecha"])
    
    save_json(HISTORICO_FILE, historico)
    print(f"✅ Snapshot guardado para {today}. Total HH: {round(hh_totales, 2)} | Nuevos: {nuevos_count} | Duración: {round(duration, 2)}s")
    return snapshot

if __name__ == "__main__":
    generate_daily_snapshot()
