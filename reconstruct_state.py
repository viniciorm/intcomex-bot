import os
import json
import pandas as pd
import io
import time
from datetime import datetime
from sync_bot import clean_price_to_float, extract_stock_number

# --- Configuración (Basada en la arquitectura centralizada) ---
DATA_PATH = "data_activa"
DOWNLOAD_DIR = "downloads"
IMAGE_DIR = "product_images"
STATE_FILE = os.path.join(DATA_PATH, "estado_productos.json")
MAP_FILE = os.path.join(DATA_PATH, "mapa_imagenes.json")

# Margen por defecto del 20%
MARGIN_PERCENTAGE = 0.20
VALOR_DOLAR_DEFAULT = 970.0 # Valor de seguridad si no se encuentra en el log

def reconstruct_state():
    print("="*60)
    print("RECONSTRUCTOR DE ESTADO: CSV -> JSON (POST-CARGA)")
    print("="*60)

    if not os.path.exists(DATA_PATH):
        os.makedirs(DATA_PATH)
        print(f"Carpeta {DATA_PATH} creada.")

    state = {}
    image_map = {}
    
    # 1. Encontrar todos los CSVs en la carpeta de descargas
    csv_files = [f for f in os.listdir(DOWNLOAD_DIR) if f.endswith('.csv') and f != 'products.csv']
    
    if not csv_files:
        print("Error: No se encontraron archivos CSV en " + DOWNLOAD_DIR)
        return

    print(f"Encontrados {len(csv_files)} categorias para procesar.")

    for csv_file in csv_files:
        category_name = csv_file.replace('.csv', '')
        file_path = os.path.join(DOWNLOAD_DIR, csv_file)
        print(f"Procesando: {category_name}")
        
        try:
            # Usar la misma lógica robusta de sync_bot
            with open(file_path, 'r', encoding='utf-16') as f:
                lines = f.readlines()
            
            header_idx = -1
            for i, line in enumerate(lines[:20]):
                l = line.lower()
                if 'sku' in l or 'categoría' in l or 'nombre' in l:
                    header_idx = i
                    break
            
            if header_idx == -1:
                print(f"  Saltando {csv_file}: No se encontro cabecera.")
                continue

            csv_content = "".join(lines[header_idx:])
            df = pd.read_csv(io.StringIO(csv_content), sep='\t', decimal=',', on_bad_lines='skip', engine='python')
            df = df.dropna(subset=[df.columns[0]])

            # Mapeo de columnas dinámico
            sku_col = next((col for col in df.columns if 'sku' in str(col).lower()), None)
            price_col = next((col for col in df.columns if 'precio' in str(col).lower()), None)
            stock_col = next((col for col in df.columns if any(x in str(col).lower() for x in ['disponibilidad', 'existencia', 'disponibil'])), None)
            desc_col = next((col for col in df.columns if any(x in str(col).lower() for x in ['nombre', 'descripción'])), None)
            cat_col = next((col for col in df.columns if 'categor' in str(col).lower() and 'sub' not in str(col).lower()), None)
            subcat_col = next((col for col in df.columns if 'subcategor' in str(col).lower()), None)

            count = 0
            for _, row in df.iterrows():
                sku = str(row[sku_col]).strip() if sku_col and pd.notna(row[sku_col]) else None
                if not sku: continue
                
                # Extraer datos básicos
                precio_usd = clean_price_to_float(row[price_col]) if price_col else 0
                stock = extract_stock_number(row[stock_col]) if stock_col else 0
                nombre = str(row[desc_col]) if desc_col else "Sin nombre"
                
                # Cálculo de precios (Usando 970 como base)
                precio_costo = round(precio_usd * VALOR_DOLAR_DEFAULT)
                precio_venta = round(precio_costo / (1 - MARGIN_PERCENTAGE))

                # Verificar imagen local
                local_img_path = os.path.join(IMAGE_DIR, f"{sku}_L.jpg")
                tiene_imagen = os.path.exists(local_img_path)
                
                # Crear entrada en el estado
                state[sku] = {
                    "sku": sku,
                    "nombre": nombre,
                    "cost_price": precio_costo,
                    "sale_price": precio_venta,
                    "stock": stock,
                    "categoria_principal": category_name,
                    "categoria_csv": str(row[cat_col]) if cat_col and pd.notna(row[cat_col]) else None,
                    "subcategoria_csv": str(row[subcat_col]) if subcat_col and pd.notna(row[subcat_col]) else None,
                    "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "tiene_imagen": tiene_imagen,
                    "imagenes_locales": [local_img_path] if tiene_imagen else [],
                    "subido_a_woo": True, # Misión: Marcarlos como subidos
                    "pendiente_sync_woo": False,
                    "procedencia": "reconstruccion_csv"
                }
                count += 1
            
            print(f"  OK: {count} SKUs agregados.")

        except Exception as e:
            print(f"  Error procesando {csv_file}: {e}")

    # 2. Guardar archivos finales
    print(f"Guardando {len(state)} productos en {STATE_FILE}...")
    with open(STATE_FILE, 'w', encoding='utf-8') as f:
        json.dump(state, f, indent=4, ensure_ascii=False)
    
    # Poblar mapa de imágenes a partir del estado reconstruido
    for sku, data in state.items():
        if data["tiene_imagen"]:
            image_map[sku] = "local_reconstructed" # No tenemos la URL original de Intcomex aquí pero sabemos que existe

    print(f"Guardando mapa de imagenes en {MAP_FILE}...")
    with open(MAP_FILE, 'w', encoding='utf-8') as f:
        json.dump(image_map, f, indent=4, ensure_ascii=False)

    print("\n" + "="*60)
    print("RECONSTRUCCION FINALIZADA CON EXITO")
    print("="*60)

if __name__ == "__main__":
    reconstruct_state()
