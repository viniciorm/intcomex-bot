# 🤖 Bot de Sincronización Intcomex -> WooCommerce `v2.1.0`

Bot de producción diseñado para sincronizar productos desde el catálogo de Intcomex Chile directamente a una tienda WooCommerce mediante API.

> [!IMPORTANT]
> **Política de Documentación**: Para mantener la integridad del proyecto, todo cambio funcional en el código DEBE ser reflejado inmediatamente en este `README.md`.

## 📋 Flujo de Operación Actual

El bot utiliza un flujo integrado en `sync_bot.py` enfocado en la resiliencia:

1.  **Fase de Acceso**:
    *   Inicia un navegador Chrome controlado.
    *   **Login Manual**: El bot espera hasta que el usuario se autentique manualmente en el portal de Intcomex para máxima seguridad y manejo de CAPTCHAs.
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
5.  **Fase de IA (Enriquecimiento Webhook)**:
    *   **Trigger Local**: `ia_webhook_trigger.py` envía lotes de 50 SKUs a n8n.
    *   **Enriquecimiento**: n8n usa `gpt-4o-mini` para generar descripciones HTML y actualiza Woo.
    *   **Reporte Final**: Envía un correo consolidado con todas las fases (incluyendo IA).

## 🖼️ Bot de Imágenes (Independiente)

Para la descarga física de imágenes, el proyecto incluye `image_bot.py`:
1.  **Lectura**: Escanea los SKUs de los CSVs descargados.
2.  **Búsqueda**: Navega de forma pública en Intcomex buscando cada SKU.
3.  **Descarga**: Baja las imágenes físicamente a la carpeta `product_images/`.
4.  **Formato**: Nombra los archivos como `SKU_001.jpg`, `SKU_002.jpg`, etc.
5.  **Registro**: Actualiza `estado_productos.json` con las rutas locales y el estado de descarga.

## 🧠 Bot de Inteligencia Artificial (IA)

Diseñado para enriquecer descripciones existentes:
1.  **Activación**: Requiere que n8n esté corriendo (Docker) con el flujo `flujo_productos_ia_webhook.json` activo.
2.  **Lógica**: Procesa solo productos con `subido_a_woo: true` en `estado_productos.json`.
3.  **Seguridad**: Incluye reintentos automáticos y pausas de 2s para evitar bloqueos de API.

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
2. Edita `credentials.py` y completa con tus datos reales de Intcomex, WooCommerce y el servidor SMTP para los reportes.

## 📖 Uso

### 1. Ejecución Consolidada (Orquestador)
El orquestador maneja el flujo completo (Sync -> Imágenes -> Carga) de forma automática y envía un reporte consolidado.

```bash
# Ejecutar todo el flujo (Sincronización + Imágenes + Carga + Limpieza + IA)
python main_orchestrator.py all

# Ejecutar solo fases específicas
python main_orchestrator.py sync    # Solo descarga CSV y actualiza precios/stock
python main_orchestrator.py images  # Solo busca y descarga imágenes faltantes
python main_orchestrator.py upload  # Solo sube imágenes nuevas a WooCommerce
python main_orchestrator.py clean   # Solo ejecuta la limpieza de inventario inteligente
python main_orchestrator.py ia      # Ejecuta el trigger del webhook de IA
```

### 2. Ejecución de Componentes Individuales
Si prefieres un control granular o depuración específica, puedes usar los bots por separado:

| Script | Función | Comando |
| :--- | :--- | :--- |
| `sync_bot.py` | Sincronización principal de CSV y WooCommerce | `python sync_bot.py` |
| `image_bot.py` | Descarga de imágenes por SKU desde el portal | `python image_bot.py` |
| `image_uploader.py` | Sube y vincula imágenes locales a WooCommerce | `python image_uploader.py` |
| `inventory_cleaner.py`| Gestión de stock seguro y fuera de catálogo | `python inventory_cleaner.py` |
| `ia_webhook_trigger.py`| Gatilla el flujo de IA en n8n por lotes | `python ia_webhook_trigger.py` |
| `scraper_intcomex.py`| Extracción de prueba (Scraper simplificado) | `python scraper_intcomex.py` |

### 3. Herramientas de Utilidad
- `ver_csv.py`: Inspecciona la estructura de los CSV descargados.
- `debug_wp_auth.py`: Prueba la conexión con la API de WooCommerce.
- `force_reset_images.py`: Reinicia el estado de las imágenes para re-procesar todo.

## 📁 Estructura del Proyecto
```
intcomex-bot/
├── main_orchestrator.py  # Orquestador central (Recomendado)
├── sync_bot.py           # Script principal de sincronización base
├── image_bot.py          # Bot de descarga de imágenes
├── inventory_cleaner.py  # Bot de gestión de stock y limpieza
├── ia_webhook_trigger.py # Trigger de lotes para n8n
├── credentials.py        # Credenciales (Ignorado por Git)
├── n8n/                  # Flujos de n8n (JSON)
├── downloads/            # Almacenamiento temporal de CSVs
├── product_images/       # Repositorio local de imágenes descargadas
├── modular_etl_backup/   # Versiones previas de la arquitectura ETL
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

## 📄 Licencia
Este proyecto es privado y confidencial.
