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
from pathlib import Path
from webdriver_manager.chrome import ChromeDriverManager

# Importar credenciales desde archivo externo
try:
    from credentials import (
        INTCOMEX_USERNAME,
        INTCOMEX_PASSWORD,
        WC_URL,
        WC_CONSUMER_KEY,
        WC_CONSUMER_SECRET
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
    "Notebooks": "https://store.intcomex.com/es-XCL/Products/ByCategory/cpt.notebook?r=True",
    "Monitores_TV": "https://store.intcomex.com/es-XCL/Products/ByCategory/mnt.tv?r=True",
    "Monitores": "https://store.intcomex.com/es-XCL/Products/ByCategory/mnt.monitor?r=True",
    "Desktop": "https://store.intcomex.com/es-XCL/Products/ByCategory/cpt.desktop?r=True",
    "Tablets": "https://store.intcomex.com/es-XCL/Products/ByCategory/cpt.tablet?r=True",
    "Impresoras_Inkjet": "https://store.intcomex.com/es-XCL/Products/ByCategory/prt.inkjet?r=True",
    "Impresoras_Label": "https://store.intcomex.com/es-XCL/Products/ByCategory/prt.label?r=True",
    "Impresoras_Laser": "https://store.intcomex.com/es-XCL/Products/ByCategory/prt.laser?r=True",
    "Impresoras_MFP": "https://store.intcomex.com/es-XCL/Products/ByCategory/prt.mfp?r=True",
    "Scanners": "https://store.intcomex.com/es-XCL/Products/ByCategory/prt.scanner?r=True",
    "All_in_One": "https://store.intcomex.com/es-XCL/Products/ByCategory/cpt.allone?r=True"
}

# --- Configuración WooCommerce ---
# Las credenciales se importan desde credentials.py

# --- Selectores CSS/XPath ---
LOGIN_USERNAME_FIELD_SELECTOR = (By.ID, "UserName")
LOGIN_PASSWORD_FIELD_SELECTOR = (By.ID, "Password")
LOGIN_BUTTON_SELECTOR = (By.ID, "LoginButton")
DOWNLOAD_BUTTON_SELECTOR = (By.CSS_SELECTOR, "a.priceListButtom[href*='Csv']")

# --- Constantes de Filtrado ---
MIN_STOCK = 5  # Stock mínimo requerido (mayor a 5 unidades)
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
        version="wc/v3"
    )


def find_product_by_sku(wcapi, sku):
    """
    Busca un producto en WooCommerce por su SKU.
    
    Args:
        wcapi: Objeto API de WooCommerce
        sku: SKU del producto a buscar
    
    Returns:
        dict: Datos del producto si existe, None si no existe
    """
    try:
        response = wcapi.get("products", params={"sku": str(sku), "per_page": 1})
        if response.status_code == 200:
            products = response.json()
            if products:
                return products[0]
        return None
    except Exception as e:
        print(f"⚠ Error al buscar producto con SKU '{sku}' en WooCommerce: {e}")
        return None


