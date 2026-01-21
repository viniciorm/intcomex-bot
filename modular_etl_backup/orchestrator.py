# orchestrator.py
import sys
import os
from downloader import IntcomexScraper
from uploader import WooSync
from credentials import WC_URL, WC_CONSUMER_KEY, WC_CONSUMER_SECRET

def main():
    print("="*60)
    print("SISTEMA DE SINCRONIZACION ETL - INTCOMEX")
    print("="*60)
    
    # 1. EXTRACCION (Downloader)
    scraper = IntcomexScraper()
    print("\n--- FASE 1: EXTRACCION ---")
    results = scraper.run()
    
    # Verificaciones de Extracción
    if not results or not results.get("downloaded_files"):
        print("Error Critico: No se descargaron archivos CSV. Abortando proceso.")
        return

    # Verificar mapa de imágenes
    image_map_path = os.path.join(scraper.download_dir, "mapa_imagenes.json")
    if not os.path.exists(image_map_path):
        print("Advertencia: No se encontro 'mapa_imagenes.json'. La carga procedera sin fotos nuevas.")
    else:
        print(f"Mapa de imagenes listo: {len(results.get('image_map', {}))} productos mapeados.")

    print(f"Extraccion completada.")
    print(f"Valor Dolar: ${results['dollar_value']}")
    print(f"Archivos CSV listos: {len(results['downloaded_files'])}")

    # 2. CARGA (Uploader)
    print("\n--- FASE 2: CARGA (WooCommerce) ---")
    sync = WooSync(WC_URL, WC_CONSUMER_KEY, WC_CONSUMER_SECRET)
    
    try:
        final_stats = sync.process_files(
            results["downloaded_files"], 
            results["dollar_value"],
            image_map_path=image_map_path if os.path.exists(image_map_path) else None
        )

        # 3. REPORTE FINAL
        print("\n" + "="*60)
        print("REPORTE DE SINCRONIZACION")
        print("="*60)
        print(f"Total Procesados: {final_stats['total_processed']}")
        print(f"Nuevos Creados:   {final_stats['creations']}")
        print(f"Actualizados:     {final_stats['updates']}")
        print(f"Errores:          {final_stats['errors']}")
        print("="*60)
        print("Proceso terminado exitosamente.")
        
    except Exception as e:
        print(f"Error durante la fase de carga: {e}")

if __name__ == "__main__":
    main()
