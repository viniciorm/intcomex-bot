# Bot de Sincronización Directa: Intcomex -> WooCommerce (Versión Producción)
# Descarga CSVs por categoría y sincroniza con WooCommerce

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.chrome.options import Options as ChromeOptions
from woocommerce import API
import pandas as pd
import time
import os
import re
import logging
import glob
import io
from pathlib import Path
from datetime import datetime
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from webdriver_manager.chrome import ChromeDriverManager

# Importar credenciales desde archivo externo
try:
    from credentials import (
        INTCOMEX_USERNAME,
        INTCOMEX_PASSWORD,
        WC_URL,
        WC_CONSUMER_KEY,
        WC_CONSUMER_SECRET,
        SMTP_SERVER,
        SMTP_PORT,
        SMTP_USER,
        SMTP_PASS,
        SMTP_RECEIVER,
        SMTP_CC
    )
except ImportError:
    print("ERROR: No se encontró el archivo 'credentials.py'")
    print("Por favor, copia 'credentials.example.py' como 'credentials.py' y completa con tus credenciales.")
    exit(1)

# --- Configuración Intcomex ---
LOGIN_URL = "https://store.intcomex.com/Account/Login"
USERNAME = INTCOMEX_USERNAME
PASSWORD = INTCOMEX_PASSWORD

# Diccionario de categorías con URLs
URLS = {
    # "Notebooks": "https://store.intcomex.com/es-XCL/Products/ByCategory/cpt.notebook?r=True",
    # "Monitores": "https://store.intcomex.com/es-XCL/Products/ByCategory/mnt.monitor?r=True",
    "Monitores_TV": "https://store.intcomex.com/es-XCL/Products/ByCategory/mnt.tv?r=True",
    # "Desktop": "https://store.intcomex.com/es-XCL/Products/ByCategory/cpt.desktop?r=True",
    # "Tablets": "https://store.intcomex.com/es-XCL/Products/ByCategory/cpt.tablet?r=True",
    # "Impresoras_Inkjet": "https://store.intcomex.com/es-XCL/Products/ByCategory/prt.inkjet?r=True",
    # "Impresoras_Label": "https://store.intcomex.com/es-XCL/Products/ByCategory/prt.label?r=True",
    # "Impresoras_Laser": "https://store.intcomex.com/es-XCL/Products/ByCategory/prt.laser?r=True",
    # "Impresoras_MFP": "https://store.intcomex.com/es-XCL/Products/ByCategory/prt.mfp?r=True",
    # "Scanners": "https://store.intcomex.com/es-XCL/Products/ByCategory/prt.scanner?r=True",
    # "All_in_One": "https://store.intcomex.com/es-XCL/Products/ByCategory/cpt.allone?r=True"
}

# --- Configuración WooCommerce ---
# Las credenciales se importan desde credentials.py

# --- Selectores CSS/XPath ---
LOGIN_USERNAME_FIELD_SELECTOR = (By.ID, "UserName")
LOGIN_PASSWORD_FIELD_SELECTOR = (By.ID, "Password")
LOGIN_BUTTON_SELECTOR = (By.ID, "LoginButton")
DOWNLOAD_BUTTON_SELECTOR = (By.CSS_SELECTOR, "a.priceListButtom[href*='Csv']")

# --- Constantes de Filtrado ---
MIN_STOCK = 0  # Restricción de stock eliminada por solicitud del usuario
MIN_PRICE_COST = 0  # Restricción de precio eliminada por solicitud del usuario
MARGIN_PERCENTAGE = 0.20  # 20% de margen

# --- Configuración de Descargas ---
DOWNLOAD_DIR = os.path.join(os.getcwd(), "downloads")
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

# Suprimir mensajes de logging
logging.getLogger('selenium').setLevel(logging.WARNING)
logging.getLogger('urllib3').setLevel(logging.WARNING)


# --- Funciones de Utilidad ---

def clean_price_to_float(price_text):
    """
    Convierte un texto de precio CLP (ej: "$ 150.000" o "$150.000" o "487,50") a float.
    Intcomex usa formato con coma decimal (ej: "487,50").
    
    Args:
        price_text: String con el precio (ej: "487,50" o "$150.000")
    
    Returns:
        float: Precio como número, o None si no se puede convertir
    """
    if pd.isna(price_text) or price_text is None:
        return None
    
    try:
        # Convertir a string si es número
        price_str = str(price_text).strip()
        
        # Si ya es un número, retornarlo
        if isinstance(price_text, (int, float)):
            return float(price_text)
        
        # Remover símbolos de moneda y espacios (USD, CLP, $)
        cleaned = re.sub(r'[\$\sCLPUSD]', '', price_str, flags=re.IGNORECASE)
        
        # Detectar si usa coma decimal o punto decimal
        # Si tiene coma y punto, el punto es separador de miles y la coma es decimal
        if ',' in cleaned and '.' in cleaned:
            # Formato: "1.234,56" -> punto es miles, coma es decimal
            cleaned = cleaned.replace('.', '')  # Remover puntos (miles)
            cleaned = cleaned.replace(',', '.')  # Coma -> punto decimal
        elif ',' in cleaned and '.' not in cleaned:
            # Solo tiene coma: puede ser decimal (ej: "487,50") o miles
            # Si hay más de una coma o la coma está antes del último grupo de 3 dígitos, es separador de miles
            parts = cleaned.split(',')
            if len(parts) == 2 and len(parts[1]) <= 2:
                # Es formato decimal: "487,50"
                cleaned = cleaned.replace(',', '.')
            else:
                # Es separador de miles: "1,234"
                cleaned = cleaned.replace(',', '')
        else:
            # Solo tiene punto o nada: puede ser miles o decimal
            # Si el punto está antes de los últimos 3 dígitos, probablemente es separador de miles
            if '.' in cleaned:
                parts = cleaned.split('.')
                if len(parts) == 2 and len(parts[1]) <= 2:
                    # Es formato decimal: "487.50"
                    pass  # Ya tiene punto decimal
                else:
                    # Es separador de miles: "1.234"
                    cleaned = cleaned.replace('.', '')
        
        return float(cleaned)
    except (ValueError, AttributeError, TypeError) as e:
        print(f"⚠ Error al convertir precio '{price_text}' a float: {e}")
        return None