def create_product_in_woocommerce(wcapi, product_data):
    """
    Crea un nuevo producto en WooCommerce.
    
    Args:
        wcapi: Objeto API de WooCommerce
        product_data: Diccionario con los datos del producto
    
    Returns:
        bool: True si se creó exitosamente, False en caso contrario
    """
    try:
        data = {
            "name": product_data.get("title", "Producto sin nombre"),
            "type": "simple",
            "regular_price": str(product_data.get("sale_price", "")),
            "sku": str(product_data.get("sku", "")),
            "stock_quantity": int(product_data.get("stock", 0)),
            "manage_stock": True,
            "stock_status": "instock" if product_data.get("stock", 0) > 0 else "outofstock",
            "shipping_class": "free-shipping",
            "tags": [{"name": "Envío Gratuito"}]
        }
        
        # Agregar descripción si está disponible
        if product_data.get("description"):
            data["short_description"] = str(product_data.get("description"))
        
        # Agregar imagen si está disponible
        if product_data.get("image_url"):
            data["images"] = [{"src": str(product_data.get("image_url"))}]
        
        response = wcapi.post("products", data)
        
        if response.status_code in [200, 201]:
            print(f"  ✓ Producto creado: {product_data.get('title', 'Sin nombre')[:50]}... (SKU: {product_data.get('sku')})")
            return True
        elif response.status_code == 401:
            print(f"  ✗ Error de autenticación al crear producto. Verifica las credenciales API.")
            raise Exception("Error de autenticación WooCommerce")
        elif response.status_code == 403:
            print(f"  ✗ Error de permisos al crear producto. Verifica los permisos de la API.")
            raise Exception("Error de permisos WooCommerce")
        else:
            error_msg = ""
            try:
                error_data = response.json()
                error_msg = str(error_data)
            except:
                error_msg = response.text[:200] if hasattr(response, 'text') else "Sin detalles"
            print(f"  ✗ Error al crear producto {product_data.get('sku')}: HTTP {response.status_code} - {error_msg}")
            return False
            
    except Exception as e:
        print(f"  ✗ Excepción al crear producto {product_data.get('sku', 'N/A')}: {e}")
        return False


def update_product_in_woocommerce(wcapi, product_id, product_data):
    """
    Actualiza un producto existente en WooCommerce.
    
    Args:
        wcapi: Objeto API de WooCommerce
        product_id: ID del producto en WooCommerce
        product_data: Diccionario con los datos actualizados
    
    Returns:
        bool: True si se actualizó exitosamente, False en caso contrario
    """
    try:
        data = {
            "regular_price": str(product_data.get("sale_price", "")),
            "stock_quantity": int(product_data.get("stock", 0)),
            "stock_status": "instock" if product_data.get("stock", 0) > 0 else "outofstock"
        }
        
        response = wcapi.put(f"products/{product_id}", data)
        
        if response.status_code == 200:
            print(f"  ✓ Producto actualizado: ID {product_id} (SKU: {product_data.get('sku')})")
            return True
        else:
            print(f"  ✗ Error al actualizar producto {product_id}: {response.status_code}")
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


