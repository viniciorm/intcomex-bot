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
import json
import logging
import glob
import io
from pathlib import Path
from datetime import datetime
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from webdriver_manager.chrome import ChromeDriverManager
import random
import sys
import pyautogui
import pyperclip
import platform

# Detectar Sistema Operativo para atajos de teclado
OS_TYPE = platform.system()
CONTROL_KEY = 'command' if OS_TYPE == 'Darwin' else 'ctrl'

class LoginException(Exception):
    """Excepción personalizada para fallos de login."""
    pass

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
    "Notebooks": "https://store.intcomex.com/es-XCL/Products/ByCategory/cpt.notebook?r=True",
    "Monitores": "https://store.intcomex.com/es-XCL/Products/ByCategory/mnt.monitor?r=True",
    "Monitores_TV": "https://store.intcomex.com/es-XCL/Products/ByCategory/mnt.tv?r=True",
    "Desktop": "https://store.intcomex.com/es-XCL/Products/ByCategory/cpt.desktop?r=True",
    "Tablets": "https://store.intcomex.com/es-XCL/Products/ByCategory/cpt.tablet?r=True",
    "Impresoras_Inkjet": "https://store.intcomex.com/es-XCL/Products/ByCategory/prt.inkjet?r=True",
    "Impresoras_Label": "https://store.intcomex.com/es-XCL/Products/ByCategory/prt.label?r=True",
    "Impresoras_Laser": "https://store.intcomex.com/es-XCL/Products/ByCategory/prt.laser?r=True",
    "Impresoras_MFP": "https://store.intcomex.com/es-XCL/Products/ByCategory/prt.mfp?r=True",
    "Scanners": "https://store.intcomex.com/es-XCL/Products/ByCategory/prt.scanner?r=True",
    "All_in_One": "https://store.intcomex.com/es-XCL/Products/ByCategory/cpt.allone?r=True",
    "Discos_Duros_Internos": "https://store.intcomex.com/es-XCL/Products/ByCategory/sto.inthd?r=True",
    "Discos_Duros_Externos": "https://store.intcomex.com/es-XCL/Products/ByCategory/sto.exthd?r=True",
    "Discos_SSD_Internos": "https://store.intcomex.com/es-XCL/Products/ByCategory/sto.ssd?r=True",
    "Discos_SSD_Externos": "https://store.intcomex.com/es-XCL/Products/ByCategory/sto.ssdext?r=True",
    "Procesadores": "https://store.intcomex.com/es-XCL/Products/ByCategory/cco.cpu?r=True"
}

# --- Validación de Categorías ---
# Este diccionario mapea la categoría de URLS a palabras clave permitidas
# en las columnas 'Categoría' o 'Subcategoría' del CSV de Intcomex.
CATEGORY_VALIDATION = {
    "Notebooks": ["Notebook", "Portátiles", "Laptops"],
    "Monitores": ["Monitores", "Monitor", "Pantallas"],
    "Monitores_TV": ["Televisores", "TV", "Monitores"],
    "Desktop": ["Desktop", "Computadores", "CPU"],
    "Tablets": ["Tablet", "Tabletas"],
    "Impresoras_Inkjet": ["Inkjet", "Inyección"],
    "Impresoras_Label": ["Label", "Etiquetas"],
    "Impresoras_Laser": ["Laser", "Láser"],
    "Impresoras_MFP": ["Multifuncionales", "Multifunción", "MFP"],
    "Scanners": ["Scanner", "Escáner"],
    "All_in_One": ["Todo-en-Uno", "All-in-One"],
    "Discos_Duros_Internos": ["Disco Duro Interno", "HDD", "Disco Duro", "Almacenamiento Interno"],
    "Discos_Duros_Externos": ["Disco Duro Externo", "Storage Externo"],
    "Discos_SSD_Internos": ["SSD", "Unidad de Estado Sólido", "Solid State", "NVMe", "SATA", "PCIe", "M.2"],
    "Discos_SSD_Externos": ["SSD Externo", "Solid State Drive Externo", "Almacenamiento Externo"],
    "Procesadores": ["Procesador", "CPU", "Microprocesador", "Processor", "Intel", "AMD"]
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
DATA_PATH = "data_activa"
DOWNLOAD_DIR = os.path.join(os.getcwd(), "downloads")
STATE_FILE = os.path.join(DATA_PATH, "estado_productos.json")
MAPA_IMAGENES_PATH = os.path.join(DATA_PATH, "mapa_imagenes.json")
os.makedirs(DOWNLOAD_DIR, exist_ok=True)
os.makedirs(DATA_PATH, exist_ok=True)

# Suprimir mensajes de logging
logging.getLogger('selenium').setLevel(logging.WARNING)
logging.getLogger('urllib3').setLevel(logging.WARNING)


# --- Funciones de Persistencia ---

def load_state():
    """Carga el estado de los productos desde el archivo JSON."""
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"⚠ Error al cargar {STATE_FILE}: {e}")
            return {}
    return {}

