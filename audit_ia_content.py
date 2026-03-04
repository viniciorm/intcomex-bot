import os
import json
from woocommerce import API

try:
    from credentials import WC_URL, WC_CONSUMER_KEY, WC_CONSUMER_SECRET
except ImportError:
    print("Error cargando credenciales.")
    exit(1)

DATA_PATH = "data_activa"
STATE_FILE = os.path.join(DATA_PATH, "estado_productos.json")

wcapi = API(
    url=WC_URL,
    consumer_key=WC_CONSUMER_KEY,
    consumer_secret=WC_CONSUMER_SECRET,
    version="wc/v3",
    timeout=60
)

def looks_like_ai_content(html):
    """
    Detecta si el contenido parece enriquecido por IA basado en etiquetas HTML 
    que nuestro prompt exige (ul, li, strong).
    """
    if not html: return False
    html_lower = html.lower()
    # Si tiene estructura de lista o negritas extensas, asumimos que es IA
    triggers = ['<ul>', '<li>', '<strong>']
    count = sum(1 for t in triggers if t in html_lower)
    return count >= 2

def audit_descriptions():
    print("🔍 Iniciando auditoría real de descripciones en WooCommerce...")
    if not os.path.exists(STATE_FILE):
        print("Error: No existe el archivo de estado local.")
        return

    with open(STATE_FILE, 'r', encoding='utf-8') as f:
        state = json.load(f)

    subidos = [sku for sku, data in state.items() if data.get("subido_a_woo")]
    print(f"Productos a auditar: {len(subidos)}")

    enriched_count = 0
    basic_count = 0
    
    for i, sku in enumerate(subidos, 1):
        if i % 20 == 0: print(f"Auditando {i}/{len(subidos)}...")
        
        try:
            res = wcapi.get("products", params={"sku": sku}).json()
            if res:
                p = res[0]
                desc = p.get("description", "")
                
                if looks_like_ai_content(desc):
                    state[sku]["ia_mejorado"] = True
                    enriched_count += 1
                else:
                    state[sku]["ia_mejorado"] = False
                    basic_count += 1
        except Exception as e:
            print(f"Error auditando {sku}: {e}")
            continue

    with open(STATE_FILE, 'w', encoding='utf-8') as f:
        json.dump(state, f, indent=4, ensure_ascii=False)
    
    print("\n" + "="*50)
    print("✅ AUDITORÍA FINALIZADA")
    print(f"Productos con IA detectada: {enriched_count}")
    print(f"Productos con descripción básica: {basic_count}")
    print("El archivo JSON local ha sido sincronizado con la realidad de la tienda.")
    print("="*50)

if __name__ == "__main__":
    audit_descriptions()
