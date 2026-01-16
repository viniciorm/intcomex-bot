import io
import json
import re
from woocommerce import API

    def __init__(self, url, consumer_key, consumer_secret):
        self.wcapi = API(
            url=url,
            consumer_key=consumer_key,
            consumer_secret=consumer_secret,
            version="wc/v3",
            timeout=60
        )
        self.margin_percentage = 0.20
        self.category_cache = {} # Cache para no consultar la API repetidamente

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

    def get_or_create_category(self, name, parent_id=0):
        """Busca o crea una categoría en WooCommerce y retorna su ID."""
        name = str(name).strip().title()
        cache_key = f"{name}_{parent_id}"
        
        if cache_key in self.category_cache:
            return self.category_cache[cache_key]
            
        # Buscar categoría por nombre
        response = self.woocommerce_request("get", "products/categories", params={"search": name})
        if response:
            categories = response.json()
            for cat in categories:
                if cat['name'].lower() == name.lower() and cat['parent'] == parent_id:
                    self.category_cache[cache_key] = cat['id']
                    return cat['id']
                    
        # Si no existe, crearla
        print(f"    📁 Creando nueva categoría: {name} (parent: {parent_id})")
        data = {"name": name, "parent": parent_id}
        response = self.woocommerce_request("post", "products/categories", data=data)
        if response:
            new_cat = response.json()
            self.category_cache[cache_key] = new_cat['id']
            return new_cat['id']
            
        return 0

    def find_product_by_sku(self, sku):
        response = self.woocommerce_request("get", "products", params={"sku": str(sku)})
        if response:
            products = response.json()
            return products[0] if products else None
        return None

    def process_files(self, file_list, dollar_value, image_map_path="downloads/mapa_imagenes.json"):
        stats = {"total_processed": 0, "updates": 0, "creations": 0, "errors": 0}
        
        # Cargar mapa de imágenes desde JSON
        image_map = {}
        if os.path.exists(image_map_path):
            try:
                with open(image_map_path, 'r', encoding='utf-8') as f:
                    image_map = json.load(f)
                print(f"📂 Mapa de imágenes cargado: {len(image_map)} SKUs")
            except Exception as e:
                print(f"⚠️ Error al cargar mapa de imágenes: {e}")

        for file_path in file_list:
            cat_name = os.path.basename(file_path).replace(".csv", "")
            print(f"\n🚀 Sincronizando categoría desde archivo: {cat_name}")
            
            try:
                # Lectura robusta con StringIO
                with open(file_path, 'r', encoding='utf-16') as f:
                    lines = f.readlines()
                
                header_idx = -1
                for i, line in enumerate(lines[:20]):
                    if 'sku' in line.lower() or 'categoría' in line.lower() or 'categoria' in line.lower():
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
                parent_cat_col = next((c for c in df.columns if 'categoría' in c.lower() or 'categoria' in c.lower()), None)
                sub_cat_col = next((c for c in df.columns if 'subcategoría' in c.lower() or 'subcategoria' in c.lower()), None)
                
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
                        
                        # Gestión de Categorías
                        id_cat_final = 0
                        if parent_cat_col and sub_cat_col:
                            parent_name = str(row[parent_cat_col])
                            sub_name = str(row[sub_cat_col])
                            if parent_name != 'nan' and sub_name != 'nan':
                                id_padre = self.get_or_create_category(parent_name)
                                id_cat_final = self.get_or_create_category(sub_name, parent_id=id_padre)

                        product_data = {
                            "name": str(row[name_col]),
                            "type": "simple",
                            "regular_price": str(precio_clp),
                            "sku": sku,
                            "manage_stock": True,
                            "stock_quantity": stock,
                            "status": "publish"
                        }
                        
                        if id_cat_final > 0:
                            product_data["categories"] = [{"id": id_cat_final}]
                        
                        existing = self.find_product_by_sku(sku)
                        if existing:
                            # Update (No tocamos imágenes en update por velocidad)
                            res = self.woocommerce_request("put", f"products/{existing['id']}", data={
                                "regular_price": str(precio_clp),
                                "stock_quantity": stock
                            })
                            if res: stats["updates"] += 1
                        else:
                            # Create (Agregar imagen si existe match en el mapa)
                            if sku in image_map:
                                product_data["images"] = [{"src": image_map[sku]}]
                                print(f"    🖼️ Imagen vinculada para nuevo producto: {sku}")
                                
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
