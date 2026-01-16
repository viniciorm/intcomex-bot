import os
import pandas as pd
import sys

# Forzar encoding UTF-8 para la salida de consola
if sys.stdout.encoding != 'utf-8':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

ruta = r"C:\Users\marco\Documents\GitHub\intcomex-bot\downloads\Notebooks.csv"

print(f"🔍 ANALIZANDO COLUMNAS CON PANDAS: {ruta}")

if not os.path.exists(ruta):
    print("❌ El archivo no existe.")
    exit()

try:
    df = pd.read_csv(
        ruta,
        encoding='utf-16',
        sep='\t',
        header=2,
        decimal=',',
        on_bad_lines='skip'
    )
    
    print(f"\n✅ Archivo cargado exitosamente.")
    print(f"📊 Total de filas: {len(df)}")
    print(f"📋 Columnas encontradas (exactas):")
    for i, col in enumerate(df.columns):
        # Limpiar posibles caracteres extraños en los nombres de las columnas
        clean_col = str(col).encode('ascii', 'ignore').decode('ascii')
        print(f"   [{i}] '{col}' (Limpio: '{clean_col}')")
    
    # Mostrar la primera fila completa para ver los datos debajo de cada columna
    if not df.empty:
        print("\n👀 Datos de la primera fila:")
        first_row = df.iloc[0]
        for col in df.columns:
            print(f"   {col}: {first_row[col]}")

except Exception as e:
    print(f"❌ Error al leer con pandas: {e}")
