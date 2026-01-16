import os
import time
import re
import json
import glob
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
            # El valor suele estar en un elemento específico del header o similar
            # Según inspecciones previas, el bot ya lo obtenía así:
            element = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.ID, "lblExchangeRate"))
            )
            text = element.text
            valor = float(re.sub(r'[^\d.]', '', text.replace(',', '.')))
            print(f"✅ Valor del dólar encontrado: ${valor}")
            return valor
        except Exception as e:
            print(f"⚠️ No se pudo obtener el dólar automáticamente: {e}. Usando valor por defecto 890.")
            return 890.0

    def is_valid_image(self, url):
        if not url: return False
        url_lower = url.lower()
        for pattern in INVALID_PATTERNS:
            if pattern in url_lower:
                return False
        return True

    def harvest_images_and_pagination(self, category_name):
        print(f"📸 Iniciando recolección de imágenes para {category_name}...")
        page_count = 1
        max_pages = 20
        
        while page_count <= max_pages:
            print(f"   📄 Escaneando página {page_count}...")
            time.sleep(3) # Esperar carga de la grilla
            
            # Extraer productos de la grilla
            # Intentar encontrar los contenedores de productos
            items = self.driver.find_elements(By.CSS_SELECTOR, ".product-item, .product-list-item, div[data-sku]")
            
            for item in items:
                try:
                    sku = item.get_attribute("data-sku") or item.find_element(By.CSS_SELECTOR, ".sku, [class*='sku']").text.strip()
                    img_element = item.find_element(By.CSS_SELECTOR, "img")
                    img_url = img_element.get_attribute("src")
                    
                    if sku and self.is_valid_image(img_url):
                        self.image_map[sku] = img_url
                    elif not self.is_valid_image(img_url):
                        # print(f"      ⚠️ Imagen placeholder ignorada para SKU: {sku}")
                        pass
                except:
                    continue
            
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
            # Encontrar el botón de descarga CSV
            download_btn = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, "a.priceListButtom[href*='Csv']"))
            )
            self.driver.execute_script("arguments[0].click();", download_btn)
            
            # Esperar a que el archivo aparezca en descargas
            time.sleep(5)
            # El archivo suele llamarse como la categoría o similar
            return True
        except Exception as e:
            print(f"❌ Error al descargar CSV for {category_name}: {e}")
            return False

    def run(self):
        downloaded_files = []
        dollar_value = 890.0
        
        try:
            self.start_browser()
            self.login()
            dollar_value = self.get_dollar_value()
            
            for name, url in URLS.items():
                print(f"\n📂 Procesando Categoría: {name}")
                self.driver.get(url)
                self.harvest_images_and_pagination(name)
                if self.download_csv(name):
                    # Identificar el archivo más reciente en descargas
                    time.sleep(2)
                    files = glob.glob(os.path.join(self.download_dir, "*.csv"))
                    # Filtrar para no tomar el mapa_imagenes.json si existe
                    files = [f for f in files if not f.endswith("mapa_imagenes.json")]
                    if files:
                        latest_file = max(files, key=os.path.getctime)
                        # Renombrar para mayor claridad
                        new_path = os.path.join(self.download_dir, f"{name}.csv")
                        if os.path.exists(new_path): os.remove(new_path)
                        os.rename(latest_file, new_path)
                        downloaded_files.append(new_path)
                        print(f"✅ Archivo guardado: {new_path}")
            
            print(f"✅ Descarga completada. {len(downloaded_files)} archivos obtenidos.")
            
            # Guardar mapa de imágenes en JSON
            map_path = os.path.join(self.download_dir, "mapa_imagenes.json")
            with open(map_path, 'w', encoding='utf-8') as f:
                json.dump(self.image_map, f, indent=4)
            print(f"📊 Mapa de imágenes guardado en: {map_path}")
            
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
    # Para pruebas rápidas:
    # results = scraper.run()
    # print(results)
