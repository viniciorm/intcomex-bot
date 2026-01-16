import os
import pandas as pd

ruta = r"C:\Users\marco\Documents\GitHub\intcomex-bot\downloads\Notebooks.csv"

with open(ruta, 'r', encoding='utf-16') as f:
    lines = f.readlines()
    print("--- RAW LINE 3 (HEADER) ---")
    print(repr(lines[2]))  # Fila 3 es índice 2
    print("\n--- RAW LINE 4 (DATA) ---")
    print(repr(lines[3]))
