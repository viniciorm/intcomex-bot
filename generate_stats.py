import os
import json
from datetime import datetime

# --- Configuración ---
DATA_PATH = "data_activa"
STATE_FILE = os.path.join(DATA_PATH, "estado_productos.json")
HISTORICO_FILE = os.path.join(DATA_PATH, "historico_stats.json")

# Lógica de HH (Horas Hombre) ahorradas por producto
HH_SYNC = 5 / 60   # 5 min (Estructural: Creación inicial)
HH_IMG = 3 / 60    # 3 min (Estructural: Búsqueda de imagen)
HH_IA = 10 / 60    # 10 min (Estructural: Enriquecimiento)
HH_MANTENCION = 1 / 60 # 1 min (Operacional: Revisión diaria de precio/stock por producto)

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
    
    # Cálculo de HH Ahorradas Estructurales (Una sola vez por producto)
    hh_estructurales = (en_woo * HH_SYNC) + (con_imagen * HH_IMG) + (con_ia * HH_IA)
    
    # Cálculo de HH Operacionales de esta ejecución (Revisar precios/stock de todo el catálogo)
    hh_mantencion_run = total_productos * HH_MANTENCION
    
    today = datetime.now().strftime("%Y-%m-%d")
    
    # Cargar histórico existente
    historico = load_json(HISTORICO_FILE)
    if not isinstance(historico, list): historico = []
    
    # Obtener HH estructurales de ayer para el delta
    hh_ayer = 0
    hh_mantencion_acumulada_historica = 0
    if historico:
        # Filtrar por fecha distinta a hoy
        entradas_anteriores = [s for s in historico if s["fecha"] != today]
        if entradas_anteriores:
            hh_ayer = entradas_anteriores[-1].get("hh_estructurales", entradas_anteriores[-1].get("hh_ahorradas", 0))
            
        # Sumar toda la mantencion acumulada en el pasado
        for s in entradas_anteriores:
            hh_mantencion_acumulada_historica += s.get("hh_mantencion_diaria", 0)

    # Las HH ganadas HOY por estructura (productos nuevos)
    hh_ganadas_estructura = max(0, hh_estructurales - hh_ayer)
    
    # Obtener entrada de hoy si existe para sumar
    entrada_hoy = next((s for s in historico if s["fecha"] == today), None)
    
    if entrada_hoy:
        nuevos_count_total = entrada_hoy.get("nuevos_productos", 0) + nuevos_count
        duration_total = entrada_hoy.get("duracion_segundos", 0) + duration
        hh_mantencion_diaria = entrada_hoy.get("hh_mantencion_diaria", 0) + hh_mantencion_run
    else:
        nuevos_count_total = nuevos_count
        duration_total = duration
        hh_mantencion_diaria = hh_mantencion_run

    # Las HH ganadas HOY totales = Nuevos productos + La revisión del catálogo
    hh_hoy_ganadas = hh_ganadas_estructura + hh_mantencion_diaria
    
    # El Total Histórico = Estructurales actuales + Toda la mantención pasada + La mantención de hoy
    hh_totales = hh_estructurales + hh_mantencion_acumulada_historica + hh_mantencion_diaria

    # Calcular Velocidad (Human vs Bot)
    velocidad = 0
    if duration_total > 0 and hh_hoy_ganadas > 0:
        horas_bot = duration_total / 3600
        velocidad = round(hh_hoy_ganadas / horas_bot, 1)

    # Crear nueva entrada
    snapshot = {
        "fecha": today,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "total_productos": total_productos,
        "en_woo": en_woo,
        "con_imagen": con_imagen,
        "con_ia": con_ia,
        "agotados": agotados,
        "hh_estructurales": round(hh_estructurales, 2),
        "hh_mantencion_diaria": round(hh_mantencion_diaria, 2),
        "hh_ahorradas": round(hh_totales, 2),
        "hh_ganadas_hoy": round(hh_hoy_ganadas, 2),
        "velocidad": velocidad,
        "nuevos_productos": nuevos_count_total,
        "duracion_segundos": round(duration_total, 2)
    }
    
    # Evitar duplicados del mismo día (actualizar si ya existe)
    historico = [s for s in historico if s["fecha"] != today]
    historico.append(snapshot)
    
    # Mantener ordenado por fecha
    historico.sort(key=lambda x: x["fecha"])
    
    save_json(HISTORICO_FILE, historico)
    print(f"✅ Snapshot guardado para {today}.")
    print(f"   Total HH: {round(hh_totales, 2)} | Ganadas Hoy: {round(hh_hoy_ganadas, 2)} | Velocidad: {velocidad}x")
    return snapshot

if __name__ == "__main__":
    generate_daily_snapshot()
