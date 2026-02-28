from image_bot import run_image_bot, save_state, load_state
import os
import json

def test_fix():
    print("="*60)
    print("🧪 TEST: VERIFICACIÓN DE ARREGLO DE IMÁGENES")
    print("="*60)
    
    sku_test = "PT101BRO28"
    state = load_state()
    
    # Asegurar que el SKU esté en el estado y marcado como sin imagen para el test
    if sku_test not in state:
        state[sku_test] = {
            "sku": sku_test,
            "nombre": "Brother Impresa Termica QL1110NWB (Test)",
            "stock": 10,
            "tiene_imagen": False
        }
    else:
        state[sku_test]["tiene_imagen"] = False
        state[sku_test]["stock"] = 10 # Asegurar stock > 0 para que el bot lo procese
    
    save_state(state)
    
    print(f"🔍 Iniciando bot para procesar únicamente el SKU: {sku_test}")
    # Ejecutamos el bot pasando una lista con solo nuestro SKU de prueba
    # Usamos headless=False para poder ver si falla algo (opcional, pero run_image_bot es headless por defecto)
    run_image_bot(skus_to_process=[sku_test])
    
    # Verificar resultado
    updated_state = load_state()
    if updated_state.get(sku_test, {}).get("tiene_imagen"):
        print(f"\n✅ ÉXITO: Imagen encontrada y descargada para {sku_test}")
        print(f"📍 Ruta local: {updated_state[sku_test].get('imagenes_locales')}")
    else:
        print(f"\n❌ FALLO: No se pudo obtener la imagen para {sku_test}")

if __name__ == "__main__":
    test_fix()
