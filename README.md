# 🤖 Bot de Sincronización Intcomex -> WooCommerce `v2.2.0`


Bot de producción diseñado para sincronizar productos desde el catálogo de Intcomex Chile directamente a una tienda WooCommerce mediante API.

> [!IMPORTANT]
> **Política de Documentación**: Para mantener la integridad del proyecto, todo cambio funcional en el código DEBE ser reflejado inmediatamente en este `README.md`.

## 📋 Flujo de Operación Actual

El bot utiliza un flujo integrado en `sync_bot.py` enfocado en la resiliencia:

1.  **Fase de Acceso**:
    *   Inicia un navegador Chrome (soporta modo **Headless** para servidores).
    *   **Login Automatizado**: El bot se autentica automáticamente mediante Selenium (sin PyAutoGUI), permitiendo ejecuciones programadas 24/7 en la nube o Docker.
2.  **Fase de Extracción**:

    *   **Dólar en Tiempo Real**: Extrae automáticamente el tipo de cambio actual directamente desde el encabezado del sitio de Intcomex.
    *   **Descarga Resiliente**: Descarga los archivos CSV por categorías. Si una descarga falla, el bot realiza un segundo intento automático tras completar la primera ronda.
3.  **Fase de Carga (WooCommerce)**:
    *   Una vez terminadas las descargas, el navegador se cierra automáticamente para liberar recursos.
    *   Procesa los CSVs y actualiza/crea productos en WooCommerce vía API.
    *   **Retry Logic**: Reintentos automáticos con espera exponencial ante fallos de la API.
4.  **Fase de Limpieza (Cleaner)**:
    *   **Gestión de Inventario**: Si el stock es <= 2, el producto pasa a borrador (`draft`) automáticamente.
    *   **Historial Inteligente**: Mantiene registro de por qué un producto fue ocultado (stock vs fuera de catálogo).
5.  **Fase de IA (Enriquecimiento v2 - Lite)**:
    *   **Control Local**: `ia_webhook_trigger.py` orquestra el proceso secuencial (uno a uno).
    *   **Estado Local**: Mantiene el registro de productos mejorados en `estado_productos.json` (`ia_mejorado: true`).
    *   **Transformer Stateless**: n8n actúa únicamente como puente hacia OpenAI, sin tocar WooCommerce.
    *   **Actualización Directa**: Python actualiza la descripción en WooCommerce mediante la API (reducir 503s).
    *   **Audit Logic**: Herramientas para verificar el contenido real en WooCommerce y sincronizar el estado local.

## 🖼️ Bot de Imágenes (Independiente)

Para la descarga física de imágenes, el proyecto incluye `image_bot.py`:
1.  **Lectura**: Escanea los SKUs de los CSVs descargados.
2.  **Búsqueda**: Navega de forma pública en Intcomex buscando cada SKU.
3.  **Descarga**: Baja las imágenes físicamente a la carpeta `product_images/`.
4.  **Formato**: Nombra los archivos como `SKU_001.jpg`, `SKU_002.jpg`, etc.
5.  **Registro**: Actualiza `estado_productos.json` con las rutas locales y el estado de descarga.

## 🧠 Bot de Inteligencia Artificial (IA) v2 (Lite)

Rediseñado para máxima estabilidad y control de estado fuera de WooCommerce:
1.  **Activación**: Requiere n8n (Docker) con `n8n/flujo_ia_lite.json` activo (Published).
2.  **Lógica Secuencial**: Procesa productos uno por uno con pausas de seguridad (3s).
3.  **Estado Robusto**: Si el proceso se interrumpe, sabe exactamente dónde quedó leyendo `estado_productos.json`.
4.  **Auditoría**: `audit_ia_content.py` verifica el HTML real en la tienda para evitar duplicidad de costos.

## 🚀 Configuración Inicial

### 1. Instalar Dependencias
```bash
pip install -r requirements.txt
```

### 2. Configurar Credenciales
1. Copia el archivo de ejemplo:
   ```bash
   cp credentials.example.py credentials.py
   ```
2. Edita `credentials.py` y completa con tus datos reales.

### 3. Gestión de Categorías
Las categorías y sus URLs ya no están en el código. Se gestionan desde:
*   `config/categories.json`: Edita este archivo para sumar o quitar categorías y configurar palabras clave de validación.


## 📖 Uso

### 1. Ejecución Consolidada (Orquestador)
El orquestador maneja el flujo completo (Sync -> Imágenes -> Carga) de forma automática y envía un reporte consolidado.