def calculate_sale_price(cost_price):
    """
    Calcula el precio de venta con margen del 20%.
    Fórmula: Precio_Venta = Costo / (1 - 0.20) = Costo / 0.8
    
    Args:
        cost_price: Precio de costo como float
    
    Returns:
        float: Precio de venta calculado
    """
    if cost_price is None or cost_price <= 0:
        return None
    return cost_price / (1 - MARGIN_PERCENTAGE)


def extract_stock_number(stock_text):
    """
    Extrae el número de stock de un texto (ej: "Disponible: 100 unidades" o "Más de 20").
    Si el texto contiene "más de X", retorna X.
    """
    if stock_text is None:
        return 0
    
    if isinstance(stock_text, (int, float)):
        return int(stock_text)
        
    try:
        text = str(stock_text).lower().strip()
        
        # Buscar el primer número en el texto
        nums = re.findall(r'\d+', text)
        if nums:
            return int(nums[0])
            
        # Si no hay números pero dice algo de disponibilidad
        if 'disponible' in text or 'en stock' in text:
            return 1 # Asumir al menos 1 si no hay número pero indica disponibilidad
            
        return 0
    except:
        return 0


def detect_csv_encoding(file_path):
    """
    Detecta el encoding correcto del CSV de Intcomex.
    Intcomex suele usar 'latin-1', 'utf-16', 'utf-8' o 'iso-8859-1'.
    
    Args:
        file_path: Ruta al archivo CSV
    
    Returns:
        str: Encoding detectado
    """
    encodings = ['latin-1', 'utf-16', 'utf-8', 'iso-8859-1', 'cp1252']
    
    for encoding in encodings:
        try:
            with open(file_path, 'r', encoding=encoding) as f:
                f.read(1024)  # Leer una muestra
            print(f"✓ Encoding detectado: {encoding}")
            return encoding
        except (UnicodeDecodeError, UnicodeError):
            continue
    
    # Si ninguno funciona, intentar utf-8 con errores ignorados
    print("⚠ No se pudo detectar encoding, usando utf-8 con errores ignorados")
    return 'utf-8'


# --- Funciones de WooCommerce ---

def init_woocommerce_api():
    """
    Inicializa la conexión con la API de WooCommerce.
    
    Returns:
        API: Objeto API de WooCommerce
    """
    return API(
        url=WC_URL,
        consumer_key=WC_CONSUMER_KEY,
        consumer_secret=WC_CONSUMER_SECRET,
        version="wc/v3",
        timeout=30  # Aumentado a 30 segundos para evitar Timeouts en cargas masivas
    )

# Cache de categorías para evitar llamadas repetidas a la API
category_cache = {}

def get_or_create_woo_category(wcapi, category_name, parent_id=None):
    """
    Busca una categoría en WooCommerce por nombre. Si no existe, la crea.
    Usa un cache local para optimizar las peticiones.
    """
    cache_key = f"{category_name}_{parent_id}"
    if cache_key in category_cache:
        return category_cache[cache_key]

    try:
        # Buscar categoría existente
        params = {"search": category_name, "per_page": 20}
        if parent_id:
            params["parent"] = parent_id
            
        response = woocommerce_request(wcapi, "get", "products/categories", params=params)
        
        if response and response.status_code == 200:
            categories = response.json()
            for cat in categories:
                # Verificación exacta de nombre (el search de WC es parcial)
                if cat['name'].lower() == category_name.lower():
                    category_cache[cache_key] = cat['id']
                    return cat['id']

        # Si no existe, crearla
        new_cat_data = {"name": category_name}
        if parent_id:
            new_cat_data["parent"] = parent_id
            
        create_res = woocommerce_request(wcapi, "post", "products/categories", data=new_cat_data)
        if create_res and create_res.status_code in [200, 201]:
            new_id = create_res.json().get('id')
            print(f"    📁 Categoría creada: {category_name} (ID: {new_id})")
            category_cache[cache_key] = new_id
            return new_id
            
    except Exception as e:
        print(f"    ⚠ Error gestionando categoría '{category_name}': {e}")
        
    return None

def woocommerce_request(wcapi, method, endpoint, data=None, params=None, max_retries=3):
    """
    Realiza una petición a la API de WooCommerce con reintentos automáticos.
    """
    for attempt in range(max_retries):
        try:
            if method.lower() == 'get':
                response = wcapi.get(endpoint, params=params)
            elif method.lower() == 'post':
                response = wcapi.post(endpoint, data=data)
            elif method.lower() == 'put':
                response = wcapi.put(endpoint, data=data)
            else:
                return None
            
            return response
        except Exception as e:
            if attempt < max_retries - 1:
                wait_time = (attempt + 1) * 2
                print(f"    ⚠ Error en API ({e}). Reintentando en {wait_time}s (Intento {attempt + 2}/{max_retries})...")
                time.sleep(wait_time)
            else:
                print(f"    ❌ Fallo definitivo tras {max_retries} intentos: {e}")
                raise e
    return None


def find_product_by_sku(wcapi, sku):
    """ Busca un producto en WooCommerce por su SKU. """
    try:
        response = woocommerce_request(wcapi, "get", "products", params={"sku": str(sku), "per_page": 1})
        if response and response.status_code == 200:
            products = response.json()
            if products:
                return products[0]
        return None
    except Exception as e:
        print(f"    ⚠ Error al buscar SKU {sku}: {e}")
        return None


