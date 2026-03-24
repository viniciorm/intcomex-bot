from woocommerce import API
import json
from credentials import WC_URL, WC_CONSUMER_KEY, WC_CONSUMER_SECRET

wcapi = API(
    url=WC_URL,
    consumer_key=WC_CONSUMER_KEY,
    consumer_secret=WC_CONSUMER_SECRET,
    version="wc/v3",
    timeout=30
)

skus_to_verify = [
    "TA106SAM03", "TA105SAM66", "TA105SAM92", "TA106SAM07",
    "PC001ASU76", "PC001ASU77", "PC001ASU79", "PC001ASU78",
    "CP991AMD61-B1"
]

print(f"{'SKU':<15} | {'Mejorado':<8} | {'ID':<6} | {'Descripción Corta (Vista)'}")
print("-" * 70)

results = []
for sku in skus_to_verify:
    res = wcapi.get("products", params={"sku": sku}).json()
    if not res:
        print(f"{sku:<15} | {'NO ENCONTRADO':<8}")
        continue
    
    p = res[0]
    meta = p.get("meta_data", [])
    mejorado = any(m.get("key") == "n8n_mejorado" and str(m.get("value")).lower() == "true" for m in meta)
    
    desc = p.get("description", "")
    has_html = "<ul>" in desc or "<li>" in desc or "<strong>" in desc
    
    status = "SÍ" if mejorado else "NO"
    preview = desc[:50].replace('\n', ' ') + "..." if desc else "VACÍA"
    
    print(f"{sku:<15} | {status:<8} | {p['id']:<6} | {preview}")
    
    results.append({
        "sku": sku,
        "id": p['id'],
        "mejorado": mejorado,
        "has_html": has_html,
        "desc_preview": preview
    })

print("\nVerificación terminada.")
