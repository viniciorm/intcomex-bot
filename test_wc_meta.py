from woocommerce import API
from credentials import WC_URL, WC_CONSUMER_KEY, WC_CONSUMER_SECRET

wcapi = API(url=WC_URL, consumer_key=WC_CONSUMER_KEY, consumer_secret=WC_CONSUMER_SECRET, version='wc/v3', timeout=30)
sku = 'NT096DEL32'
print(f"Buscando {sku}...")
res_raw = wcapi.get('products', params={'sku': sku})
print(f"Status GET: {res_raw.status_code}")
try:
    res = res_raw.json()
except Exception as e:
    print(f"Error decodificando JSON: {e}")
    print(f"Respuesta bruta (primeros 500 chars): {res_raw.text[:500]}")
    exit(1)

if not res:
    print("No encontrado")
    exit(1)

p = res[0]
print(f"Producto ID: {p['id']}")

meta_update = [{'key': 'n8n_mejorado', 'value': 'false'}]
print(f"Aplicando meta_data: {meta_update}")
update_res = wcapi.put(f"products/{p['id']}", data={'meta_data': meta_update})
print(f"Status PUT: {update_res.status_code}")
try:
    updated_p = update_res.json()
except Exception as e:
    print(f"Error decodificando respuesta PUT: {e}")
    print(f"Respuesta bruta PUT: {update_res.text[:500]}")
    exit(1)

found = [m for m in updated_p.get('meta_data', []) if m.get('key') == 'n8n_mejorado']
print(f"Resultado meta_data: {found}")

