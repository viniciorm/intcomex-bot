# scraper_intcomex.py

# Importar las librerías necesarias
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service as ChromeService
from bs4 import BeautifulSoup
import time
import csv
import getpass # Módulo para solicitar la contraseña de forma segura
from webdriver_manager.chrome import ChromeDriverManager

# --- Configuración ---
LOGIN_URL = "https://store.intcomex.com/Account/Login"
USERNAME = "paola.riveros@tupartnerti.cl" # El usuario ahora está fijo en el código

# Lista de URLs de categorías de productos
CATEGORY_URLS = [
    "https://store.intcomex.com/es-XCL/Products/ByCategory/mnt.tv?r=True",
    "https://store.intcomex.com/es-XCL/Products/ByCategory/mnt.monitor?r=True",
    "https://store.intcomex.com/es-XCL/Products/ByCategory/cpt.desktop?r=True",
    "https://store.intcomex.com/es-XCL/Products/ByCategory/cpt.notebook?r=True",
    "https://store.intcomex.com/es-XCL/Products/ByCategory/cpt.tablet?r=True",
    "https://store.intcomex.com/es-XCL/Products/ByCategory/prt.inkjet?r=True",
    "https://store.intcomex.com/es-XCL/Products/ByCategory/prt.label?r=True",
    "https://store.intcomex.com/es-XCL/Products/ByCategory/prt.laser?r=True",
    "https://store.intcomex.com/es-XCL/Products/ByCategory/prt.mfp?r=True",
    "https://store.intcomex.com/es-XCL/Products/ByCategory/prt.scanner?r=True",
    "https://store.intcomex.com/es-XCL/Products/ByCategory/cpt.allone?r=True"
]

# --- ¡¡¡AQUÍ NECESITAS TUS SELECTORES CSS/XPATH REALES!!! ---
# Estos son EJEMPLOS. Debes usar las herramientas de desarrollador (F12) en tu navegador
# para encontrar los selectores CSS o XPath correctos para Intcomex.

# Selectores para la página de LOGIN:
# Usa By.ID, By.NAME, By.XPATH, By.CSS_SELECTOR según lo que encuentres en el HTML
LOGIN_USERNAME_FIELD_SELECTOR = (By.ID, "UserName") # Ejemplo: el ID del campo de usuario
LOGIN_PASSWORD_FIELD_SELECTOR = (By.ID, "Password") # Ejemplo: el ID del campo de contraseña
LOGIN_BUTTON_SELECTOR = (By.ID, "LoginButton") # Ejemplo: el ID del botón de inicio de sesión

# Selectores para la página de PRODUCTOS (después de iniciar sesión y en una categoría):
PRODUCT_CONTAINER_SELECTOR = "div.product-item" # Selector CSS para un solo contenedor de producto
PRICE_SELECTOR = ".price-actual" # Selector CSS para el precio dentro del contenedor de producto
DESCRIPTION_SELECTOR = ".product-name" # Selector CSS para la descripción/nombre del producto
IMAGE_SELECTOR = ".product-image img" # Selector CSS para la etiqueta <img> de la imagen del producto
IMAGE_SRC_ATTRIBUTE = "src" # Atributo que contiene la URL de la imagen (generalmente 'src')

# --- Función para iniciar sesión con Selenium ---
def login_intcomex(driver, username, password):
    driver.get(LOGIN_URL)
    wait = WebDriverWait(driver, 20) # Aumentar tiempo de espera si la carga es lenta

    try:
        # Esperar y encontrar campos de usuario y contraseña
        username_field = wait.until(EC.presence_of_element_located(LOGIN_USERNAME_FIELD_SELECTOR))
        password_field = wait.until(EC.presence_of_element_located(LOGIN_PASSWORD_FIELD_SELECTOR))
        login_button = wait.until(EC.element_to_be_clickable(LOGIN_BUTTON_SELECTOR))

        username_field.send_keys(username)
        password_field.send_keys(password)
        login_button.click()

        # Esperar a que la URL cambie o que aparezca un elemento post-login
        # Ajusta "https://store.intcomex.com/es-XCL/Home" a la URL a la que te redirige después del login
        wait.until(EC.url_to_be("https://store.intcomex.com/es-XCL/Home"))
        print("Inicio de sesión exitoso.")
        return True
    except Exception as e:
        print(f"Error durante el inicio de sesión: {e}")
        driver.save_screenshot("login_error.png") # Guarda una captura de pantalla del error
        return False

