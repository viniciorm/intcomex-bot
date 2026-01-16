import os
import pandas as pd
import sys

# Forzar encoding UTF-8 para la salida de consola
if sys.stdout.encoding != 'utf-8':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

ruta = r"C:\Users\marco\Documents\GitHub\intcomex-bot\downloads\Notebooks.csv"

# 1. Leer RAW
with open(ruta, 'r', encoding='utf-16') as f:
    lines = f.readlines()

# 2. Encontrar cabecera
header_idx = -1
for i, line in enumerate(lines[:10]):
    l = line.lower()
    if 'sku' in l or 'categoría' in l:
        header_idx = i
        break

print(f"Header detectado en linea: {header_idx}")

if header_idx != -1:
    # 3. Intentar cargar con pandas usando las lineas filtradas
    import io
    csv_data = "".join(lines[header_idx:])
    df = pd.read_csv(io.StringIO(csv_data), sep='\t', decimal=',', engine='python')
    print(f"Pandas cargo exitosamente {len(df)} filas.")
    print(f"Columnas: {list(df.columns)}")
    print(f"Primera fila: {df.iloc[0].to_dict()}")