def save_state(state):
    """Guarda el estado de los productos en el archivo JSON."""
    try:
        with open(STATE_FILE, 'w', encoding='utf-8') as f:
            json.dump(state, f, indent=4, ensure_ascii=False)
    except Exception as e:
        print(f"✗ Error al guardar {STATE_FILE}: {e}")

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
            "tags": [{"name": "Envío Gratuito"}],
            "meta_data": [
                {
                    "key": "n8n_mejorado",
                    "value": "false"
                }
            ]
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
            "categories": product_data.get("categories", []),
            "meta_data": [
                {
                    "key": "n8n_mejorado",
                    "value": "false"
                }
            ]
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

def escribir_como_humano(element, text):
    """Escribe texto en un elemento simulando el ritmo humano."""
    for char in text:
        element.send_keys(char)
        time.sleep(random.uniform(0.1, 0.3))

def login_intcomex(driver, username, password):
    """
    Inicia sesión en Intcomex usando "Fuerza Bruta" con PyAutoGUI.
    Asegura el foco usando Shift+Tab y limpia el campo antes de escribir.
    """
    print(f"🌐 Navegando a: {LOGIN_URL}")
    driver.get(LOGIN_URL)
    
    # 1. Maximizar y esperar a que la carga sea completa
    print("📺 Maximizando ventana y esperando 5 segundos...")
    driver.maximize_window()
    time.sleep(5)
    
    try:
        # Asegurar que estamos en el contenido principal
        driver.switch_to.default_content()
        
        # 2. Asegurar Foco en la ventana (Clic en el cuerpo)
        print("🖱️  Asegurando foco en la ventana...")
        driver.execute_script("window.scrollTo(0, 0);")
        time.sleep(0.5)
        
        # Intentar clickear el campo de correo vía Selenium para centrar el foco
        print("🤖 Intentando foco Selenium en campo correo...")
        selectors_email = [
            (By.ID, "email"), # Común en B2C
            (By.ID, "logonIdentifier"), # Común en B2C
            (By.ID, "txtEmail"),
            (By.NAME, "email"),
            (By.CSS_SELECTOR, "input[type='email']")
        ]
        
        email_element = None
        for selector in selectors_email:
            try:
                email_element = driver.find_element(selector[0], selector[1])
                if email_element.is_displayed():
                    print(f"   ✓ Encontrado por {selector[0]}='{selector[1]}'")
                    # Usar click para enfocar
                    driver.execute_script("arguments[0].focus();", email_element)
                    time.sleep(0.5)
                    email_element.click()
                    break
            except: continue
        
        time.sleep(1)
        
        # 3. Forzar Foco adicional con Shift+Tab (x2 para re-entrar si es necesario)
        print("⌨️  Garantizando foco con Shift+Tab...")
        pyautogui.hotkey('shift', 'tab')
        time.sleep(0.3)
        pyautogui.press('tab') # Volver a entrar
        time.sleep(0.5)
        
        # 4. Limpiar campo (Ctrl + A + Backspace)
        print("⌨️  Limpiando campo...")
        pyautogui.hotkey(CONTROL_KEY, 'a')
        time.sleep(0.3)
        pyautogui.press('backspace')
        time.sleep(0.5)
        
        # 5. Escritura de Usuario (Uso de Portapapeles para evitar fallos con '@')
        print(f"⌨️  Pegando usuario desde portapapeles...")
        pyperclip.copy(username)
        time.sleep(0.5)
        pyautogui.hotkey(CONTROL_KEY, 'v')
        time.sleep(0.8)
        
        # 6. Saltar a Contraseña (Tab)
        print("⌨️  Saltando a contraseña (TAB)...")
        pyautogui.press('tab')
        time.sleep(0.8)
        
        # 7. Escribir Contraseña (Uso de Portapapeles para robustez)
        print("⌨️  Pegando contraseña...")
        pyperclip.copy(password)
        time.sleep(0.5)
        pyautogui.hotkey(CONTROL_KEY, 'v')
        time.sleep(0.8)
        
        # 8. Entrar (ENTER)
        print("⌨️  Enviando formulario (ENTER)...")
        pyautogui.press('enter')
        
        # 8. Validación Rápida (10 segundos)
        print("🔍 Validando acceso (espera 10s)...")
        for i in range(10):
            # Check por URL (si ya no estamos en login)
            current_url = driver.current_url.lower()
            if "login" not in current_url and "account" not in current_url:
                print(f"✓ Inicio de sesión detectado por URL: {driver.current_url}")
                return True
                
            # Check por elementos de éxito
            success_indicators = [
                (By.CSS_SELECTOR, "a[href*='logout']"),
                (By.CSS_SELECTOR, ".user-menu"),
                (By.ID, "CountrySelector")
            ]
            for indicator in success_indicators:
                try:
                    if driver.find_elements(indicator[0], indicator[1]):
                        print("✓ Inicio de sesión exitoso detectado.")
                        return True
                except: pass
            
            time.sleep(1)
            
        print("✗ No se detectó cambio de estado en 10 segundos.")
        return False
        
    except Exception as e:
        print(f"✗ Error durante la fuerza bruta de login: {e}")
        driver.save_screenshot("login_error_brute_force.png")
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