# --- Función para extraer productos de una URL de categoría ---
def scrape_category_products(driver, category_url):
    print(f"Navegando a la categoría: {category_url}")
    driver.get(category_url)
    time.sleep(5) # Esperar a que la página cargue. Ajusta si es necesario.

    # --- Manejo de Paginación/Scroll Infinito (Si aplica) ---
    # Si la página carga productos al hacer scroll o tiene botones de "Cargar más",
    # aquí deberías implementar la lógica para desplazarte o hacer clic.
    # Ejemplo básico de scroll hasta el final para cargar más productos:
    # last_height = driver.execute_script("return document.body.scrollHeight")
    # while True:
    #     driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
    #     time.sleep(2) # Esperar a que carguen nuevos productos
    #     new_height = driver.execute_script("return document.body.scrollHeight")
    #     if new_height == last_height:
    #         break # No se cargaron más productos, llegamos al final
    #     last_height = new_height

    soup = BeautifulSoup(driver.page_source, 'html.parser')
    products_on_page = []

    # Encontrar todos los contenedores de producto
    product_divs = soup.select(PRODUCT_CONTAINER_SELECTOR)

    if not product_divs:
        print(f"Advertencia: No se encontraron productos con el selector '{PRODUCT_CONTAINER_SELECTOR}' en {category_url}. Revisa el selector o si la página cargó correctamente.")

    for product_div in product_divs:
        try:
            # Extraer precio
            price_element = product_div.select_one(PRICE_SELECTOR)
            price = price_element.get_text(strip=True) if price_element else "N/A"

            # Extraer descripción
            description_element = product_div.select_one(DESCRIPTION_SELECTOR)
            description = description_element.get_text(strip=True) if description_element else "N/A"

            # Extraer URL de la imagen
            image_element = product_div.select_one(IMAGE_SELECTOR)
            image_url = image_element[IMAGE_SRC_ATTRIBUTE] if image_element and IMAGE_SRC_ATTRIBUTE in image_element.attrs else "N/A"

            products_on_page.append({
                'category_url': category_url,
                'price': price,
                'description': description,
                'image_url': image_url
            })
        except Exception as e:
            # Captura errores individuales de extracción de producto sin detener el script
            print(f"Error al extraer un producto en {category_url}: {e}. Se saltará este producto.")
            continue # Continúa con el siguiente producto si uno falla

    return products_on_page

# --- Ejecución principal del script ---
if __name__ == "__main__":
    # Solicitar la contraseña de forma segura
    user_password = getpass.getpass("Por favor, ingresa tu contraseña de Intcomex: ")

    # Configurar el driver de Chrome (ChromeDriverManager lo descarga automáticamente)
    service = ChromeService(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service)
    driver.maximize_window() # Maximiza la ventana para una mejor visibilidad

    all_extracted_products = []

    try:
        # Intenta iniciar sesión con el usuario fijo y la contraseña ingresada
        if login_intcomex(driver, USERNAME, user_password):
            # Itera sobre cada URL de categoría y extrae los productos
            for category_url in CATEGORY_URLS:
                category_products = scrape_category_products(driver, category_url)
                all_extracted_products.extend(category_products)
                time.sleep(2) # Pequeña pausa entre categorías para evitar sobrecargar el servidor

            # Si se extrajeron productos, guárdalos en un archivo CSV
            if all_extracted_products:
                print(f"\nSe extrajeron {len(all_extracted_products)} productos en total.")
                with open('productos_intcomex.csv', 'w', newline='', encoding='utf-8') as csvfile:
                    fieldnames = ['category_url', 'price', 'description', 'image_url']
                    writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

                    writer.writeheader()
                    for product in all_extracted_products:
                        writer.writerow(product)
                print("Datos guardados exitosamente en 'productos_intcomex.csv'")
            else:
                print("No se extrajeron productos. Por favor, revisa los selectores CSS/XPath y el proceso de login.")
        else:
            print("El inicio de sesión falló. El script no puede extraer productos.")

    except Exception as e:
        print(f"Ocurrió un error general durante la ejecución: {e}")
    finally:
        driver.quit() # Siempre cierra el navegador al finalizar, ¡muy importante!