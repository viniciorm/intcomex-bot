import time
import sys
import os

# Cambiar al directorio de desarrollo para asegurar importaciones locales
os.chdir(os.path.dirname(os.path.abspath(__file__)))

from ia_webhook_trigger import run_ia_webhook_trigger
from image_uploader import run_image_uploader
from image_bot import run_image_bot

def benchmark():
    print("🏁 INICIANDO BENCHMARK VINI-TURBO")
    print("="*40)
    
    # Prueba IA con límite de 3
    start = time.time()
    print("\n[TEST] Ejecutando IA (Límite 3)...")
    run_ia_webhook_trigger() # El script ya tiene sus límites internos si queremos, o procesará lo que haya en el JSON de desarrollo
    ia_duration = time.time() - start
    print(f"⏱️ Tiempo IA Parallel: {ia_duration:.2f}s")

    # Prueba Uploader con límite
    start = time.time()
    print("\n[TEST] Ejecutando Uploader...")
    run_image_uploader()
    up_duration = time.time() - start
    print(f"⏱️ Tiempo Uploader Batch: {up_duration:.2f}s")

    print("\n" + "="*40)
    print(f"🚀 TOTAL BENCHMARK: {ia_duration + up_duration:.2f}s")
    print("="*40)

if __name__ == "__main__":
    benchmark()