def close_banners(driver):
    """Detecta y cierra banners y popups publicitarios de forma exhaustiva."""
    popup_selectors = [
        (By.CSS_SELECTOR, ".popin_img_img"),
        (By.CSS_SELECTOR, ".popup-close"),
        (By.CSS_SELECTOR, ".modal-header .close"),
        (By.CSS_SELECTOR, "[class*='popup'] [class*='close']"),
        (By.CSS_SELECTOR, "[class*='ad'] [class*='close']"),
        (By.CSS_SELECTOR, ".p-close"),
        (By.XPATH, "//button[contains(@class, 'close') or contains(@id, 'close')]"),
    ]
    
    found_any = False
    for attempt in range(2): # Intentar un par de veces por si hay capas
        for selector in popup_selectors:
            try:
                popups = driver.find_elements(selector[0], selector[1])
                for popup in popups:
                    if popup.is_displayed():
                        print(f"  🗙 Cerrando popup/banner detectado (intento {attempt+1})...")
                        driver.execute_script("arguments[0].click();", popup)
                        found_any = True
                        time.sleep(1)
            except:
                continue
    return found_any

def download_category_csv(driver, category_name, category_url):
    """
    Navega a una categoría y descarga su CSV con validaciones robustas.
    """
    try:
        print(f"\n📥 Procesando categoría: {category_name}")
        print(f"   URL: {category_url}")
        
        # Navegar a la categoría
        driver.get(category_url)
        time.sleep(4)  # Esperar un poco más
        
        # 1. Validar que la URL cargada sea la correcta o contenga el segmento esperado
        # Intcomex a veces redirige si hay errores de sesión o banners
        current_url = driver.current_url.lower()
        segmento_esperado = category_url.split('/')[-1].split('?')[0].lower()
        if segmento_esperado not in current_url and "login" not in current_url:
            print(f"  ⚠ Advertencia: URL actual ({current_url}) no parece coincidir con la esperada ({segmento_esperado})")
            print(f"  🔄 Re-navegando para asegurar fidelidad...")
            driver.get(category_url)
            time.sleep(3)

        # 2. Cerrar banners publicitarios
        close_banners(driver)
        
        # Buscar y hacer click en el botón de descarga
        wait = WebDriverWait(driver, 15)
        try:
            # Buscar el botón de descarga
            download_button = wait.until(EC.presence_of_element_located(DOWNLOAD_BUTTON_SELECTOR))
            print(f"  ✓ Botón de descarga encontrado")
            
            # Re-confirmar que no haya aparecido un banner justo antes del click
            close_banners(driver)
            
            # Hacer scroll y click
            driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", download_button)
            time.sleep(1)
            
            # Click "seguro" usando JS
            print(f"  🖱️  Haciendo clic en botón de descarga...")
            driver.execute_script("arguments[0].click();", download_button)
            
            # Esperar a que aparezca el archivo descargado
            csv_file = wait_for_download(category_name, timeout=40)
            return csv_file
            
        except Exception as e:
            print(f"  ✗ Error al ubicar/clickear botón de descarga: {e}")
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


