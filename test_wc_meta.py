from woocommerce import API
from credentials import WC_URL, WC_CONSUMER_KEY, WC_CONSUMER_SECRET

wcapi = API(url=WC_URL, consumer_key=WC_CONSUMER_KEY, consumer_secret=WC_CONSUMER_SECRET, version='wc/v3', timeout=30)
sku = 'NT096DEL32'
print(f"Buscando {sku}...")
res = wcapi.get('products', params={'sku': sku}).json()
if not res:
    print("No encotrado")
    exit(1)

p = res[0]
print(f"Producto ID: {p['id']}")

meta_update = [{'key': 'n8n_mejorado', 'value': 'false'}]
print(f"Aplicando meta_data: {meta_update}")
update_res = wcapi.put(f"products/{p['id']}", data={'meta_data': meta_update})
print(f"Status PUT: {update_res.status_code}")
updated_p = update_res.json()

found = [m for m in updated_p.get('meta_data', []) if m.get('key') == 'n8n_mejorado']
print(f"Resultado meta_data: {found}")