def create_product_in_woocommerce(wcapi, product_data):
    """Crea un nuevo producto en WooCommerce."""
    try:
        data = {
            "name": product_data.get("title", "Producto sin nombre"),
            "type": "simple",
            "regular_price": str(product_data.get("sale_price", "")),
            "sku": str(product_data.get("sku", "")),
            "manage_stock": True,
            "stock_quantity": int(product_data.get("stock", 0)),
            "status": "publish",
            "shipping_class": "free-shipping",
            "tags": [{"name": "Envío Gratuito"}]
        }
        
        if product_data.get("categories"):
            data["categories"] = product_data.get("categories")
            
        if product_data.get("short_description"):
            data["short_description"] = str(product_data.get("short_description"))
            
        if product_data.get("image_url"):
            data["images"] = [{"src": str(product_data.get("image_url"))}]
            
        response = woocommerce_request(wcapi, "post", "products", data=data)
        
        if response and response.status_code in [200, 201]:
            print(f"  ✓ Producto creado: ID {response.json().get('id')} (SKU: {product_data.get('sku')})")
            return True
        return False
    except Exception as e:
        print(f"  ✗ Excepción al crear producto {product_data.get('sku', 'N/A')}: {e}")
        return False


def update_product_in_woocommerce(wcapi, product_id, product_data):
    """Actualiza un producto existente en WooCommerce."""
    try:
        data = {
            "regular_price": str(product_data.get("sale_price", "")),
            "stock_quantity": int(product_data.get("stock", 0)),
            "stock_status": "instock" if product_data.get("stock", 0) > 0 else "outofstock",
            "short_description": str(product_data.get("short_description", "")),
            "categories": product_data.get("categories", [])
        }
        
        response = woocommerce_request(wcapi, "put", f"products/{product_id}", data=data)
        
        if response and response.status_code == 200:
            print(f"  ✓ Producto actualizado: ID {product_id} (SKU: {product_data.get('sku')})")
            return True
        return False
    except Exception as e:
        print(f"  ✗ Excepción al actualizar producto {product_id}: {e}")
        return False


# --- Funciones de Navegación ---

def login_intcomex(driver, username, password):
    """
    Inicia sesión en Intcomex usando Selenium.
    MODO MANUAL: Espera a que el usuario ingrese las credenciales manualmente.
    El código de llenado automático está disponible pero comentado para uso futuro.
    """
    print(f"🌐 Navegando a: {LOGIN_URL}")
    driver.get(LOGIN_URL)
    time.sleep(2)
    wait = WebDriverWait(driver, 20)

    try:
        # Verificar si ya estamos logueados
        current_url = driver.current_url
        if "Login" not in current_url and "login" not in current_url.lower():
            print(f"✓ Ya estás logueado en Intcomex. URL: {current_url}")
            return True
        
        print("🔍 Esperando login manual...")
        print("   Por favor, ingresa tus credenciales en el navegador.")
        print(f"   Usuario sugerido: {username}")
        print("   El bot esperará hasta que detecte que el login fue exitoso...")
        
        # ============================================================
        # CÓDIGO DE LLENADO AUTOMÁTICO (COMENTADO - NO ACTIVO)
        # ============================================================
        # Descomenta este bloque si quieres activar el llenado automático:
        #
        # # Intentar múltiples selectores para el campo de usuario
        # username_field = None
        # selectors_username = [
        #     LOGIN_USERNAME_FIELD_SELECTOR,
        #     (By.NAME, "UserName"),
        #     (By.NAME, "Email"),
        #     (By.CSS_SELECTOR, "input[type='email']"),
        #     (By.CSS_SELECTOR, "input[name='UserName']"),
        # ]
        # 
        # for selector in selectors_username:
        #     try:
        #         username_field = wait.until(EC.presence_of_element_located(selector))
        #         print(f"✓ Campo de usuario encontrado")
        #         break
        #     except:
        #         continue
        # 
        # if not username_field:
        #     raise Exception("No se pudo encontrar el campo de usuario")
        # 
        # # Intentar múltiples selectores para el campo de contraseña
        # password_field = None
        # selectors_password = [
        #     LOGIN_PASSWORD_FIELD_SELECTOR,
        #     (By.NAME, "Password"),
        #     (By.CSS_SELECTOR, "input[type='password']"),
        #     (By.CSS_SELECTOR, "input[name='Password']"),
        # ]
        # 
        # for selector in selectors_password:
        #     try:
        #         password_field = wait.until(EC.presence_of_element_located(selector))
        #         print(f"✓ Campo de contraseña encontrado")
        #         break
        #     except:
        #         continue
        # 
        # if not password_field:
        #     raise Exception("No se pudo encontrar el campo de contraseña")
        # 
        # # Limpiar y escribir credenciales
        # username_field.clear()
        # password_field.clear()
        # time.sleep(0.5)
        # 
        # print(f"⌨️  Ingresando usuario: {username}")
        # username_field.send_keys(username)
        # time.sleep(0.5)
        # 
        # print("⌨️  Ingresando contraseña...")
        # password_field.send_keys(password)
        # time.sleep(0.5)
        # 
        # # Buscar botón de login
        # login_button = None
        # selectors_button = [
        #     LOGIN_BUTTON_SELECTOR,
        #     (By.CSS_SELECTOR, "button[type='submit']"),
        #     (By.CSS_SELECTOR, "input[type='submit']"),
        # ]
        # 
        # for selector in selectors_button:
        #     try:
        #         login_button = wait.until(EC.element_to_be_clickable(selector))
        #         print(f"✓ Botón de login encontrado")
        #         break
        #     except:
        #         continue
        # 
        # if not login_button:
        #     raise Exception("No se pudo encontrar el botón de login")
        # 
        # print("🖱️  Haciendo clic en el botón de login...")
        # login_button.click()
        # time.sleep(3)
        # ============================================================
        
        # Esperar activamente a que el usuario complete el login manualmente
        # Verificar cada segundo si el login fue exitoso
        max_wait_time = 300  # 5 minutos máximo de espera
        check_interval = 2  # Verificar cada 2 segundos
        elapsed_time = 0
        
        print(f"   ⏳ Esperando login manual (máximo {max_wait_time} segundos)...")
        
        while elapsed_time < max_wait_time:
            current_url = driver.current_url
            
            # Verificar si ya no estamos en la página de login
            if "Login" not in current_url and "login" not in current_url.lower() and "Account" not in current_url:
                print(f"\n✓ Inicio de sesión detectado exitosamente!")
                print(f"   URL actual: {current_url}")
                time.sleep(2)  # Esperar un poco más para asegurar que la página cargue
                return True
            
            # Verificar si hay elementos que indican que estamos logueados
            try:
                logged_in_indicators = [
                    (By.CSS_SELECTOR, "a[href*='logout']"),
                    (By.CSS_SELECTOR, "a[href*='Logout']"),
                    (By.XPATH, "//a[contains(text(), 'Cerrar') or contains(text(), 'Salir') or contains(text(), 'Logout')]"),
                    (By.CSS_SELECTOR, ".user-menu"),
                    (By.CSS_SELECTOR, ".account-menu"),
                ]
                
                for indicator in logged_in_indicators:
                    try:
                        element = driver.find_element(indicator[0], indicator[1])
                        if element:
                            print(f"\n✓ Inicio de sesión detectado (elemento de sesión encontrado)!")
                            print(f"   URL actual: {current_url}")
                            return True
                    except:
                        continue
            except:
                pass
            
            time.sleep(check_interval)
            elapsed_time += check_interval
            
            # Mostrar progreso cada 30 segundos
            if elapsed_time % 30 == 0:
                remaining = max_wait_time - elapsed_time
                print(f"   ⏳ Aún esperando... ({remaining} segundos restantes)")
        
        # Si llegamos aquí, el timeout se alcanzó
        print(f"\n⚠ Timeout alcanzado después de {max_wait_time} segundos")
        print(f"   URL actual: {current_url}")
        
        # Preguntar al usuario si el login fue exitoso
        print("\n¿El login fue exitoso? (s/n): ", end="")
        try:
            response = input().lower()
            if response == 's':
                print("✓ Continuando con el script...")
                return True
            else:
                print("✗ Login no completado. Cancelando ejecución.")
                return False
        except:
            print("\n✗ No se pudo obtener respuesta. Cancelando ejecución.")
            return False
        
    except KeyboardInterrupt:
        print("\n⚠ Proceso interrumpido por el usuario durante el login.")
        return False
    except Exception as e:
        print(f"✗ Error durante el inicio de sesión: {e}")
        driver.save_screenshot("login_error.png")
        return False


