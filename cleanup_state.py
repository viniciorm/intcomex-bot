import json
import os
import shutil
from datetime import datetime

# Configuración
DATA_PATH = "data_activa"
STATE_FILE = os.path.join(DATA_PATH, "estado_productos.json")
BACKUP_FILE = os.path.join(DATA_PATH, f"estado_productos_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")

# Diccionario de validación (sincronizado con sync_bot.py)
CATEGORY_VALIDATION = {
    "Notebooks": ["Notebook", "Portátiles", "Laptops"],
    "Monitores": ["Monitores", "Monitor", "Pantallas"],
    "Monitores_TV": ["Televisores", "TV", "Monitores"],
    "Desktop": ["Desktop", "Computadores", "CPU"],
    "Tablets": ["Tablet", "Tabletas"],
    "Impresoras_Inkjet": ["Inkjet", "Inyección"],
    "Impresoras_Label": ["Label", "Etiquetas"],
    "Impresoras_Laser": ["Laser", "Láser"],
    "Impresoras_MFP": ["Multifuncionales", "Multifunción", "MFP"],
    "Scanners": ["Scanner", "Escáner"],
    "All_in_One": ["Todo-en-Uno", "All-in-One"]
}

def cleanup():
    print("="*60)
    print("🧹 SCRIPT DE LIMPIEZA DE ESTADO: INTCOMEX BOT")
    print("="*60)
    
    if not os.path.exists(STATE_FILE):
        print(f"❌ No se encontró el archivo {STATE_FILE}")
        return

    # 1. Crear respaldo
    print(f"📦 Creando respaldo en: {BACKUP_FILE}")
    shutil.copy2(STATE_FILE, BACKUP_FILE)

    # 2. Cargar estado
    try:
        with open(STATE_FILE, 'r', encoding='utf-8') as f:
            state = json.load(f)
    except Exception as e:
        print(f"❌ Error al cargar el JSON: {e}")
        return

    initial_count = len(state)
    print(f"🔍 Productos iniciales registrados: {initial_count}")

    # 3. Limpieza por validación de categoría
    cleaned_state = {}
    removed_count = 0
    
    for sku, data in state.items():
        main_cat = data.get("categoria_principal", "")
        csv_cat = str(data.get("categoria_csv", "")).lower()
        csv_subcat = str(data.get("subcategoria_csv", "")).lower()
        full_csv_text = csv_cat + " " + csv_subcat
        
        valid_keywords = CATEGORY_VALIDATION.get(main_cat, [])
        
        if valid_keywords:
            # Si la categoría tiene reglas de validación, aplicarlas
            if not any(kw.lower() in full_csv_text for kw in valid_keywords):
                if removed_count < 10: # Mostrar los primeros 10 para debug
                    print(f"  🗑️ Filtrando SKU {sku}: {data.get('nombre')[:40]}...")
                    print(f"      - Cat Principal: {main_cat}")
                    print(f"      - Cat CSV: {csv_cat} / {csv_subcat}")
                elif removed_count == 10:
                    print("  ... más productos filtrados ...")
                    
                removed_count += 1
                continue
        
        # Mantener el producto
        cleaned_state[sku] = data

    # 4. Guardar estado limpio
    print("\n" + "="*60)
    print(f"✅ Limpieza completada.")
    print(f"📊 Productos eliminados: {removed_count}")
    print(f"📊 Productos restantes: {len(cleaned_state)}")
    print("="*60)

    try:
        with open(STATE_FILE, 'w', encoding='utf-8') as f:
            json.dump(cleaned_state, f, indent=4, ensure_ascii=False)
        print(f"💾 Archivo {STATE_FILE} actualizado exitosamente.")
    except Exception as e:
        print(f"❌ Error al guardar el archivo: {e}")

if __name__ == "__main__":
    cleanup()
