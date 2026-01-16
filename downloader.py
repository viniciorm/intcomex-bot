import os
import time
import re
import json
import glob
from datetime import date
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver import Chrome, ChromeOptions
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service
from credentials import INTCOMEX_USERNAME, INTCOMEX_PASSWORD

# Configuración de URLs y Selectores
LOGIN_URL = "https://store.intcomex.com/es-XCL/Account/Login"
DOWNLOAD_DIR = os.path.join(os.getcwd(), "downloads")
STATE_FILE = "estado_productos.json"

URLS = {
    "Notebooks": "https://store.intcomex.com/es-XCL/Products/ByCategory/cpt.notebook?r=True",
    "Monitores": "https://store.intcomex.com/es-XCL/Products/ByCategory/mnt.monitor?r=True",
    "Desktop": "https://store.intcomex.com/es-XCL/Products/ByCategory/cpt.desktop?r=True",
    "Tablets": "https://store.intcomex.com/es-XCL/Products/ByCategory/cpt.tablet?r=True",
    "All_in_One": "https://store.intcomex.com/es-XCL/Products/ByCategory/cpt.allone?r=True"
}

INVALID_PATTERNS = ["no_image", "sin_imagen", "placeholder", "default", "coming-soon", "not_available", "noimage"]

class IntcomexScraper:
    def __init__(self, download_dir=DOWNLOAD_DIR):
        self.download_dir = download_dir
        if not os.path.exists(self.download_dir):
            os.makedirs(self.download_dir)
        
        self.options = ChromeOptions()
        self.options.add_argument("--disable-blink-features=AutomationControlled")
        self.options.add_argument("--no-sandbox")
        self.options.add_argument("--disable-dev-shm-usage")
        self.options.add_experimental_option("prefs", {
            "download.default_directory": self.download_dir,
            "download.prompt_for_download": False,
            "download.directory_upgrade": True,
            "safebrowsing.enabled": True
        })
        self.driver = None
        self.image_map = {}
        self.product_state = self._load_state()

    def _load_state(self):
        if os.path.exists(STATE_FILE):
            try:
                with open(STATE_FILE, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                return {}
        return {}

    def _save_state(self):
        try:
            with open(STATE_FILE, 'w', encoding='utf-8') as f:
                json.dump(self.product_state, f, indent=4)
            print(f"💾 Estado de productos guardado en: {STATE_FILE}")
        except Exception as e:
            print(f"⚠️ Error al guardar estado: {e}")

    def start_browser(self):
        print("🌐 Iniciando navegador...")
        self.driver = Chrome(service=Service(ChromeDriverManager().install()), options=self.options)
        self.driver.maximize_window()

    def login(self):
        print(f"🔑 Navegando a login: {LOGIN_URL}")
        self.driver.get(LOGIN_URL)
        print("🔍 Por favor, realiza el login manual en la ventana de Chrome.")
        print("Esperando a que el login sea exitoso...")
        
        wait = WebDriverWait(self.driver, 300) # 5 minutos para login manual
        wait.until(lambda d: "Login" not in d.current_url and "login" not in d.current_url.lower())
        print("✅ Login detectado exitosamente.")

    def get_dollar_value(self):
        print("💵 Extrayendo valor del dólar...")
        try:
            element = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.ID, "lblExchangeRate"))
            )
            text = element.text
            valor = float(re.sub(r'[^\d.]', '', text.replace(',', '.')))
            print(f"✅ Valor del dólar encontrado: ${valor}")
            return valor
        except Exception as e:
            print(f"⚠️ No se pudo obtener el dólar automáticamente: {e}. Usando valor por defecto 810.")
            return 810.0

    def is_valid_image(self, url):
        if not url: return False
        url_lower = url.lower()
        for pattern in INVALID_PATTERNS:
            if pattern in url_lower:
                return False
        return True

    def harvest_images_and_pagination(self, category_name):
        print(f"📸 Iniciando recolección inteligente para {category_name}...")
        page_count = 1
        max_pages = 20
        today = str(date.today())
        
        while page_count <= max_pages:
            print(f"   📄 Escaneando página {page_count}...")
            time.sleep(3) # Esperar carga de la grilla
            
            # Obtener contenedores de productos (grilla de 30)
            items = self.driver.find_elements(By.CSS_SELECTOR, ".product-item, .product-list-item, div[data-sku]")
            
            total_items = len(items)
            known_with_image = 0
            
            for item in items:
                try:
                    sku = item.get_attribute("data-sku") or item.find_element(By.CSS_SELECTOR, ".sku, [class*='sku']").text.strip()
                    if not sku: continue
                    
                    # Verificar si ya lo conocemos y tiene imagen
                    if sku in self.product_state and self.product_state[sku].get("tiene_imagen"):
                        known_with_image += 1
                        self.product_state[sku]["ultima_vista"] = today
                        # Si ya tiene imagen, no necesitamos extraer el src de nuevo, 
                        # pero si queremos que esté en el image_map para el uploader en esta sesión,
                        # necesitamos tener una URL guardada en el estado también (opcional pero recomendado)
                        # Por ahora el requisito dice: "actualiza la ultima_vista sin volver a procesar la imagen"
                        continue
                    
                    # Si es nuevo o no tiene imagen, extraer
                    img_element = item.find_element(By.CSS_SELECTOR, "img")
                    img_url = img_element.get_attribute("src")
                    
                    es_valida = self.is_valid_image(img_url)
                    
                    # Actualizar estado
                    self.product_state[sku] = {
                        "tiene_imagen": es_valida,
                        "ultima_vista": today
                    }
                    
                    if es_valida:
                        self.image_map[sku] = img_url
                        
                except:
                    continue
            
            # Optimización: Si todos en la página ya tenían imagen, saltar "Siguiente" rápido
            if total_items > 0 and known_with_image == total_items:
                print(f"      ⚡ Página conocida (30/30 con imagen). Saltando rápido...")
            
            # Buscar botón de siguiente página
            try:
                next_button = self.driver.find_element(By.CSS_SELECTOR, "a.next, .pagination-next, a[title*='Siguiente'], a[title*='Next']")
                if "disabled" in next_button.get_attribute("class") or not next_button.is_displayed():
                    print("   🏁 Última página alcanzada.")
                    break
                
                # Scroll y click
                self.driver.execute_script("arguments[0].scrollIntoView();", next_button)
                time.sleep(1)
                self.driver.execute_script("arguments[0].click();", next_button)
                page_count += 1
            except:
                print("   🏁 No se encontró botón de siguiente página.")
                break

    def download_csv(self, category_name):
        print(f"📥 Descargando CSV para {category_name}...")
        try:
            download_btn = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, "a.priceListButtom[href*='Csv']"))
            )
            self.driver.execute_script("arguments[0].click();", download_btn)
            time.sleep(5)
            return True
        except Exception as e:
            print(f"❌ Error al descargar CSV for {category_name}: {e}")
            return False

    def run(self):
        downloaded_files = []
        dollar_value = 810.0
        
        try:
            self.start_browser()
            self.login()
            dollar_value = self.get_dollar_value()
            
            for name, url in URLS.items():
                print(f"\n📂 Procesando Categoría: {name}")
                self.driver.get(url)
                self.harvest_images_and_pagination(name)
                if self.download_csv(name):
                    time.sleep(2)
                    files = glob.glob(os.path.join(self.download_dir, "*.csv"))
                    files = [f for f in files if not f.endswith("mapa_imagenes.json")]
                    if files:
                        latest_file = max(files, key=os.path.getctime)
                        new_path = os.path.join(self.download_dir, f"{name}.csv")
                        if os.path.exists(new_path): os.remove(new_path)
                        os.rename(latest_file, new_path)
                        downloaded_files.append(new_path)
                        print(f"✅ Archivo guardado: {new_path}")
            
            print(f"✅ Extracción terminada. {len(downloaded_files)} CSVs obtenidos.")
            
            # Guardar mapa de imágenes para el uploader (solo lo extraído en esta sesión)
            map_path = os.path.join(self.download_dir, "mapa_imagenes.json")
            with open(map_path, 'w', encoding='utf-8') as f:
                json.dump(self.image_map, f, indent=4)
            
            # Guardar estado global persistente
            self._save_state()
            
            return {
                "dollar_value": dollar_value,
                "downloaded_files": downloaded_files,
                "image_map": self.image_map
            }
        finally:
            if self.driver:
                self.driver.quit()

if __name__ == "__main__":
    scraper = IntcomexScraper()
    # Para pruebas: scraper.run()
