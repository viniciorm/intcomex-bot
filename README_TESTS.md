# 🧪 Suite de Pruebas TDD - Sync Bot

Este documento describe cómo ejecutar y mantener las pruebas automatizadas para el bot de sincronización Intcomex -> WooCommerce.

## 📋 Resumen

El archivo `test_sync_bot.py` contiene **40 pruebas automatizadas** que cubren:

- ✅ Conversión de precios CLP a float
- ✅ Cálculo de precio de venta con margen del 20%
- ✅ Extracción de números de stock
- ✅ Filtrado de productos (stock > 50, precio > $150.000)
- ✅ Integración con API de WooCommerce (crear/actualizar productos)
- ✅ Flujos de integración completos
- ✅ Casos límite y validaciones

## 🚀 Ejecutar Pruebas

### Instalación de Dependencias

```bash
pip install -r requirements.txt
```

### Ejecutar Todas las Pruebas

```bash
pytest test_sync_bot.py -v
```

### Ejecutar Pruebas con Más Detalle

```bash
pytest test_sync_bot.py -v --tb=long
```

### Ejecutar una Clase de Pruebas Específica

```bash
pytest test_sync_bot.py::TestCleanPriceToFloat -v
```

### Ejecutar una Prueba Específica

```bash
pytest test_sync_bot.py::TestCleanPriceToFloat::test_precio_con_espacios_y_simbolo -v
```

### Ejecutar con Cobertura de Código

```bash
pip install pytest-cov
pytest test_sync_bot.py --cov=sync_bot --cov-report=html
```

## 📊 Estructura de las Pruebas

### 1. TestCleanPriceToFloat (9 pruebas)
Pruebas para la conversión de precios CLP desde texto a float:
- Precios con espacios y símbolos
- Precios sin espacios
- Precios con separadores de miles
- Casos edge (vacíos, None, inválidos)

### 2. TestCalculateSalePrice (6 pruebas)
Pruebas para el cálculo de precio de venta:
- Cálculo correcto con margen del 20%
- Validación de precios None, cero o negativos
- Verificación de precisión del margen

### 3. TestExtractStockNumber (7 pruebas)
Pruebas para extracción de números de stock:
- Stock solo con números
- Stock con texto descriptivo
- Casos edge (sin números, vacíos, None)

### 4. TestProductFiltering (4 pruebas)
Pruebas para la lógica de filtrado:
- Filtro de stock mínimo (> 50)
- Filtro de precio mínimo (>= $150.000)
- Productos que cumplen/no cumplen filtros

### 5. TestFindProductBySku (3 pruebas)
Pruebas para búsqueda de productos en WooCommerce:
- Producto existe
- Producto no existe
- Errores de API

### 6. TestCreateProductInWooCommerce (3 pruebas)
Pruebas para creación de productos:
- Creación exitosa
- Configuración de envío gratuito
- Manejo de errores

### 7. TestUpdateProductInWooCommerce (2 pruebas)
Pruebas para actualización de productos:
- Actualización exitosa
- Productos sin stock

### 8. TestIntegrationFlow (3 pruebas)
Pruebas de integración del flujo completo:
- Flujo completo de producto válido
- Filtrado por stock
- Filtrado por precio

### 9. TestEdgeCases (3 pruebas)
Pruebas para casos límite:
- Precio exacto en el mínimo
- Stock exacto en el mínimo
- Precisión de cálculos

## 🔄 Workflow TDD Recomendado

1. **Antes de hacer cambios:**
   ```bash
   pytest test_sync_bot.py -v
   ```
   Asegúrate de que todas las pruebas pasen.

2. **Al agregar nueva funcionalidad:**
   - Escribe primero la prueba (RED)
   - Implementa la funcionalidad (GREEN)
   - Refactoriza si es necesario (REFACTOR)

3. **Después de hacer cambios:**
   ```bash
   pytest test_sync_bot.py -v
   ```
   Verifica que nada se haya roto.

## 🐛 Solución de Problemas

### Si una prueba falla:

1. Lee el mensaje de error detallado
2. Revisa qué función está fallando
3. Verifica que la implementación coincida con lo esperado
4. Ejecuta la prueba específica con `-vv` para más detalles

### Si necesitas agregar nuevas pruebas:

1. Identifica la función o funcionalidad a probar
2. Agrega una nueva clase de pruebas o método de prueba
3. Sigue el patrón de las pruebas existentes
4. Ejecuta las pruebas para verificar

## 📝 Notas Importantes

- Las pruebas usan **mocks** para la API de WooCommerce, por lo que no requieren conexión real
- Las pruebas de Selenium (login, scraping) no están incluidas porque requieren navegador real
- Para pruebas de integración completa, ejecuta el script `sync_bot.py` manualmente

## ✅ Estado Actual

**40/40 pruebas pasando** ✅

Todas las funciones principales están cubiertas por pruebas automatizadas.


