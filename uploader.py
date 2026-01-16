# uploader.py
import os
import time
import pandas as pd
import io
from woocommerce import API

class WooSync:
    def __init__(self, url, consumer_key, consumer_secret):
        self.wcapi = API(
            url=url,
            consumer_key=consumer_key,
            consumer_secret=consumer_secret,
            version="wc/v3",
            timeout=60
        )
        self.margin_percentage = 0.20

    def woocommerce_request(self, method, endpoint, data=None, params=None, max_retries=3):
        for attempt in range(max_retries):
            try:
                if method.lower() == 'get':
                    response = self.wcapi.get(endpoint, params=params)
                elif method.lower() == 'post':
                    response = self.wcapi.post(endpoint, data=data)
                elif method.lower() == 'put':
                    response = self.wcapi.put(endpoint, data=data)
                else: return None
                
                if response.status_code in [200, 201]:
                    return response
                else:
                    print(f"    ⚠️ Error API (HTTP {response.status_code}): {response.text[:200]}")
            except Exception as e:
                if attempt < max_retries - 1:
                    wait = (attempt + 1) * 5
                    print(f"    ⚠️ Error de red... Reintentando en {wait}s ({attempt+1}/{max_retries})")
                    time.sleep(wait)
                else:
                    print(f"    ❌ Fallo crítico tras {max_retries} reintentos.")
                    return None
        return None

    def find_product_by_sku(self, sku):
        response = self.woocommerce_request("get", "products", params={"sku": str(sku)})
        if response:
            products = response.json()
            return products[0] if products else None
        return None

    def process_files(self, file_list, dollar_value, image_map):
        stats = {"total_processed": 0, "updates": 0, "creations": 0, "errors": 0}
        
        for file_path in file_list:
            cat_name = os.path.basename(file_path).replace(".csv", "")
            print(f"\n🚀 Sincronizando categoría: {cat_name}")
            
            try:
                # Lectura robusta con StringIO
                with open(file_path, 'r', encoding='utf-16') as f:
                    lines = f.readlines()
                
                header_idx = -1
                for i, line in enumerate(lines[:20]):
                    if 'sku' in line.lower() or 'categoría' in line.lower():
                        header_idx = i
                        break
                
                if header_idx == -1: 
                    print(f"❌ No se encontró cabecera en {file_path}")
                    continue
                
                csv_content = "".join(lines[header_idx:])
                df = pd.read_csv(io.StringIO(csv_content), sep='\t', decimal=',', engine='python')
                
                # Mapeo de columnas
                sku_col = next((c for c in df.columns if 'sku' in c.lower()), None)
                price_col = next((c for c in df.columns if 'precio' in c.lower()), None)
                stock_col = next((c for c in df.columns if 'disponibilidad' in c.lower()), None)
                name_col = next((c for c in df.columns if 'nombre' in c.lower()), None)
                
                for _, row in df.iterrows():
                    try:
                        sku = str(row[sku_col]).strip()
                        if not sku or sku == 'nan': continue
                        
                        price_usd = float(str(row[price_col]).replace(',', '.'))
                        precio_clp = round((price_usd * dollar_value) / (1 - self.margin_percentage))
                        
                        # Extraer stock
                        stock_text = str(row[stock_col]).lower()
                        stock_nums = re.findall(r'\d+', stock_text)
                        stock = int(stock_nums[0]) if stock_nums else (20 if 'más' in stock_text or 'mas' in stock_text else 0)
                        
                        product_data = {
                            "name": str(row[name_col]),
                            "type": "simple",
                            "regular_price": str(precio_clp),
                            "sku": sku,
                            "manage_stock": True,
                            "stock_quantity": stock,
                            "status": "publish"
                        }
                        
                        # Agregar imagen desde el mapa si existe
                        if sku in image_map:
                            product_data["images"] = [{"src": image_map[sku]}]
                        
                        existing = self.find_product_by_sku(sku)
                        if existing:
                            # Update
                            res = self.woocommerce_request("put", f"products/{existing['id']}", data={
                                "regular_price": str(precio_clp),
                                "stock_quantity": stock
                            })
                            if res: stats["updates"] += 1
                        else:
                            # Create
                            res = self.woocommerce_request("post", "products", data=product_data)
                            if res: stats["creations"] += 1
                        
                        stats["total_processed"] += 1
                        print(f"   ✅ SKU {sku} sincronizado. (${precio_clp} CLP, Stock: {stock})")
                        time.sleep(2) # Respetar el límite de la API
                        
                    except Exception as e:
                        print(f"   ⚠️ Error en SKU {sku}: {e}")
                        stats["errors"] += 1
                        
            except Exception as e:
                print(f"❌ Error al procesar archivo {file_path}: {e}")
                
        return stats

import re
