# orchestrator.py
import sys
import os
from downloader import IntcomexScraper
from uploader import WooSync
from credentials import WC_URL, WC_CONSUMER_KEY, WC_CONSUMER_SECRET

def main():
    print("="*60)
    print("🤖 SISTEMA DE SINCRONIZACIÓN ETL - INTCOMEX")
    print("="*60)
    
    # 1. EXTRACCIÓN (Downloader)
    scraper = IntcomexScraper()
    print("\n--- FASE 1: EXTRACCIÓN ---")
    results = scraper.run()
    
    if not results or not results["downloaded_files"]:
        print("❌ Error: No se descargaron archivos. Abortando.")
        return

    print(f"\n✅ Extracción completada.")
    print(f"💵 Dólar: {results['dollar_value']}")
    print(f"📂 Archivos: {len(results['downloaded_files'])}")
    print(f"🖼️ Imágenes recolectadas: {len(results['image_map'])}")

    # 2. CARGA (Uploader)
    print("\n--- FASE 2: CARGA ---")
    sync = WooSync(WC_URL, WC_CONSUMER_KEY, WC_CONSUMER_SECRET)
    
    final_stats = sync.process_files(
        results["downloaded_files"], 
        results["dollar_value"], 
        results["image_map"]
    )

    # 3. REPORTE FINAL
    print("\n" + "="*60)
    print("📊 REPORTE DE SINCRONIZACIÓN")
    print("="*60)
    print(f"Total Procesados: {final_stats['total_processed']}")
    print(f"Creados:          {final_stats['creations']}")
    print(f"Actualizados:     {final_stats['updates']}")
    print(f"Errores:          {final_stats['errors']}")
    print("="*60)
    print("✨ Proceso terminado.")

if __name__ == "__main__":
    main()
