from image_bot import run_image_bot
from image_uploader import run_image_uploader

def main():
    print("="*60)
    print("🚀 PROCESO SOLO IMÁGENES: MONITORES_TV (OPTIMIZADO)")
    print("="*60)
    
    try:
        # 1. Descarga de imágenes
        # Ya no requiere driver porque descarga directo de mapa_imagenes.json
        print("\n[1/2] Iniciando descarga de imágenes para Monitores_TV...")
        descargadas = run_image_bot()
        
        # 2. Vinculación a WooCommerce
        if descargadas > 0:
            print(f"\n[2/2] Vinculando {descargadas} nuevas imágenes a WooCommerce...")
            run_image_uploader()
        else:
            print("\n[2/2] No hay nuevas imágenes para vincular.")
            
    except Exception as e:
        print(f"\n❌ Ocurrió un error: {e}")
    finally:
        print("\n✅ Proceso finalizado.")

if __name__ == "__main__":
    main()
