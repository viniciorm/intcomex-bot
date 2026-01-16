# 🤖 Bot de Sincronización Intcomex -> WooCommerce (Arquitectura ETL)

Bot avanzado que sincroniza productos desde Intcomex directamente a tu tienda WooCommerce mediante API, utilizando una arquitectura modular de Extracción, Transformación y Carga (ETL).

## 📋 Características Principales

- **Arquitectura ETL Modular**: Separación de responsabilidades para mayor robustez y mantenimiento.
- **Extracción Inteligente (Extractor)**:
  - ✅ Login automático/manual en Intcomex con Selenium.
  - ✅ **Paginación automática**: Recorre todas las páginas del catálogo para asegurar la captura de imágenes.
  - ✅ **Filtrado de Imágenes**: Ignora automáticamente placeholders y fotos genéricas ("Sin imagen").
- **Carga Robusta (Loader)**:
  - ✅ **Retry Logic**: Reintentos automáticos con espera exponencial ante fallos de red o Timeouts de la API.
  - ✅ **Rate Limiting**: Pausas de 2 segundos entre productos para estabilidad del servidor WooCommerce.
  - ✅ **Parseo Mejorado**: Manejo de stock especial (ej: "Más de 20") y conversión precisa de precios CLP.
- **Orquestación Central**: Un único punto de control para todo el flujo.

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

2. Edita `credentials.py` y completa con tus datos reales de Intcomex y WooCommerce.

## 📖 Uso

### Ejecutar el Bot (Modo ETL)

El nuevo motor de sincronización se ejecuta desde el orquestador:

```bash
python orchestrator.py
```

El flujo seguirá estos pasos:
1. **Fase 1 (Extraction)**: Abrirá Chrome, solicitará login manual, recolectará imágenes (paginando) y descargará los CSVs.
2. **Fase 2 (Load)**: Procesará los archivos descargados y sincronizará con WooCommerce usando el mapa de imágenes recolectado.

### Ejecutar Pruebas Automatizadas

```bash
pytest test_sync_bot.py -v
```

## 📁 Estructura del Proyecto

```
Intcomex_Project/
├── orchestrator.py      # Punto de entrada principal (Orquestador)
├── downloader.py        # Clase IntcomexScraper (Fase de Extracción)
├── uploader.py          # Clase WooSync (Fase de Carga/Sincronización)
├── credentials.py       # Credenciales privadas (Ignorado por Git)
├── downloads/           # Carpeta donde se guardan los CSVs temporales
├── requirements.txt     # Dependencias del proyecto
└── README.md            # Este archivo
```

## ⚙️ Configuración de Filtros

Puedes ajustar el comportamiento en `sync_bot.py` (o en los nuevos módulos):
- `MIN_STOCK`: Stock mínimo para sincronizar (por defecto 0 para subir todo).
- `MARGIN_PERCENTAGE`: Margen de ganancia (por defecto 20% / 0.20).

## 🔒 Seguridad y Robustez

- **Timeouts**: La API ahora tiene un tiempo de espera de 60 segundos.
- **Reintentos**: Si la conexión falla, el bot reintenta hasta 3 veces automáticamente.
- **Git**: Archivos sensibles y temporales están protegidos vía `.gitignore`.

## 📝 Notas de Sincronización

- Si un producto ya existe bajo el mismo SKU, el bot solo **actualiza su precio y stock**.
- Si el producto es nuevo, lo **crea** con imagen (si fue encontrada), nombre y SKU.
- Se aplica automáticamente el tag de "Envío Gratuito".

## 📄 Licencia

Este proyecto es privado y confidencial.
