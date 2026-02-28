import os
import json
import requests
import time

STATE_FILE = "data_activa/estado_productos.json"
# Configura aqui la URL de webhook que te da n8n cuando lo importes y lo publiques
N8N_WEBHOOK_URL = "http://localhost:5678/webhook/mejorar-productos-ia" 

def run_ia_webhook_trigger():
    print("\n==================================================")
    print("🧠 INICIANDO TRIGGER IA BOT (n8n Webhook)")
    print("==================================================")
    
    if not os.path.exists(STATE_FILE):
        print("✗ No se encontró estado_productos.json. Terminando.")
        return 0
        
    try:
        with open(STATE_FILE, 'r', encoding='utf-8') as f:
            estado = json.load(f)
    except Exception as e:
        print(f"✗ Error al leer estado_productos.json: {e}")
        return 0

    # Filtrar: subidos a Woo = True
    skus_a_procesar = []
    
    for sku, data in estado.items():
        # Aquí puedes agregar validaciones extras (ej. que no haya sido procesado por IA antes)
        if data.get("subido_a_woo", False):
            skus_a_procesar.append(sku)
            
    if not skus_a_procesar:
        print("✓ No hay SKUs pendientes de mejora IA (o subidos a Woo).")
        return 0
        
    print(f"✓ Se encontraron {len(skus_a_procesar)} SKUs subidos a Woo.")
    
    # Enviar en lotes (ej: de a 50) para no saturar la petición POST
    batch_size = 50
    total_enviados = 0
    
    for i in range(0, len(skus_a_procesar), batch_size):
        lote = skus_a_procesar[i:i + batch_size]
        print(f"  📤 Enviando lote de {len(lote)} SKUs a n8n...")
        
        payload = {
            "skus": lote
        }
        
        try:
            response = requests.post(N8N_WEBHOOK_URL, json=payload, timeout=15)
            if response.status_code in [200, 201]:
                print(f"  ✓ Lote recibido por n8n correctamente.")
                total_enviados += len(lote)
            else:
                print(f"  ✗ Error enviando webhook a n8n. Code: {response.status_code} - {response.text}")
        except Exception as e:
            print(f"  ✗ Error de conexión con Webhook de n8n: {e}")
            print(f"  (Asegúrate de haber activado el workflow en n8n y tener la URL correcta)")
            
        time.sleep(2) # Pausa entre lotes
        
    print(f"\n✅ Total de SKUs enviados a n8n: {total_enviados}")
    return total_enviados

if __name__ == "__main__":
    run_ia_webhook_trigger()
