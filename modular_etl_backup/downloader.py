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
    # "Notebooks": "https://store.intcomex.com/es-XCL/Products/ByCategory/cpt.notebook?r=True",
    # "Monitores": "https://store.intcomex.com/es-XCL/Products/ByCategory/mnt.monitor?r=True",
    # "Desktop": "https://store.intcomex.com/es-XCL/Products/ByCategory/cpt.desktop?r=True",
    "Tablets": "https://store.intcomex.com/es-XCL/Products/ByCategory/cpt.tablet?r=True",
    # "All_in_One": "https://store.intcomex.com/es-XCL/Products/ByCategory/cpt.allone?r=True"
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
        print("Starting browser...")
        self.driver = Chrome(service=Service(ChromeDriverManager().install()), options=self.options)
        self.driver.maximize_window()

    def login(self):
        print(f"Navigating to login: {LOGIN_URL}")
        self.driver.get(LOGIN_URL)
        print("Please perform manual login in the Chrome window.")
        print("Waiting for login success...")
        
        wait = WebDriverWait(self.driver, 300) # 5 minutos para login manual
        wait.until(lambda d: "Login" not in d.current_url and "login" not in d.current_url.lower())
        print("Login detected successfully.")

    def get_dollar_value(self):
        print("Extracting dollar value...")
        try:
            element = WebDriverWait(self.driver, 15).until(
                EC.presence_of_element_located((By.XPATH, "//*[contains(text(), 'US$1 =')]"))
            )
            text = element.text
            print(f"      Text found: '{text}'")
            nums = re.findall(r'[\d.,]+', text.split('=')[-1])
            if nums:
                valor = float(nums[0].replace('.', '').replace(',', '.'))
                print(f"Dollar value found: ${valor}")
                return valor
            return 810.0
        except Exception as e:
            print(f"Could not get dollar automatically: {e}. Using default 810.")
            return 810.0

    def is_valid_image(self, url):
        if not url: return False
        url_lower = url.lower()
        for pattern in INVALID_PATTERNS:
            if pattern in url_lower:
                return False
        return True

    def harvest_images_and_pagination(self, category_name):
        print(f"Starting intelligent harvest for {category_name}...")
        page_count = 1
        max_pages = 20
        today = str(date.today())
        
        while page_count <= max_pages:
            print(f"   Scanning page {page_count}...")
            time.sleep(7) # More wait for grid load
            
            items = self.driver.find_elements(By.CSS_SELECTOR, ".product-list-item, .item-box, div.product-item, .product-container")
            
            total_items = len(items)
            print(f"      Cards found: {total_items}")
            
            if total_items == 0:
                print("      No products found. Retrying with longer wait...")
                time.sleep(10)
                items = self.driver.find_elements(By.CSS_SELECTOR, ".product-list-item, .item-box, div.product-item, .product-container")
                total_items = len(items)

            known_with_image = 0
            
            for item in items:
                try:
                    sku = None
                    # Try getting SKU from data attribute first
                    sku = item.get_attribute("data-sku")
                    
                    if not sku:
                        try:
                            # Try finding element containing "SKU:" and cleaning it
                            sku_elements = item.find_elements(By.XPATH, ".//*[contains(text(), 'SKU:')]")
                            if sku_elements:
                                sku_text = sku_elements[0].text
                                sku = sku_text.split("SKU:")[-1].strip()
                        except:
                            pass
                    
                    if not sku:
                        try:
                            sku = item.find_element(By.CSS_SELECTOR, ".sku, [class*='sku']").text.strip()
                        except:
                            continue
                    
                    if not sku: continue
                    
                    # Check state
                    if sku in self.product_state and self.product_state[sku].get("tiene_imagen"):
                        cached_url = self.product_state[sku].get("url")
                        if cached_url:
                            known_with_image += 1
                            self.product_state[sku]["ultima_vista"] = today
                            self.image_map[sku] = cached_url
                            continue
                    
                    # Identify Image
                    img_url = None
                    try:
                        img_element = item.find_element(By.CSS_SELECTOR, "img")
                        img_url = img_element.get_attribute("data-src") or \
                                  img_element.get_attribute("data-original") or \
                                  img_element.get_attribute("src")
                    except:
                        continue
                    
                    if not img_url: continue
                    
                    valid = self.is_valid_image(img_url)
                    
                    self.product_state[sku] = {
                        "tiene_imagen": valid,
                        "url": img_url if valid else None,
                        "ultima_vista": today
                    }
                    
                    if valid:
                        self.image_map[sku] = img_url
                        # print(f"      Product {sku}: Image detected.")
                        
                except Exception as e:
                    continue
            
            print(f"      Finished: {total_items} items (Known: {known_with_image})")
            
            # Simple skip if all known
            if total_items > 0 and known_with_image == total_items:
                 print("      Fast skip to next page...")

            # Next page
            try:
                next_btn = self.driver.find_element(By.CSS_SELECTOR, "a.next, .pagination-next, a[title*='Siguiente'], a[title*='Next']")
                if "disabled" in next_btn.get_attribute("class") or not next_btn.is_displayed():
                    break
                
                self.driver.execute_script("arguments[0].scrollIntoView();", next_btn)
                time.sleep(1)
                self.driver.execute_script("arguments[0].click();", next_btn)
                page_count += 1
            except:
                break

    def download_csv(self, category_name):
        print(f"Downloading CSV for {category_name}...")
        try:
            btn = WebDriverWait(self.driver, 15).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, "a.priceListButtom[href*='Csv']"))
            )
            self.driver.execute_script("arguments[0].click();", btn)
            time.sleep(10) # More time for download
            return True
        except:
            return False

    def run(self):
        downloaded_files = []
        dollar_value = 810.0
        
        try:
            self.start_browser()
            self.login()
            dollar_value = self.get_dollar_value()
            
            for name, url in URLS.items():
                print(f"\nProcessing Category: {name}")
                self.driver.get(url)
                self.harvest_images_and_pagination(name)
                if self.download_csv(name):
                    time.sleep(5)
                    files = glob.glob(os.path.join(self.download_dir, "*.csv"))
                    files = [f for f in files if not f.endswith("mapa_imagenes.json")]
                    if files:
                        latest = max(files, key=os.path.getctime)
                        path = os.path.join(self.download_dir, f"{name}.csv")
                        if os.path.exists(path): os.remove(path)
                        os.rename(latest, path)
                        downloaded_files.append(path)
                        print(f"File saved: {path}")
            
            print(f"Extraction finished. {len(downloaded_files)} CSVs obtained.")
            
            # Save maps
            map_path = os.path.join(self.download_dir, "mapa_imagenes.json")
            with open(map_path, 'w', encoding='utf-8') as f:
                json.dump(self.image_map, f, indent=4)
            
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
