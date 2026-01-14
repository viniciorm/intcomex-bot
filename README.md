# 🤖 Bot de Sincronización Intcomex -> WooCommerce

Bot automatizado que sincroniza productos desde Intcomex directamente a tu tienda WooCommerce mediante API.

## 📋 Características

- ✅ Login automático en Intcomex con Selenium
- ✅ Extracción de productos de múltiples categorías
- ✅ Filtrado inteligente (stock > 50, precio > $150.000 CLP)
- ✅ Cálculo automático de precio de venta con margen del 20%
- ✅ Sincronización directa con WooCommerce (crear/actualizar productos)
- ✅ Manejo robusto de errores
- ✅ Suite completa de pruebas TDD

## 🚀 Configuración Inicial

### 1. Instalar Dependencias

```bash
pip install -r requirements.txt
```

### 2. Configurar Credenciales

**IMPORTANTE:** Las credenciales NO deben subirse a GitHub por seguridad.

1. Copia el archivo de ejemplo:
   ```bash
   cp credentials.example.py credentials.py
   ```

2. Edita `credentials.py` y completa con tus credenciales reales:
   ```python
   # Intcomex
   INTCOMEX_USERNAME = "tu_usuario@ejemplo.com"
   INTCOMEX_PASSWORD = "tu_contraseña"
   
   # WooCommerce
   WC_URL = "https://tu-tienda.com"
   WC_CONSUMER_KEY = "ck_tu_consumer_key"
   WC_CONSUMER_SECRET = "cs_tu_consumer_secret"
   ```

3. El archivo `credentials.py` está en `.gitignore` y NO se subirá a GitHub.

### 3. Obtener Credenciales de WooCommerce

1. Ve a tu panel de WordPress: `WooCommerce > Configuración > Avanzado > REST API`
2. Crea una nueva clave API
3. Copia el Consumer Key y Consumer Secret a `credentials.py`

## 📖 Uso

### Ejecutar el Bot

```bash
python sync_bot.py
```

El bot:
1. Iniciará sesión en Intcomex
2. Recorrerá todas las categorías configuradas
3. Filtrará productos según los criterios (stock > 50, precio > $150.000)
4. Sincronizará productos con WooCommerce (crear nuevos o actualizar existentes)

### Ejecutar Pruebas

```bash
# Todas las pruebas automatizadas
pytest test_sync_bot.py -v

# Prueba rápida (sin APIs)
python test_quick.py
```

## 📁 Estructura del Proyecto

```
Intcomex_Project/
├── sync_bot.py              # Script principal del bot
├── credentials.py           # Credenciales (NO subir a GitHub)
├── credentials.example.py   # Plantilla de credenciales
├── test_sync_bot.py         # Suite de pruebas TDD
├── test_quick.py            # Pruebas rápidas
├── requirements.txt         # Dependencias Python
├── .gitignore              # Archivos ignorados por Git
└── README.md              # Este archivo
```

## 🔒 Seguridad

- ✅ `credentials.py` está en `.gitignore`
- ✅ Nunca subas credenciales a GitHub
- ✅ Usa `credentials.example.py` como referencia
- ✅ Mantén tus credenciales seguras y privadas

## 🧪 Pruebas

El proyecto incluye una suite completa de pruebas TDD con **40 pruebas automatizadas**:

- Conversión de precios CLP
- Cálculo de precio de venta
- Extracción de stock
- Filtrado de productos
- Integración con WooCommerce API
- Flujos de integración completos

Ver `README_TESTS.md` para más detalles sobre las pruebas.

## ⚙️ Configuración Avanzada

### Ajustar Filtros

Edita las constantes en `sync_bot.py`:

```python
MIN_STOCK = 50              # Stock mínimo requerido
MIN_PRICE_COST = 150000      # Precio mínimo en CLP
MARGIN_PERCENTAGE = 0.20     # Margen de ganancia (20%)
```

### Ajustar Selectores CSS

Si Intcomex cambia su estructura HTML, actualiza los selectores en `sync_bot.py`:

```python
PRODUCT_CONTAINER_SELECTOR = "div.product-item"
PRICE_SELECTOR = ".price-actual"
STOCK_SELECTOR = ".stock-quantity"
SKU_SELECTOR = ".product-sku"
```

## 🐛 Solución de Problemas

### Error: "No se encontró el archivo 'credentials.py'"

Solución: Copia `credentials.example.py` como `credentials.py` y completa con tus credenciales.

### Error de Login en Intcomex

- Verifica que las credenciales sean correctas
- Revisa que los selectores CSS sean correctos (pueden haber cambiado)
- Revisa `login_error.png` para ver qué pasó

### Error de Conexión con WooCommerce

- Verifica que la URL de tu tienda sea correcta
- Confirma que las claves API tengan permisos de lectura/escritura
- Verifica que la API REST esté habilitada en WooCommerce

## 📝 Notas

- El bot procesa productos en tiempo real y los sincroniza inmediatamente
- Los productos se marcan automáticamente con "Envío Gratuito"
- Si un producto ya existe (mismo SKU), se actualiza en lugar de crear uno nuevo

## 📄 Licencia

Este proyecto es privado y confidencial.


