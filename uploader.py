import os
import time
import re
import io
import json
import pandas as pd
from woocommerce import API

class WooSync:
    """
    Clase responsable de la carga de datos (Load) hacia WooCommerce.
    Implementa lógica de categorías jerárquicas, mapeo de imágenes y filtros de negocio.
    """
    
    def __init__(self, url, consumer_key, consumer_secret):
        self.wcapi = API(
            url=url,
            consumer_key=consumer_key,
            consumer_secret=consumer_secret,
            version="wc/v3",
            timeout=60
        )
        self.margin_percentage = 0.20
        self.category_cache = {}  # Para evitar consultas repetidas a la API

    def woocommerce_request(self, method, endpoint, data=None, params=None, max_retries=3):
        """Wrapper con reintentos para la API de WooCommerce."""
        for attempt in range(max_retries):
            try:
                if method.lower() == 'get':
                    response = self.wcapi.get(endpoint, params=params)
                elif method.lower() == 'post':
                    response = self.wcapi.post(endpoint, data=data)
                elif method.lower() == 'put':
                    response = self.wcapi.put(endpoint, data=data)
                else: 
                    return None
                
                if response.status_code in [200, 201]:
                    return response
                else:
                    print(f"    ⚠️ Error API (HTTP {response.status_code}): {response.text[:200]}")
            except Exception as e:
                if attempt < max_retries - 1:
                    wait = (attempt + 1) * 5
                    print(f"    ⚠️ Error de conexión ({e}). Reintentando en {wait}s ({attempt+1}/{max_retries})...")
                    time.sleep(wait)
                else:
                    print(f"    ❌ Fallo definitivo tras {max_retries} intentos.")
                    return None
        return None

    def get_or_create_category(self, name, parent_id=0):
        """Busca o crea una categoría jerárquica en WooCommerce."""
        name = str(name).strip().title()
        if not name or name == 'Nan': return 0
        
        cache_key = f"{name}_{parent_id}"
        if cache_key in self.category_cache:
            return self.category_cache[cache_key]
            
        # Buscar por nombre exacto y padre
        response = self.woocommerce_request("get", "products/categories", params={"search": name, "per_page": 100})
        if response:
            categories = response.json()
            for cat in categories:
                if cat['name'].lower() == name.lower() and cat['parent'] == parent_id:
                    self.category_cache[cache_key] = cat['id']
                    return cat['id']
                    
        # Crear si no existe
        print(f"    📁 Creando categoría: {name} (Padre ID: {parent_id})")
        data = {"name": name, "parent": parent_id}
        response = self.woocommerce_request("post", "products/categories", data=data)
        if response:
            new_cat = response.json()
            self.category_cache[cache_key] = new_cat['id']
            return new_cat['id']
            
        return 0

    def find_product_by_sku(self, sku):
        """Busca un producto existente por su SKU."""
        response = self.woocommerce_request("get", "products", params={"sku": str(sku)})
        if response:
            products = response.json()
            return products[0] if products else None
        return None

    def process_files(self, file_list, dollar_value, image_map_path="downloads/mapa_imagenes.json"):
        """Procesa la lista de archivos CSV y sincroniza con la API."""
        stats = {"total_processed": 0, "updates": 0, "creations": 0, "errors": 0, "filtered": 0}
        
        # 1. Cargar Mapa de Imágenes
        image_map = {}
        if os.path.exists(image_map_path):
            try:
                with open(image_map_path, 'r', encoding='utf-8') as f:
                    image_map = json.load(f)
                print(f"🖼️ Mapa de imágenes cargado: {len(image_map)} productos.")
            except Exception as e:
                print(f"⚠️ No se pudo cargar el mapa de imágenes: {e}")

        # 2. Iterar sobre archivos
        for file_path in file_list:
            print(f"\n📖 Procesando: {os.path.basename(file_path)}")
            
            try:
                # Lectura de CSV según requisitos (UTF-16, Tab, Header=2)
                with open(file_path, 'r', encoding='utf-16') as f:
                    content = f.read()
                
                df = pd.read_csv(
                    io.StringIO(content),
                    sep='\t',
                    header=2,
                    decimal=',',
                    engine='python'
                )
                
                # Identificar columnas dinámicamente por nombre
                col_sku = next((c for c in df.columns if 'sku' in c.lower()), None)
                col_name = next((c for c in df.columns if 'nombre' in c.lower()), None)
                col_price = next((c for c in df.columns if 'precio' in c.lower()), None)
                col_stock = next((c for c in df.columns if 'disponibilidad' in c.lower()), None)
                col_cat = next((c for c in df.columns if 'Categoría' == c or 'Categoria' == c), None)
                col_subcat = next((c for c in df.columns if 'Subcategoría' == c or 'Subcategoria' == c), None)

                for _, row in df.iterrows():
                    sku = str(row[col_sku]).strip() if col_sku else None
                    if not sku or sku == 'nan': continue

                    try:
                        # --- Limpieza y Conversión ---
                        # Precio (Costo USD -> Costo CLP)
                        cost_usd = float(str(row[col_price]).replace('$', '').replace(' ', '').replace(',', '.'))
                        cost_clp = cost_usd * dollar_value
                        
                        # Stock
                        stock_text = str(row[col_stock]).lower()
                        if 'más de 20' in stock_text or 'mas de 20' in stock_text:
                            stock = 20
                        elif 'sin stock' in stock_text:
                            stock = 0
                        else:
                            nums = re.findall(r'\d+', stock_text)
                            stock = int(nums[0]) if nums else 0

                        # --- Cálculo de Precio de Venta ---
                        # Fórmula: Costo / (1 - Margen)
                        sale_price = round(cost_clp / (1 - self.margin_percentage))

                        # --- Gestión de Categorías Jerárquicas ---
                        category_id = 0
                        if col_cat and col_subcat:
                            parent_id = self.get_or_create_category(row[col_cat])
                            category_id = self.get_or_create_category(row[col_subcat], parent_id=parent_id)

                        # --- Preparación de Datos ---
                        product_data = {
                            "name": str(row[col_name]),
                            "type": "simple",
                            "regular_price": str(sale_price),
                            "sku": sku,
                            "manage_stock": True,
                            "stock_quantity": stock,
                            "status": "publish",
                            "categories": [{"id": category_id}] if category_id > 0 else []
                        }

                        # --- Sincronización ---
                        existing = self.find_product_by_sku(sku)
                        
                        if existing:
                            # Actualización (Solo precio y stock para velocidad)
                            payload = {
                                "regular_price": str(sale_price),
                                "stock_quantity": stock,
                                "stock_status": "instock" if stock > 0 else "outofstock"
                            }
                            res = self.woocommerce_request("put", f"products/{existing['id']}", data=payload)
                            if res:
                                stats["updates"] += 1
                                print(f"   🔄 SKU {sku}: Actualizado (${sale_price} CLP, Stock: {stock})")
                        else:
                            # Creación (Con imagen del mapa JSON)
                            if sku in image_map:
                                product_data["images"] = [{"src": image_map[sku]}]
                                print(f"   🖼️ SKU {sku}: Imagen vinculada.")
                            
                            res = self.woocommerce_request("post", "products", data=product_data)
                            if res:
                                stats["creations"] += 1
                                print(f"   ✨ SKU {sku}: Creado (${sale_price} CLP, Stock: {stock})")

                        stats["total_processed"] += 1
                        time.sleep(2)  # Pausa de estabilidad

                    except Exception as e:
                        print(f"   ❌ Error procesando SKU {sku}: {e}")
                        stats["errors"] += 1

            except Exception as e:
                print(f"❌ Error crítico leyendo archivo {file_path}: {e}")

        return stats