def wait_for_download(category_name, timeout=30):
    """
    Espera activamente hasta que aparezca un nuevo archivo CSV en la carpeta downloads.
    
    Args:
        category_name: Nombre de la categoría para el nombre del archivo
        timeout: Tiempo máximo de espera en segundos
    
    Returns:
        str: Ruta del archivo descargado, o None si timeout
    """
    print(f"  ⏳ Esperando descarga del CSV...")
    
    # Obtener lista de archivos antes de la descarga
    initial_files = set(glob.glob(os.path.join(DOWNLOAD_DIR, "*.csv")))
    
    start_time = time.time()
    while time.time() - start_time < timeout:
        current_files = set(glob.glob(os.path.join(DOWNLOAD_DIR, "*.csv")))
        new_files = current_files - initial_files
        
        if new_files:
            # Tomar el archivo más reciente
            downloaded_file = max(new_files, key=os.path.getctime)
            
            # Esperar un poco más para asegurar que el archivo se complete
            time.sleep(2)
            
            # Renombrar archivo
            new_name = os.path.join(DOWNLOAD_DIR, f"{category_name}.csv")
            if os.path.exists(new_name):
                os.remove(new_name)  # Eliminar si ya existe
            
            os.rename(downloaded_file, new_name)
            print(f"  ✓ CSV descargado y renombrado: {new_name}")
            return new_name
        
        time.sleep(1)
    
    print(f"  ✗ Timeout esperando descarga del CSV")
    return None


def download_category_csv(driver, category_name, category_url):
    """
    Navega a una categoría y descarga su CSV.
    
    Args:
        driver: WebDriver de Selenium
        category_name: Nombre de la categoría
        category_url: URL de la categoría
    
    Returns:
        str: Ruta del archivo CSV descargado, o None si falló
    """
    try:
        print(f"\n📥 Procesando categoría: {category_name}")
        print(f"   URL: {category_url}")
        
        # Navegar a la categoría
        driver.get(category_url)
        time.sleep(3)  # Esperar a que la página cargue
        
        # Buscar y hacer click en el botón de descarga
        wait = WebDriverWait(driver, 10)
        try:
            # Intentar cerrar popups de publicidad si existen
            try:
                popup_selectors = [
                    (By.CSS_SELECTOR, ".popin_img_img"),
                    (By.CSS_SELECTOR, ".popup-close"),
                    (By.CSS_SELECTOR, "[class*='popup'] [class*='close']"),
                    (By.CSS_SELECTOR, "[class*='ad'] [class*='close']"),
                    (By.XPATH, "//button[contains(@class, 'close') or contains(@id, 'close')]"),
                ]
                for selector in popup_selectors:
                    try:
                        popup = driver.find_element(selector[0], selector[1])
                        if popup.is_displayed():
                            print(f"  🗙 Cerrando popup de publicidad...")
                            driver.execute_script("arguments[0].click();", popup)
                            time.sleep(1)
                            break
                    except:
                        continue
            except:
                pass  # Si no hay popup, continuar
            
            # Buscar el botón de descarga
            download_button = wait.until(EC.presence_of_element_located(DOWNLOAD_BUTTON_SELECTOR))
            print(f"  ✓ Botón de descarga encontrado")
            
            # Verificar que tenga el atributo data-login (puede ser "LoggedUser" o "LogedUser")
            data_login = download_button.get_attribute("data-login")
            if data_login and data_login not in ["LoggedUser", "LogedUser"]:
                print(f"  ⚠ Advertencia: data-login='{data_login}' (esperado: 'LoggedUser' o 'LogedUser')")
            elif data_login:
                print(f"  ✓ data-login encontrado: '{data_login}'")
            
            # Hacer scroll hasta el botón para asegurar que esté visible
            driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", download_button)
            time.sleep(0.5)
            
            # Hacer click usando JavaScript para evitar "Element Click Intercepted" por popups
            # Este método penetra cualquier overlay visual (popups, publicidad, etc.)
            print(f"  🖱️  Haciendo clic en botón de descarga (usando JavaScript)...")
            driver.execute_script("arguments[0].click();", download_button)
            
            # Esperar a que aparezca el archivo descargado
            csv_file = wait_for_download(category_name, timeout=30)
            return csv_file
            
        except Exception as e:
            print(f"  ✗ Error al descargar CSV: {e}")
            return None
            
    except Exception as e:
        print(f"  ✗ Error al procesar categoría {category_name}: {e}")
        return None