```bash
# Ejecutar todo el flujo (Sincronización + Imágenes + Carga + Limpieza + IA)
python main_orchestrator.py all

# Ejecutar fases específicas
python main_orchestrator.py sync
python main_orchestrator.py images
```

### 4. Despliegue con Docker (Recomendado para Servidores)
El proyecto incluye soporte nativo para Docker y Docker Compose:

```bash
# Iniciar todo el stack (Bot + n8n)
docker-compose up -d

# Ver logs del bot
docker-compose logs -f bot
```

*   **Variables de Entorno**: Puedes controlar el modo headless mediante `HEADLESS=true` o `false` en el archivo `docker-compose.yml`.


### 2. Ejecución de Componentes Individuales
Si prefieres un control granular o depuración específica, puedes usar los bots por separado:

| Script | Función | Comando |
| :--- | :--- | :--- |
| `sync_bot.py` | Sincronización principal de CSV y WooCommerce | `python sync_bot.py` |
| `image_bot.py` | Descarga de imágenes por SKU desde el portal | `python image_bot.py` |
| `image_uploader.py` | Sube y vincula imágenes locales a WooCommerce | `python image_uploader.py` |
| `inventory_cleaner.py`| Gestión de stock seguro y fuera de catálogo | `python inventory_cleaner.py` |
| `ia_webhook_trigger.py`| Orquestador de IA secuencial (Actualiza Woo) | `python ia_webhook_trigger.py` |
| `audit_ia_content.py` | Audita descripciones HTML reales en Woo | `python audit_ia_content.py` |
| `migrate_ia_state.py` | Sincroniza metadatos de IA a estado local | `python migrate_ia_state.py` |

### 3. Herramientas de Utilidad
- `ver_csv.py`: Inspecciona la estructura de los CSV descargados.
- `debug_wp_auth.py`: Prueba la conexión con la API de WooCommerce.
- `force_reset_images.py`: Reinicia el estado de las imágenes para re-procesar todo.

## 📁 Estructura del Proyecto
```
├── config/               # Configuración de categorías (JSON)
├── main_orchestrator.py  # Orquestador central (Recomendado)
├── sync_bot.py           # Script principal de sincronización base
├── image_bot.py          # Bot de descarga de imágenes
├── inventory_cleaner.py  # Bot de gestión de stock y limpieza
├── ia_webhook_trigger.py # Trigger de lotes para n8n
├── credentials.py        # Credenciales (Ignorado por Git)
├── Dockerfile            # Configuración de imagen Docker
├── docker-compose.yml    # Orquestación de servicios (Bot + n8n)
├── n8n/                  # Flujos de n8n (JSON)
├── downloads/            # Almacenamiento temporal de CSVs
├── product_images/       # Repositorio local de imágenes descargadas
└── requirements.txt      # Dependencias
```


## ⚙️ Parámetros de Negocio
Configurables dentro de `sync_bot.py`:
- `MARGIN_PERCENTAGE`: Margen de ganancia aplicado (por defecto 20% / 0.20).
- `URLS`: Diccionario de categorías y URLs a sincronizar.

## 🔒 Seguridad y Robustez
- **Cierre Limpio**: El navegador se cierra siempre después de las descargas, incluso si hay errores.
- **Validación de Precios**: Manejo avanzado de formatos numéricos CLP (puntos de miles y comas decimales).
- **Control de Stock**: Se mapea el stock real y estados especiales (ej: "Más de 20").

## 🌐 Requisitos del Servidor (WordPress/PHP)

Para asegurar que la API de WooCommerce responda correctamente a las peticiones del bot, el servidor de WordPress **DEBE** tener al menos la siguiente configuración en PHP:

| Parámetro | Valor Recomendado | Motivo |
| :--- | :--- | :--- |
| `memory_limit` | **512M** | Evita errores 500 por falta de memoria al procesar productos. |
| `max_execution_time` | **300** | Permite que las subidas de imágenes no se corten por tiempo. |
| `upload_max_filesize` | **64M** | Permite subir fotos de productos en alta resolución. |
| `post_max_size` | **64M** | Debe ser igual o mayor a `upload_max_filesize`. |
| `max_input_time` | **300** | Tiempo adicional para procesar datos de entrada de la API. |

> [!TIP]
> Si persisten los errores 500, verifica el archivo `wp-config.php` y asegúrate de que `define('WP_MEMORY_LIMIT', '512M');` esté presente.

## 📄 Licencia
Este proyecto es privado y confidencial.

