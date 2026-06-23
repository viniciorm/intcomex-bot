import requests
import re
import json

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

# Cargar 5 SKUs sin imagen
try:
    r = requests.get('http://166.0.112.6:8000/data_activa/estado_productos.json').json()
    skus = [sku for sku, data in r.items() if not data.get("tiene_imagen")][:5]
    print("Testing SKUs:", skus)
    
    for sku in skus:
        url = f"https://store.intcomex.com/es-XCL/Products/ByKeyword?term=+{sku}"
        resp = requests.get(url, headers=headers, timeout=10)
        
        # Buscar src de imagenes que contengan /images/products/
        img_srcs = re.findall(r'src=["\']([^"\']*/images/products/[^"\']+)["\']', resp.text)
        # O también data-original
        data_origs = re.findall(r'data-original=["\']([^"\']*/images/products/[^"\']+)["\']', resp.text)
        
        all_found = img_srcs + data_origs
        print(f"\nSKU: {sku} - Status: {resp.status_code}")
        print(f"  Found images: {all_found}")
        
except Exception as e:
    print("Error:", e)