def obtener_dolar_web(driver):
    """
    Extrae el valor del dólar del encabezado del sitio web de Intcomex.
    Busca texto como "US$1 = CLP$902" en el header superior.
    
    Args:
        driver: WebDriver de Selenium
    
    Returns:
        float: Valor del dólar, o valor por defecto (970) si no se encuentra
    """
    valor_dolar_default = 970.0
    
    try:
        print(f"  💵 Buscando valor del dólar en el sitio web...")
        
        # Esperar a que la página cargue completamente
        time.sleep(2)
        
        # Obtener el HTML completo de la página
        page_source = driver.page_source
        
        # Buscar patrones comunes donde aparece el tipo de cambio
        # Patrones a buscar: "US$1 = CLP$902", "US$1 = $902", "CLP$902", etc.
        patterns = [
            r'US\$1\s*=\s*CLP\$?(\d+(?:[.,]\d+)?)',  # US$1 = CLP$902 o US$1 = CLP 902
            r'US\$1\s*=\s*\$?(\d+(?:[.,]\d+)?)',     # US$1 = $902 o US$1 = 902
            r'CLP\$(\d+(?:[.,]\d+)?)',               # CLP$902
            r'\$1\s*=\s*\$?(\d{3,4}(?:[.,]\d+)?)',   # $1 = $902 o $1 = 902.50
            r'T\.?Cambio[:\s]+(\d+(?:[.,]\d+)?)',    # T.Cambio: 902.50
            r'Tasa[:\s]+(\d+(?:[.,]\d+)?)',          # Tasa: 902.50
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, page_source, re.IGNORECASE)
            if matches:
                # Tomar el primer match y convertir a float
                for match in matches:
                    valor_str = match.replace(',', '.')
                    try:
                        valor_dolar = float(valor_str)
                        # Validar que sea un valor razonable de dólar (entre 500 y 2000)
                        if 500 <= valor_dolar <= 2000:
                            print(f"  ✓ Valor del dólar extraído del sitio: ${valor_dolar:,.2f} CLP")
                            return valor_dolar
                    except ValueError:
                        continue
        
        # Si no se encontró con regex, intentar buscar en elementos específicos del DOM
        try:
            selectors_dolar = [
                (By.XPATH, "//*[contains(text(), 'US$1') or contains(text(), 'CLP$')]"),
                (By.CSS_SELECTOR, "[class*='exchange']"),
                (By.CSS_SELECTOR, "[class*='tasa']"),
                (By.CSS_SELECTOR, "[class*='dolar']"),
                (By.CSS_SELECTOR, "header *"),
            ]
            
            for selector_type, selector_value in selectors_dolar:
                try:
                    elements = driver.find_elements(selector_type, selector_value)
                    for element in elements:
                        text = element.text
                        if 'US$' in text or 'CLP$' in text or '$1' in text:
                            # Buscar número en el texto del elemento
                            for pattern in patterns:
                                matches = re.findall(pattern, text, re.IGNORECASE)
                                if matches:
                                    valor_str = matches[0].replace(',', '.')
                                    try:
                                        valor_dolar = float(valor_str)
                                        if 500 <= valor_dolar <= 2000:
                                            print(f"  ✓ Valor del dólar extraído del elemento DOM: ${valor_dolar:,.2f} CLP")
                                            return valor_dolar
                                    except ValueError:
                                        continue
                except:
                    continue
        except:
            pass
        
        # Si no se encontró, usar valor por defecto
        print(f"  ⚠ No se pudo extraer el valor del dólar del sitio web. Usando valor por defecto: ${valor_dolar_default:,.2f} CLP")
        return valor_dolar_default
        
    except Exception as e:
        print(f"  ⚠ Error al obtener dólar del sitio web: {e}")
        print(f"  ⚠ Usando valor por defecto: ${valor_dolar_default:,.2f} CLP")
        return valor_dolar_default