def sincronizar_csv(archivo_csv, category_name, valor_dolar):
    """
    Procesa un CSV descargado y actualiza el estado local (estado_productos.json).
    Ya no sincroniza directamente con WooCommerce (Fase A).
    """
    stats = {"procesados": 0, "creados": 0, "actualizados": 0, "filtrados": 0, "errores": 0}
    nuevos_skus = []
    
    state = load_state()
    print(f"  💵 Usando valor del dólar: ${valor_dolar:,.2f} CLP")
    
    # Lectura ULTRA robusta
    try:
        with open(archivo_csv, 'r', encoding='utf-16') as f:
            lines = f.readlines()
        
        header_idx = -1
        for i, line in enumerate(lines[:20]):
            l = line.lower()
            if 'sku' in l or 'categoría' in l or 'nombre' in l:
                header_idx = i
                break
        
        if header_idx == -1:
            raise Exception("No se encontró la fila de cabecera en el CSV")

        csv_content = "".join(lines[header_idx:])
        df = pd.read_csv(io.StringIO(csv_content), sep='\t', decimal=',', on_bad_lines='skip', engine='python')
        
    except Exception as e:
        print(f"  ❌ Fallo crítico en lectura de CSV: {e}")
        return stats

    if df.empty:
        return stats
    
    df = df.dropna(subset=[df.columns[0]])
    
    # Mapeo de columnas
    sku_col = next((col for col in df.columns if 'sku' in str(col).lower()), None)
    price_col = next((col for col in df.columns if 'precio' in str(col).lower()), None)
    stock_col = next((col for col in df.columns if any(x in str(col).lower() for x in ['disponibilidad', 'existencia', 'disponibil'])), None)
    desc_col = next((col for col in df.columns if any(x in str(col).lower() for x in ['nombre', 'descripción'])), None)
    attr_col = next((col for col in df.columns if 'atrib' in str(col).lower()), None)
    cat_col = next((col for col in df.columns if 'categor' in str(col).lower() and 'sub' not in str(col).lower()), None)
    subcat_col = next((col for col in df.columns if 'subcategor' in str(col).lower()), None)

    # Palabras clave para validar esta categoría específica
    valid_keywords = CATEGORY_VALIDATION.get(category_name, [])

    for idx, row in df.iterrows():
        try:
            sku = str(row[sku_col]).strip() if sku_col and pd.notna(row[sku_col]) else None
            if not sku: continue
            
            # --- VALIDACIÓN DE CATEGORÍA ---
            if valid_keywords:
                cat_text = ""
                if cat_col and pd.notna(row[cat_col]): 
                    cat_text += str(row[cat_col])
                if subcat_col and pd.notna(row[subcat_col]): 
                    cat_text += " " + str(row[subcat_col])
                
                # Si no hay ninguna palabra clave en el texto de categoría, saltar
                if not any(kw.lower() in cat_text.lower() for kw in valid_keywords):
                    # Opcional: Loguear solo los primeros fallos para no saturar
                    if stats["filtrados"] < 3:
                        print(f"    ⚠ Filtrado por categoría incorrecta: SKU {sku} ({cat_text[:30]}...)")
                    stats["filtrados"] += 1
                    continue
            # -------------------------------
            
            description = str(row[desc_col]) if desc_col and pd.notna(row[desc_col]) else "Sin descripción"
            
            # --- FILTRADO GENERALIZADO POR SUFIJO Y LIQUIDACIONES ---
            sku_upper = sku.upper()
            name_upper = description.upper()
            
            # Excluir SKUs con sufijos especiales (ej: -B1, -RC, -EX, -S)
            # Buscamos la presencia de un guión que indica una variante
            is_special_suffix = '-' in sku_upper
            
            # Excluir Liquidaciones y Ofertas (términos solicitados por el usuario)
            is_liquidation = 'LIQUIDACION' in name_upper or 'OFERTA' in name_upper
            
            if is_special_suffix or is_liquidation:
                if stats["filtrados"] < 10: # Loguear algunos ejemplos más
                    motivo = f"Sufijo especial ({sku_upper})" if is_special_suffix else "Liquidación/Oferta"
                    print(f"    🚫 Filtrado por {motivo}: SKU {sku} - {description[:40]}...")
                stats["filtrados"] += 1
                continue
            # --------------------------------------------------------
            
            precio_usd = clean_price_to_float(row[price_col])
            if precio_usd is None or precio_usd <= 0: continue
            
            precio_costo_clp = round(precio_usd * valor_dolar)
            precio_venta_clp = round(precio_costo_clp / (1 - MARGIN_PERCENTAGE))
            
            stock = extract_stock_number(row[stock_col]) if stock_col and pd.notna(row[stock_col]) else 0
            description = str(row[desc_col]) if desc_col and pd.notna(row[desc_col]) else "Sin descripción"
            
            # Actualizar estado
            is_new = sku not in state
            
            state[sku] = {
                "sku": sku,
                "nombre": description,
                "cost_price": precio_costo_clp,
                "sale_price": precio_venta_clp,
                "stock": stock,
                "categoria_principal": category_name,
                "categoria_csv": str(row[cat_col]) if cat_col and pd.notna(row[cat_col]) else None,
                "subcategoria_csv": str(row[subcat_col]) if subcat_col and pd.notna(row[subcat_col]) else None,
                "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "tiene_imagen": state.get(sku, {}).get("tiene_imagen", False),
                "subido_a_woo": state.get(sku, {}).get("subido_a_woo", False),
                # Marcar para subir a WooCommerce si cambiaron datos críticos o es nuevo
                "pendiente_sync_woo": True 
            }
            
            if is_new:
                stats["creados"] += 1
                nuevos_skus.append(sku)
            else:
                stats["actualizados"] += 1
                
            stats["procesados"] += 1
        except:
            stats["errores"] += 1

    save_state(state)
    return stats, nuevos_skus

