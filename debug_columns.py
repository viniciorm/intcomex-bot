import os
import pandas as pd

ruta = r"C:\Users\marco\Documents\GitHub\intcomex-bot\downloads\Notebooks.csv"

# Leer el CSV tal cual lo hace el bot
df = pd.read_csv(
    ruta,
    encoding='utf-16',
    sep='\t',
    header=2,
    decimal=',',
    on_bad_lines='skip'
)

print(f"Columnas detectadas: {list(df.columns)}")
print("\nPrimeras 2 filas con sus nombres de columnas:")
for idx, row in df.head(2).iterrows():
    print(f"\nFila {idx}:")
    for col in df.columns:
        print(f"  [{col}]: {repr(row[col])}")
