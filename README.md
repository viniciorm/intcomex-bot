# 🤖 Bot de Sincronización Intcomex -> WooCommerce `v3.2.0 - VINI TURBO` 🚀

Bot de producción de alto rendimiento diseñado para sincronizar miles de productos desde Intcomex Chile a WooCommerce en tiempo récord mediante arquitectura paralela, multithreading y operaciones en lote.

> [!IMPORTANT]
> **Arquitectura ViniBot Turbo**: Esta versión ha sido rediseñada para eliminar cuellos de botella secuenciales. El bot utiliza **Multi-threading** y **Batch API Operations**, reduciendo el tiempo de ejecución de 5+ horas a menos de 45 minutos.

---

## 🛠️ Stack Tecnológico
* **Lenguaje**: Python 3.11+
* **Automatización Web**: Selenium (Chrome Headless)
* **Motor de Orquestación**: n8n (Dockerized)
* **Inteligencia Artificial**: OpenAI API (GPT-4o)
* **Servidor Web**: Nginx (para el Dashboard de KPIs)
* **Infraestructura**: Docker & Docker Compose
* **Puertos Utilizados**: 
  * `5678`: Interfaz y Webhooks de n8n.
  * `8000`: Dashboard web interactivo de ROI y velocidad.

---

## 📋 Flujo de Operación
1. **Fase A (Sincronización)**: Selenium para login automatizado y descarga de CSVs en Intcomex. *(Compatible con interceptación interactiva de código 2FA SMS vía Telegram)*.
2. **Fase B (Imágenes)**: `image_bot.py` descarga imágenes de productos en paralelo.
3. **Fase C (Uploader)**: `image_uploader.py` sube los binarios a WordPress y vincula los productos en lotes.
4. **Fase D (Limpieza)**: `inventory_cleaner.py` oculta o re-activa productos basándose en el stock en lotes de 100.
5. **Fase E (IA n8n)**: `ia_webhook_trigger.py` envía webhooks concurrentes a n8n para enriquecer títulos y descripciones vía OpenAI.

---

## ⚙️ Alternativas de Instalación

El ecosistema de ViniBot puede ejecutarse bajo dos caminos de instalación bien definidos según el entorno:

### 💻 CAMINO A: Ejecución Local en Entorno de Desarrollo (Windows o Linux)

Este camino está diseñado para pruebas rápidas de código y depuración en tu máquina local.

#### Requisitos Previos:
* Python 3.11+ instalado.
* Google Chrome y ChromeDriver compatible instalado en el sistema operativo del host.

#### Configuración:
1. Instala las dependencias locales:
   ```bash
   pip install -r requirements.txt
   ```
2. Duplica el archivo de ejemplo: `cp credentials.example.py credentials.py` y completa tus datos.
3. En `credentials.py`, asegúrate de que el bot apunte localmente a la instancia de n8n:
   * **`N8N_HOST = "localhost"`** (dentro de tus archivos de configuración).
4. El Dashboard se puede visualizar levantando un servidor local en la raíz:
   ```bash
   python -m http.server 8000
   ```

#### Ejecución:
Para correr el flujo completo de forma secuencial tradicional:
```bash
python main_orchestrator.py all
```
*(O puedes ejecutar partes específicas, ej: `python main_orchestrator.py sync` o `python main_orchestrator.py local` para usar CSVs ya descargados sin loguearte de nuevo).*

---

### ☁️ CAMINO B: Despliegue en Producción Avanzado (VPS con Ubuntu mediante Docker)

Diseñado para ejecuciones automatizadas 24/7 en servidores remotos sin interfaz gráfica, aislando completamente las dependencias y asegurando la persistencia de datos.

#### Requisitos Previos:
* Servidor VPS (ej. Ubuntu con 8GB RAM recomendado).
* Docker y Docker Compose instalados.

#### Arquitectura de Datos y Persistencia:
Para que las métricas de ROI y el catálogo histórico de sincronización no se borren cada vez que se recrea el contenedor, el sistema utiliza **volúmenes locales montados en el disco del VPS**:
* `./data_activa:/app/data_activa`: Base de datos local en JSON (`estado_productos.json`, ROI histórico).
* `./product_images:/app/product_images`: Caché local de imágenes descargadas.
* `./downloads:/app/downloads`: Archivos CSV temporales obtenidos de Intcomex.

#### Comunicación Nativa Inteligente (DNS de Docker):
Para evitar hardcodear IPs públicas o abrir puertos inseguros, la lógica de comunicación en Python (`ia_webhook_trigger.py`) y el chequeo de salud (`system_health.py`) resuelven la ruta de n8n de forma interna usando la red compartida de Docker Compose:
* **Webhook de IA**: Se envía directo a la URL **`http://n8n-automation:5678/webhook/ia-transformer`** gracias a que el contenedor de n8n tiene el alias `n8n-automation` dentro de la red `vinibot_network`.
* **Configuración en n8n**: En la interfaz de n8n, solo se requiere configurar el Path manual en el nodo Webhook como **`ia-transformer`**.

#### Despliegue y Encendido:
1. Clona el proyecto y crea tu archivo `credentials.py` en la raíz del VPS.
2. Inicia todo el ecosistema (Agente, n8n, Dashboard seguro en Nginx) en segundo plano:
   ```bash
   docker compose up -d --build
   ```
3. Verifica el estado de los contenedores:
   ```bash
   docker compose ps
   ```

---

## 🔄 Despliegue Automático (CI/CD)

El repositorio incluye un pipeline de GitHub Actions configurado en [`.github/workflows/deploy.yml`](file:///.github/workflows/deploy.yml). Cada vez que haces un `git push` a la rama `main`, el pipeline se conecta de forma segura a tu VPS vía SSH, actualiza el código y recrea el agente del bot sin que tengas que intervenir manualmente.

### Pasos para Activar el Despliegue Continuo en GitHub:
1. Entra a la página web de tu repositorio en GitHub.
2. Ve a **Settings** -> **Secrets and variables** -> **Actions**.
3. Haz clic en **New repository secret** y registra de forma segura los siguientes 4 secretos:
   * **`VPS_HOST`**: La dirección IP pública de tu servidor VPS.
   * **`VPS_USER`**: El usuario del VPS (normalmente `root`).
   * **`VPS_SSH_KEY`**: El contenido completo de tu llave SSH privada de acceso al servidor (el contenido de tu archivo `.pem` o `id_rsa`).
   * **`VPS_PORT`**: El puerto de conexión SSH de tu servidor (típicamente `22`).

---

## 🔒 Seguridad y Git

El archivo [`.gitignore`](file:///.gitignore) está configurado para evitar cualquier fuga de información sensible. Están estrictamente bloqueados de subirse a GitHub:
* El archivo de credenciales activas `credentials.py` (solo se expone la plantilla inofensiva `credentials.example.py`).
* El contenido dinámico de la carpeta `data_activa/` (previniendo subir historiales, estados e información del cliente).
* Las imágenes de productos en `product_images/` y logs temporales `*.log`.