def sincronizar_csv(archivo_csv, wcapi, category_name, valor_dolar):
    """
    Procesa un CSV descargado y sincroniza productos con WooCommerce.
    
    ESTRUCTURA DEL CSV:
    - Fila 1: Información general (ignorada)
    - Fila 2: Valor del dólar (ya obtenido del sitio web)
    - Fila 3: Encabezados de columnas (header=2)
    - Fila 4+: Datos de productos
    
    Args:
        archivo_csv: Ruta al archivo CSV
        wcapi: Objeto API de WooCommerce
        category_name: Nombre de la categoría
        valor_dolar: Valor del dólar obtenido del sitio web
    
    Returns:
        dict: Estadísticas de procesamiento
    """
    stats = {
        "procesados": 0,
        "creados": 0,
        "actualizados": 0,
        "filtrados": 0,
        "errores": 0
    }
    
    try:
        print(f"  📖 Procesando CSV: {archivo_csv}")
        print(f"  💵 Usando valor del dólar: ${valor_dolar:,.2f} CLP")
        
        # Leer los productos desde la Fila 3 (header=2 significa que la fila 3 es el encabezado)
        # Separador: TAB, Encoding: utf-16 (con fallback a latin-1)
        df = None
        encodings_to_try = ['utf-16', 'latin-1', 'utf-8', 'iso-8859-1', 'cp1252']
        
        for encoding in encodings_to_try:
            try:
                # Leer CSV con header=2 (la fila 3 contiene los encabezados)
                # Separador TAB, encoding según intento actual
                try:
                    df = pd.read_csv(
                        archivo_csv,
                        encoding=encoding,
                        sep='\t',  # Separador TAB
                        header=2,  # La fila 3 (índice 2) contiene los encabezados
                        low_memory=False,
                        engine='python',
                        on_bad_lines='skip'  # Saltar líneas con errores (pandas < 2.0)
                    )
                except TypeError:
                    # Para pandas >= 2.0
                    try:
                        df = pd.read_csv(
                            archivo_csv,
                            encoding=encoding,
                            sep='\t',
                            header=2,
                            low_memory=False,
                            engine='python',
                            on_bad_lines=lambda x: None
                        )
                    except Exception as e:
                        continue
                
                # Verificar que se leyó correctamente (debe tener varias columnas)
                if df is not None and len(df.columns) > 3:
                    print(f"  ✓ CSV leído con encoding: {encoding}, separador: TAB")
                    break
                else:
                    df = None
            except Exception as e:
                continue
        
        if df is None or len(df.columns) <= 1:
            raise Exception("No se pudo leer el CSV. Formato no reconocido.")
        
        print(f"  ✓ CSV leído: {len(df)} filas de productos, {len(df.columns)} columnas encontradas")
        print(f"  📋 Columnas disponibles: {', '.join(df.columns.tolist()[:5])}...")
        
        # Identificar columnas (nombres en español de Intcomex)
        sku_col = None
        price_col = None
        stock_col = None
        desc_col = None
        image_col = None
        
        for col in df.columns:
            col_str = str(col).strip()
            col_lower = col_str.lower()
            
            # Buscar SKU
            if 'sku' in col_lower or 'codigo' in col_lower or 'parte' in col_lower or 'número' in col_lower:
                sku_col = col
            # Buscar Precio (en español: "Precio")
            elif 'precio' in col_lower or 'price' in col_lower or 'costo' in col_lower or 'cost' in col_lower:
                price_col = col
            # Buscar Stock (en español: "Disponibilidad")
            elif 'disponibilidad' in col_lower or 'stock' in col_lower or 'existencia' in col_lower or 'cantidad' in col_lower or 'inventario' in col_lower:
                stock_col = col
            # Buscar Descripción (en español: "Nombre")
            elif 'nombre' in col_lower or 'name' in col_lower or 'descripcion' in col_lower or 'description' in col_lower or 'producto' in col_lower:
                desc_col = col
            # Buscar Imagen
            elif 'imagen' in col_lower or 'image' in col_lower or 'url' in col_lower or 'foto' in col_lower:
                image_col = col
        
        print(f"  📊 Columnas detectadas:")
        print(f"     - SKU: {sku_col}")
        print(f"     - Precio: {price_col}")
        print(f"     - Stock: {stock_col}")
        print(f"     - Descripción: {desc_col}")
        print(f"     - Imagen: {image_col}")
        
        if not sku_col or not price_col:
            raise Exception(f"Columnas obligatorias no encontradas: SKU={sku_col}, Precio={price_col}")
        
        # Procesar cada fila
        for idx, row in df.iterrows():
            try:
                # Extraer datos
                sku = row[sku_col] if sku_col else None
                price_text = row[price_col] if price_col else None
                
                # Extraer stock de la columna "Disponibilidad" que puede tener formato "11 en inventario" o "Más de 20"
                stock = 0
                if stock_col and pd.notna(row[stock_col]):
                    stock_text = str(row[stock_col]).strip()
                    # Buscar números en el texto (ej: "11 en inventario" -> 11, "Más de 20" -> 20)
                    numbers = re.findall(r'\d+', stock_text)
                    if numbers:
                        stock = int(numbers[0])
                    elif 'más' in stock_text.lower() or 'more' in stock_text.lower() or 'mayor' in stock_text.lower():
                        # Si dice "Más de 20" o similar, extraer el número o asumir mínimo + 1
                        numbers = re.findall(r'\d+', stock_text)
                        if numbers:
                            stock = int(numbers[0]) + 1  # "Más de 20" -> 21
                        else:
                            stock = MIN_STOCK + 1  # Si no hay número, asumir mínimo requerido + 1
                
                description = str(row[desc_col]) if desc_col and pd.notna(row[desc_col]) else "Sin descripción"
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
                
                # FILTRADO: Stock > 5 (filtro por precio eliminado - todas las categorías tienen precios altos)
                if stock <= MIN_STOCK:
                    stats["filtrados"] += 1
                    if idx < 5:  # Mostrar primeros 5 filtrados para debugging
                        print(f"    ⊘ Filtrado (stock insuficiente): {description[:50]}... - Stock: {stock} (mínimo requerido: >{MIN_STOCK})")
                    continue
                
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
                
                # Preparar datos del producto
                product_data = {
                    "title": description,
                    "description": description,
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
                
                time.sleep(0.3)  # Pequeña pausa entre productos para no sobrecargar la API
                
            except Exception as e:
                stats["errores"] += 1
                print(f"  ⚠ Error procesando fila {idx}: {e}")
                continue
        
        return stats
        
    except Exception as e:
        print(f"  ✗ Error al procesar CSV: {e}")
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
    
    try:
        # Paso 1: Login obligatorio
        print("\n" + "="*60)
        print("PASO 1: INICIO DE SESIÓN")
        print("="*60)
        if not login_intcomex(driver, USERNAME, PASSWORD):
            print("✗ El inicio de sesión falló. El bot no puede continuar.")
            exit(1)
        
        # Paso 2: Obtener valor del dólar del sitio web
        print("\n" + "="*60)
        print("PASO 2: OBTENER VALOR DEL DÓLAR")
        print("="*60)
        valor_dolar = obtener_dolar_web(driver)
        print(f"✓ Valor del dólar obtenido: ${valor_dolar:,.2f} CLP")
        
        # Paso 3: Procesar cada categoría
        print("\n" + "="*60)
        print("PASO 3: DESCARGAS Y SINCRONIZACIÓN")
        print("="*60)
        
        for category_name, category_url in URLS.items():
            try:
                # Descargar CSV de la categoría
                csv_file = download_category_csv(driver, category_name, category_url)
                
                if csv_file and os.path.exists(csv_file):
                    # Procesar y sincronizar CSV usando el valor del dólar obtenido del sitio web
                    stats = sincronizar_csv(csv_file, wcapi, category_name, valor_dolar)
                    
                    # Acumular estadísticas
                    total_stats["categorias_procesadas"] += 1
                    total_stats["productos_procesados"] += stats["procesados"]
                    total_stats["productos_creados"] += stats["creados"]
                    total_stats["productos_actualizados"] += stats["actualizados"]
                    total_stats["productos_filtrados"] += stats["filtrados"]
                    total_stats["errores"] += stats["errores"]
                    
                    print(f"  📊 Resumen {category_name}:")
                    print(f"     - Procesados: {stats['procesados']}")
                    print(f"     - Creados: {stats['creados']}")
                    print(f"     - Actualizados: {stats['actualizados']}")
                    print(f"     - Filtrados: {stats['filtrados']}")
                    print(f"     - Errores: {stats['errores']}")
                else:
                    total_stats["categorias_fallidas"] += 1
                    print(f"  ✗ No se pudo descargar CSV para {category_name}")
                
                time.sleep(2)  # Pausa entre categorías
                
            except Exception as e:
                total_stats["categorias_fallidas"] += 1
                print(f"  ✗ Error procesando categoría {category_name}: {e}")
                continue
        
        # Resumen final
        print("\n" + "="*60)
        print("✅ SINCRONIZACIÓN COMPLETADA")
        print("="*60)
        print(f"Categorías procesadas: {total_stats['categorias_procesadas']}")
        print(f"Categorías fallidas: {total_stats['categorias_fallidas']}")
        print(f"Productos procesados: {total_stats['productos_procesados']}")
        print(f"Productos creados: {total_stats['productos_creados']}")
        print(f"Productos actualizados: {total_stats['productos_actualizados']}")
        print(f"Productos filtrados: {total_stats['productos_filtrados']}")
        print(f"Errores: {total_stats['errores']}")
        print("="*60)
        
    except KeyboardInterrupt:
        print("\n\n⚠ Proceso interrumpido por el usuario.")
    except Exception as e:
        print(f"\n✗ Error general durante la ejecución: {e}")
        import traceback
        traceback.print_exc()
    finally:
        driver.quit()
        print("\n🔒 Navegador cerrado. Bot finalizado.")
