import os

ruta = r"C:\Users\marco\Documents\GitHub\intcomex-bot\downloads\Notebooks.csv"
output = r"c:\Users\marco\Documents\GitHub\intcomex-bot\raw_output_utf8.txt"

with open(ruta, 'r', encoding='utf-16') as f_in:
    lines = f_in.readlines()
    with open(output, 'w', encoding='utf-8') as f_out:
        f_out.write("--- RAW LINE 3 (HEADER) ---\n")
        f_out.write(repr(lines[2]) + "\n")
        f_out.write("\n--- RAW LINE 4 (DATA) ---\n")
        f_out.write(repr(lines[3]) + "\n")