def enviar_reporte(descargas_exitosas, errores_descarga, total_stats):
    """
    Envía un reporte por correo electrónico con el resumen del proceso.
    """
    print("\n📧 Enviando reporte por correo...")
    
    try:
        fecha_actual = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        fecha_asunto = datetime.now().strftime("%d/%m/%Y")
        
        msg = MIMEMultipart()
        msg['From'] = SMTP_USER
        msg['To'] = SMTP_RECEIVER
        msg['Cc'] = SMTP_CC
        msg['Subject'] = f"🤖 Reporte Automático: Sincronización Intcomex [{fecha_asunto}]"
        
        # Lista de todos los destinatarios para smtplib
        destinatarios = [SMTP_RECEIVER]
        if SMTP_CC:
            destinatarios.append(SMTP_CC)
        
        # Construir cuerpo del mensaje
        cuerpo = f"""
        <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <h2 style="color: #2c3e50;">Resumen de Sincronización - {fecha_actual}</h2>
            <hr>
            
            <h3 style="color: #2980b9;">📥 Fase de Descarga</h3>
            <ul>
                <li><b>✅ Exitosas:</b> {', '.join(descargas_exitosas.keys()) if descargas_exitosas else 'Ninguna'}</li>
                <li><b>❌ Fallidas (tras reintentos):</b> <span style="color: #c0392b;">{', '.join(errores_descarga) if errores_descarga else 'Ninguna'}</span></li>
            </ul>
            
            <h3 style="color: #27ae60;">📦 Resumen WooCommerce</h3>
            <table border="0" cellpadding="5">
                <tr><td><b>Total procesados:</b></td><td>{total_stats['productos_procesados']}</td></tr>
                <tr><td><b>Creados:</b></td><td style="color: #27ae60;">{total_stats['productos_creados']}</td></tr>
                <tr><td><b>Actualizados:</b></td><td style="color: #2980b9;">{total_stats['productos_actualizados']}</td></tr>
                <tr><td><b>Errores:</b></td><td style="color: #c0392b;">{total_stats['errores']}</td></tr>
            </table>
            
            <br>
            <p style="font-size: 0.9em; color: #7f8c8d;">Este es un mensaje automático generado por Intcomex Bot.</p>
        </body>
        </html>
        """
        
        msg.attach(MIMEText(cuerpo, 'html'))
        
        # Conexión Segura SSL
        with smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT) as server:
            server.login(SMTP_USER, SMTP_PASS)
            server.sendmail(SMTP_USER, destinatarios, msg.as_string())
            
        print(f"✓ Reporte enviado exitosamente a: {SMTP_RECEIVER} (CC: {SMTP_CC})")
        
    except Exception as e:
        print(f"❌ Error al enviar el correo: {e}")


