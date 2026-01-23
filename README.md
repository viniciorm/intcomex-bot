# 🤖 Bot de Sincronización Intcomex -> WooCommerce

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
4.  **Fase de Reporte**:
    *   Envía un correo electrónico detallado con el resumen de la sincronización (productos actualizados, creados, errores y categorías procesadas).

## 🖼️ Bot de Imágenes (Independiente)

Para la descarga física de imágenes, el proyecto incluye `image_bot.py`:
1.  **Lectura**: Escanea los SKUs de los CSVs descargados.
2.  **Búsqueda**: Navega de forma pública en Intcomex buscando cada SKU.
3.  **Descarga**: Baja las imágenes físicamente a la carpeta `product_images/`.
4.  **Formato**: Nombra los archivos como `SKU_001.jpg`, `SKU_002.jpg`, etc.
5.  **Registro**: Actualiza `estado_productos.json` con las rutas locales y el estado de descarga.

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

### Ejecutar la Sincronización Completa
```bash
python sync_bot.py
```

### Otras herramientas
- `image_bot.py`: Bot dedicado a la descarga física de imágenes por SKU.
- `scraper_intcomex.py`: Versión simplificada para pruebas de extracción.
- `ver_csv.py`: Utilidad para inspeccionar la estructura de los CSV descargados.

## 📁 Estructura del Proyecto
```
intcomex-bot/
├── sync_bot.py           # Script principal de producción
├── image_bot.py          # Bot de descarga de imágenes
├── credentials.py        # Credenciales (Ignorado por Git)
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