# --- Funciones de Ejecución ---

def run_sync_bot(driver=None, skip_download=False):
    """
    Ejecuta el bot de sincronización completo.
    Retorna (total_stats, nuevos_skus_detectados)
    """
    print("="*60)
    print("🤖 BOT DE SINCRONIZACIÓN INTCOMEX -> LOCAL STATE (FASE A)")
    print("="*60)
    
    must_close_driver = False
    if not driver:
        must_close_driver = True
        print("🌐 Inicializando navegador...")
        chrome_options = ChromeOptions()
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--log-level=3")
        chrome_options.add_experimental_option("excludeSwitches", ["enable-logging"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        
        prefs = {
            "download.default_directory": DOWNLOAD_DIR,
            "download.prompt_for_download": False,
            "download.directory_upgrade": True,
            "safebrowsing.enabled": True
        }
        chrome_options.add_experimental_option("prefs", prefs)
        
        service = ChromeService(ChromeDriverManager().install())
        service.log_path = "NUL"
        driver = webdriver.Chrome(service=service, options=chrome_options)
        driver.maximize_window()

    total_stats = {
        "categorias_procesadas": 0,
        "categorias_fallidas": 0,
        "productos_procesados": 0,
        "productos_creados": 0,
        "productos_actualizados": 0,
        "productos_filtrados": 0,
        "errores": 0
    }
    todos_los_nuevos_skus = []
    descargas_exitosas = {}
    errores_descarga = []
    valor_dolar = 970.0 # Valor por defecto
    
    try:
        if skip_download:
            print("\n📂 MODO LOCAL: Saltando login y descargas. Usando archivos existentes...")
            for cat_name in URLS.keys():
                csv_path = os.path.join(DOWNLOAD_DIR, f"{cat_name}.csv")
                if os.path.exists(csv_path):
                    descargas_exitosas[cat_name] = csv_path
                else:
                    print(f"  ⚠ CSV local no encontrado para: {cat_name}")
        else:
            # FASE 1: DESCARGAS
            print("\nPASO 1.1: INICIO DE SESIÓN (REINTENTOS ACTIVADOS)")
            login_success = False
            max_intentos = 3
            for intento in range(1, max_intentos + 1):
                print(f"🤖 Intento de login #{intento} de {max_intentos}...")
                if login_intcomex(driver, USERNAME, PASSWORD):
                    login_success = True
                    break
                else:
                    print(f"✗ Intento #{intento} fallido.")
                    if intento < max_intentos:
                        print("🔄 Reintentando en 5 segundos...")
                        time.sleep(5)
            
            if not login_success:
                print("❌ Todos los intentos de login fallaron.")
                if must_close_driver: driver.quit()
                raise LoginException("Fallo de autenticación tras 3 intentos con PyAutoGUI")
            
            print("\nPASO 1.2: OBTENER VALOR DEL DÓLAR")
            valor_dolar = obtener_dolar_web(driver)
            
            print("\nPASO 1.3: DESCARGA DE CSVs")
            for cat_name, cat_url in URLS.items():
                try:
                    csv_file = download_category_csv(driver, cat_name, cat_url)
                    if csv_file and os.path.exists(csv_file):
                        descargas_exitosas[cat_name] = csv_file
                    else:
                        errores_descarga.append(cat_name)
                except Exception as e:
                    print(f"  ⚠ Error descargando {cat_name}: {e}")
                    errores_descarga.append(cat_name)
                time.sleep(2)

    except Exception as e:
        print(f"\n✗ Error crítico en descargas: {e}")
        if isinstance(e, LoginException):
             raise e
    finally:
        if must_close_driver:
            print("\n🔒 Cerrando navegador...")
            driver.quit()

    # FASE 2: ACTUALIZACIÓN DE ESTADO LOCAL
    if descargas_exitosas:
        print("\n" + "="*60)
        print("FASE 2: ACTUALIZACIÓN DE ESTADO LOCAL (JSON)")
        print("="*60)
        
        for cat_name, csv_path in descargas_exitosas.items():
            try:
                print(f"\n🚀 Procesando CSV: {cat_name}")
                stats, nuevos_skus = sincronizar_csv(csv_path, cat_name, valor_dolar)
                
                total_stats["categorias_procesadas"] += 1
                total_stats["productos_procesados"] += stats.get("procesados", 0)
                total_stats["productos_creados"] += stats.get("creados", 0)
                total_stats["productos_actualizados"] += stats.get("actualizados", 0)
                total_stats["errores"] += stats.get("errores", 0)
                todos_los_nuevos_skus.extend(nuevos_skus)
                
            except Exception as e:
                total_stats["categorias_fallidas"] += 1
                print(f"  ✗ Error procesando {cat_name}: {e}")

    total_stats["categorias_fallidas"] += len(errores_descarga)
    
    print("\n" + "="*60)
    print("✅ FASE A FINALIZADA (ESTADO ACTUALIZADO)")
    print(f"Nuevos en JSON: {total_stats['productos_creados']} | Actualizados en JSON: {total_stats['productos_actualizados']}")
    print("="*60)
    
    return total_stats, todos_los_nuevos_skus

    total_stats["categorias_fallidas"] += len(errores_descarga)
    
    # Reporte final por consola
    print("\n" + "="*60)
    print("✅ PROCESO FINALIZADO")
    print(f"Creados: {total_stats['productos_creados']} | Actualizados: {total_stats['productos_actualizados']}")
    print("="*60)
    
    return total_stats, todos_los_nuevos_skus

if __name__ == "__main__":
    # Si se ejecuta directamente, también envía el reporte por correo al final
    stats, nuevos = run_sync_bot()
    # Mock descargas para el reporte (usamos las procesadas)
    # Nota: No tenemos la lista exacta de archivos aquí para enviar_reporte original sin cambios,
    # pero el orquestador se encargará del reporte consolidado.
    # Por ahora mantenemos compatibilidad mínima si alguien usa este script solo.
    pass