def sincronizar_csv(archivo_csv, wcapi, category_name, valor_dolar):
    """
    Procesa un CSV descargado y sincroniza productos con WooCommerce.
    """
    stats = {"procesados": 0, "creados": 0, "actualizados": 0, "filtrados": 0, "errores": 0}
    print(f"  💵 Usando valor del dólar: ${valor_dolar:,.2f} CLP")
    
    # Lectura ULTRA robusta usando StringIO para evitar errores de tokenización
    try:
        with open(archivo_csv, 'r', encoding='utf-16') as f:
            lines = f.readlines()
        
        # Buscar la cabecera dinámicamente
        header_idx = -1
        for i, line in enumerate(lines[:20]): # Revisar las primeras 20 líneas
            l = line.lower()
            if 'sku' in l or 'categoría' in l or 'nombre' in l:
                header_idx = i
                break
        
        if header_idx == -1:
            raise Exception("No se encontró la fila de cabecera en el CSV")

        print(f"  ✓ Cabecera detectada en la fila {header_idx}")
        
        # Crear DataFrame desde el bloque de datos que empieza en la cabecera
        csv_content = "".join(lines[header_idx:])
        df = pd.read_csv(
            io.StringIO(csv_content),
            sep='\t',
            decimal=',',
            on_bad_lines='skip',
            engine='python'
        )
        print(f"  ✓ CSV cargado con éxito. Filas: {len(df)}")
        
    except Exception as e:
        print(f"  ❌ Fallo crítico en lectura de CSV: {e}")
        return stats

    if df.empty:
        print("  ⚠ El archivo está vacío.")
        return stats
    
    # Filtrar filas que sean completamente nulas o que no tengan SKU
    df = df.dropna(subset=[df.columns[0]]) # Asumimos que la primera columna debe tener datos
    
    # Mapeo DINÁMICO para mayor robustez
    sku_col = None
    price_col = None
    stock_col = None
    desc_col = None
    
    for col in df.columns:
        c = str(col).strip().lower()
        if c == 'sku': sku_col = col
        elif c == 'precio': price_col = col
        elif c == 'disponibilidad' or c == 'existencia': stock_col = col
        elif c == 'nombre' or c == 'descripción': desc_col = col
        elif c == 'atributos': attr_col = col
        elif c == 'categoría': cat_col = col
        elif c == 'subcategoría': subcat_col = col

    if not sku_col or not price_col:
        # Fallback a búsqueda parcial si la exacta falla
        for col in df.columns:
            c = str(col).strip().lower()
            if 'sku' in c: sku_col = col
            elif 'precio' in c: price_col = col
            elif 'disponibil' in c: stock_col = col
            elif 'nombre' in c: desc_col = col
            elif 'atrib' in c: attr_col = col
            elif 'categor' in c and 'sub' not in c: cat_col = col
            elif 'subcategor' in c: subcat_col = col
    
    image_col = None # No hay columna de imagen en este CSV
    
    print(f"  📊 Mapeo final:")
    print(f"     - SKU: '{sku_col}'")
    print(f"     - Precio: '{price_col}'")
    print(f"     - Stock: '{stock_col}'")
    print(f"     - Nombre: '{desc_col}'")
    print(f"     - Atributos: '{attr_col}'")
    print(f"     - Categoría: '{cat_col}'")
    print(f"     - Subcategoría: '{subcat_col}'")
    
    if not sku_col or not price_col:
        raise Exception(f"Columnas obligatorias no encontradas: SKU={sku_col}, Precio={price_col}")
    
    # Procesar cada fila
    for idx, row in df.iterrows():
        try:
            # Extraer datos
            sku = row[sku_col] if sku_col else None
            price_text = row[price_col] if price_col else None
            
            # Extraer stock de la columna "Disponibilidad"
            stock = 0
            if stock_col and pd.notna(row[stock_col]):
                stock = extract_stock_number(row[stock_col])
            
            description = str(row[desc_col]) if desc_col and pd.notna(row[desc_col]) else "Sin descripción"
            short_description = str(row[attr_col]) if attr_col and pd.notna(row[attr_col]) else ""
            categoria_text = str(row[cat_col]) if cat_col and pd.notna(row[cat_col]) else None
            subcat_text = str(row[subcat_col]) if subcat_col and pd.notna(row[subcat_col]) else None
            image_url = str(row[image_col]) if image_col and pd.notna(row[image_col]) else None
            
            if not sku or pd.isna(sku):
                continue
            
            sku = str(sku).strip()
            
            # PASO 3: Calcular Precio Final en CLP
            # Los precios en el CSV vienen en USD, necesitamos convertirlos a CLP
            precio_usd = clean_price_to_float(price_text)
            
            # Validar que el precio USD sea válido
            if precio_usd is None or precio_usd <= 0:
                stats["errores"] += 1
                if idx < 5:  # Mostrar primeros 5 errores para debugging
                    print(f"    ⚠ Error en precio USD: {description[:50]}... - Precio inválido: {price_text}")
                continue
            
            # El usuario solicitó eliminar los filtros de stock y precio costo
            # Se procesan todos los productos que tengan un precio válido
            precio_costo_clp = precio_usd * valor_dolar
            
            # Convertir USD a CLP y aplicar margen del 20%
            # Fórmula: Precio_Final_CLP = (Precio_CSV_USD * valor_dolar) / (1 - 0.20)
            precio_costo_clp = precio_usd * valor_dolar
            precio_venta_clp = precio_costo_clp / (1 - MARGIN_PERCENTAGE)
            
            # Redondear a enteros (sin decimales)
            precio_costo_clp = round(precio_costo_clp)
            precio_venta_clp = round(precio_venta_clp)
            
            # Validar que el precio final sea válido
            if precio_venta_clp <= 0:
                stats["errores"] += 1
                if idx < 5:
                    print(f"    ⚠ Error: Precio de venta inválido después de cálculo (USD: {precio_usd}, Dólar: {valor_dolar})")
                continue
            
            # Procesar categorías de WooCommerce
            categories_list = []
            if categoria_text:
                cat_id = get_or_create_woo_category(wcapi, categoria_text)
                if cat_id:
                    categories_list.append({"id": cat_id})
                    if subcat_text:
                        sub_id = get_or_create_woo_category(wcapi, subcat_text, parent_id=cat_id)
                        if sub_id:
                            categories_list.append({"id": sub_id})
            
            # Preparar datos del producto
            product_data = {
                "title": description,
                "description": description,
                "short_description": short_description,
                "categories": categories_list,
                "sku": sku,
                "cost_price": precio_costo_clp,  # Precio costo en CLP
                "sale_price": precio_venta_clp,  # Precio venta en CLP (con margen aplicado)
                "precio_usd": precio_usd,  # Precio original en USD
                "valor_dolar": valor_dolar,  # Tipo de cambio usado
                "stock": stock,
                "image_url": image_url
            }
            
            # Buscar si el producto ya existe en WooCommerce
            existing_product = find_product_by_sku(wcapi, sku)
            
            if existing_product:
                # Actualizar producto existente
                product_id = existing_product["id"]
                if update_product_in_woocommerce(wcapi, product_id, product_data):
                    stats["actualizados"] += 1
                else:
                    stats["errores"] += 1
            else:
                # Crear nuevo producto
                if create_product_in_woocommerce(wcapi, product_data):
                    stats["creados"] += 1
                else:
                    stats["errores"] += 1
            
            stats["procesados"] += 1
            
            # Mostrar progreso cada 10 productos
            if stats["procesados"] % 10 == 0:
                print(f"    📊 Progreso: {stats['procesados']} procesados, {stats['creados']} creados, {stats['actualizados']} actualizados, {stats['filtrados']} filtrados")
            
            time.sleep(1.0)  # Pausa de 1 segundo para evitar saturar el servidor/API
            
        except Exception as e:
            stats["errores"] += 1
            print(f"  ⚠ Error procesando fila {idx}: {e}")
            continue
    
    return stats


# --- Ejecución Principal ---

