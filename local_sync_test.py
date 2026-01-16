import os
import sys

# Forzar encoding UTF-8 para la salida de consola
if sys.stdout.encoding != 'utf-8':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from sync_bot import (
    init_woocommerce_api, 
    sincronizar_csv, 
    WC_URL
)

# Configuración
DOWNLOAD_DIR = os.path.join(os.getcwd(), "downloads")
VALOR_DOLAR_FIJO = 890.0  # Valor detectado en la ejecución anterior

def run_local_sync():
    print("="*60)
    print("INICIANDO SINCRONIZACION LOCAL (Modo Test)")
    print("="*60)
    
    # 1. Inicializar WooCommerce
    print(f"Conectando con WooCommerce ({WC_URL})...")
    wcapi = init_woocommerce_api()
    
    # 2. Localizar archivo
    archivo = os.path.join(DOWNLOAD_DIR, "Notebooks.csv")
    
    if not os.path.exists(archivo):
        print(f"Error: No se encuentra el archivo {archivo}")
        print("Asegurate de que el bot lo haya descargado previamente.")
        return

    # 3. Ejecutar sincronizacion
    print(f"Procesando archivo local: {archivo}")
    stats = sincronizar_csv(archivo, wcapi, "Notebooks", VALOR_DOLAR_FIJO)
    
    # 4. Mostrar resultados
    print("\n" + "="*60)
    print("📊 RESUMEN DE EJECUCIÓN")
    print("="*60)
    print(f"✅ Productos procesados: {stats['procesados']}")
    print(f"⭐ Creados:           {stats['creados']}")
    print(f"🔄 Actualizados:      {stats['actualizados']}")
    print(f"🚫 Filtrados:         {stats['filtrados']}")
    print(f"⚠️ Errores:           {stats['errores']}")
    print("="*60)

if __name__ == "__main__":
    run_local_sync()