if __name__ == "__main__":
    print("="*60)
    print("🤖 BOT DE SINCRONIZACIÓN INTCOMEX -> WOOCOMMERCE (PRODUCCIÓN)")
    print("="*60)
    
    # Verificar configuración de WooCommerce
    if WC_URL == "https://tu-tienda.com" or "xxxxx" in WC_CONSUMER_KEY or "ejemplo" in WC_CONSUMER_KEY:
        print("\n⚠ ADVERTENCIA: Debes configurar las credenciales de WooCommerce en credentials.py")
        print("   Copia 'credentials.example.py' como 'credentials.py' y completa con tus credenciales reales.")
        response = input("¿Deseas continuar de todos modos? (s/n): ")
        if response.lower() != 's':
            print("Ejecución cancelada.")
            exit(1)
    
    # Inicializar WooCommerce API
    print("\n🔌 Conectando con WooCommerce...")
    wcapi = init_woocommerce_api()
    
    # Configurar Chrome para descargas headless
    print("🌐 Inicializando navegador...")
    chrome_options = ChromeOptions()
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--log-level=3")
    chrome_options.add_experimental_option("excludeSwitches", ["enable-logging"])
    chrome_options.add_experimental_option('useAutomationExtension', False)
    
    # Configurar descargas
    prefs = {
        "download.default_directory": DOWNLOAD_DIR,
        "download.prompt_for_download": False,
        "download.directory_upgrade": True,
        "safebrowsing.enabled": True
    }
    chrome_options.add_experimental_option("prefs", prefs)
    
    # Inicializar driver
    service = ChromeService(ChromeDriverManager().install())
    service.log_path = "NUL"
    
    driver = webdriver.Chrome(service=service, options=chrome_options)
    driver.maximize_window()
    
    # Estadísticas globales
    total_stats = {
        "categorias_procesadas": 0,
        "categorias_fallidas": 0,
        "productos_procesados": 0,
        "productos_creados": 0,
        "productos_actualizados": 0,
        "productos_filtrados": 0,
        "errores": 0
    }
    
    # --- FASE 1: DESCARGAS ---
    print("\n" + "="*60)
    print("FASE 1: DESCARGA DE CSVs")
    print("="*60)
    
    categorias_pendientes = list(URLS.keys())
    descargas_exitosas = {} # category_name -> file_path
    errores_descarga = []
    valor_dolar = 970.0 # Valor por defecto
    
    try:
        # 1. Login obligatorio
        print("\nPASO 1.1: INICIO DE SESIÓN")
        if not login_intcomex(driver, USERNAME, PASSWORD):
            print("✗ El inicio de sesión falló. El bot no puede continuar.")
            driver.quit()
            exit(1)
        
        # 2. Obtener valor del dólar
        print("\nPASO 1.2: OBTENER VALOR DEL DÓLAR")
        valor_dolar = obtener_dolar_web(driver)
        print(f"✓ Valor del dólar para esta sesión: ${valor_dolar:,.2f} CLP")
        
        # 3. Primer buecle de descargas
        print("\nPASO 1.3: PRIMER INTENTO DE DESCARGAS")
        for cat_name in categorias_pendientes[:]:
            try:
                cat_url = URLS[cat_name]
                csv_file = download_category_csv(driver, cat_name, cat_url)
                
                if csv_file and os.path.exists(csv_file):
                    descargas_exitosas[cat_name] = csv_file
                    categorias_pendientes.remove(cat_name)
                    print(f"  ✓ {cat_name}: Descarga completa.")
                else:
                    print(f"  ⚠ {cat_name}: Falló la descarga.")
                    errores_descarga.append(cat_name)
            except Exception as e:
                print(f"  ⚠ {cat_name}: Error durante descarga: {e}")
                errores_descarga.append(cat_name)
            
            time.sleep(2)
            
        # 4. Segunda oportunidad para errores
        if errores_descarga:
            print("\nPASO 1.4: SEGUNDA OPORTUNIDAD PARA DOWNLOADS FALLIDOS")
            pendientes_reintento = errores_descarga.copy()
            errores_descarga = [] # Limpiar para el reintento
            
            for cat_name in pendientes_reintento:
                try:
                    print(f"  � Reintentando {cat_name}...")
                    cat_url = URLS[cat_name]
                    csv_file = download_category_csv(driver, cat_name, cat_url)
                    
                    if csv_file and os.path.exists(csv_file):
                        descargas_exitosas[cat_name] = csv_file
                        print(f"  ✓ {cat_name}: Descarga exitosa en segundo intento.")
                    else:
                        print(f"  ❌ {cat_name}: Falló nuevamente.")
                        errores_descarga.append(cat_name)
                except Exception as e:
                    print(f"  ❌ {cat_name}: Error en reintento: {e}")
                    errores_descarga.append(cat_name)
                
                time.sleep(2)

    except KeyboardInterrupt:
        print("\n\n⚠ Descargas interrumpidas por el usuario.")
    except Exception as e:
        print(f"\n✗ Error crítico en Fase de Descargas: {e}")
    finally:
        print("\n🔒 Cerrando navegador antes de la fase de carga...")
        driver.quit()
        print("✓ Navegador cerrado correctamente.")

    # --- FASE 2: CARGA A WOOCOMMERCE ---
    if not descargas_exitosas:
        print("\n⚠ No hay archivos descargados para procesar. Fin del programa.")
        exit(0)

    print("\n" + "="*60)
    print("FASE 2: SINCRONIZACIÓN CON WOOCOMMERCE")
    print("="*60)
    print(f"Archivos listos para procesar: {len(descargas_exitosas)}")

    # Estadísticas globales de carga
    total_stats = {
        "categorias_procesadas": 0,
        "categorias_fallidas": len(errores_descarga),
        "productos_procesados": 0,
        "productos_creados": 0,
        "productos_actualizados": 0,
        "productos_filtrados": 0,
        "errores": 0
    }

    for cat_name, csv_path in descargas_exitosas.items():
        try:
            print(f"\n🚀 Sincronizando categoría: {cat_name}")
            stats = sincronizar_csv(csv_path, wcapi, cat_name, valor_dolar)
            
            # Acumular estadísticas
            total_stats["categorias_procesadas"] += 1
            total_stats["productos_procesados"] += stats.get("procesados", 0)
            total_stats["productos_creados"] += stats.get("creados", 0)
            total_stats["productos_actualizados"] += stats.get("actualizados", 0)
            total_stats["productos_filtrados"] += stats.get("filtrados", 0)
            total_stats["errores"] += stats.get("errores", 0)
            
            print(f"  📊 Resumen {cat_name}:")
            print(f"     - Procesados: {stats.get('procesados', 0)}")
            print(f"     - Creados: {stats.get('creados', 0)}")
            print(f"     - Actualizados: {stats.get('actualizados', 0)}")
            print(f"     - Errores: {stats.get('errores', 0)}")
            
        except Exception as e:
            total_stats["categorias_fallidas"] += 1
            print(f"  ✗ Error fatal al sincronizar CSV de {cat_name}: {e}")

    # Resumen final
    print("\n" + "="*60)
    print("✅ PROCESO DE SINCRONIZACIÓN FINALIZADO")
    print("="*60)
    print(f"Categorías exitosas: {total_stats['categorias_procesadas']}")
    print(f"Categorías fallidas: {total_stats['categorias_fallidas']}")
    if total_stats["categorias_fallidas"] > 0:
        print(f"Categorías que fallaron descarga: {', '.join(errores_descarga)}")
    print(f"Total errores en productos: {total_stats['errores']}")
    print("="*60)

    # --- ENVIAR REPORTE ---
    enviar_reporte(descargas_exitosas, errores_descarga, total_stats)
