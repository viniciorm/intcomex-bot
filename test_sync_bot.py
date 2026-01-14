# test_sync_bot.py
# Suite de pruebas TDD para sync_bot.py
# Ejecutar con: pytest test_sync_bot.py -v

import pytest
from unittest.mock import Mock, patch, MagicMock
from sync_bot import (
    clean_price_to_float,
    calculate_sale_price,
    extract_stock_number,
    find_product_by_sku,
    create_product_in_woocommerce,
    update_product_in_woocommerce,
    MIN_STOCK,
    MIN_PRICE_COST,
    MARGIN_PERCENTAGE
)


# ============================================
# TESTS: clean_price_to_float
# ============================================

class TestCleanPriceToFloat:
    """Tests para la función de conversión de precios CLP a float"""
    
    def test_precio_con_espacios_y_simbolo(self):
        """Test: "$ 150.000" debe convertirse a 150000.0"""
        assert clean_price_to_float("$ 150.000") == 150000.0
    
    def test_precio_sin_espacios(self):
        """Test: "$150.000" debe convertirse a 150000.0"""
        assert clean_price_to_float("$150.000") == 150000.0
    
    def test_precio_con_punto_separador_miles(self):
        """Test: "$200.500" debe convertirse a 200500.0"""
        assert clean_price_to_float("$200.500") == 200500.0
    
    def test_precio_sin_simbolo(self):
        """Test: "150000" debe convertirse a 150000.0"""
        assert clean_price_to_float("150000") == 150000.0
    
    def test_precio_con_coma_decimal(self):
        """Test: "$150.000,50" debe convertirse a 150000.50"""
        assert clean_price_to_float("$150.000,50") == 150000.50
    
    def test_precio_texto_vacio(self):
        """Test: String vacío debe retornar None"""
        assert clean_price_to_float("") is None
    
    def test_precio_none(self):
        """Test: None debe retornar None"""
        assert clean_price_to_float(None) is None
    
    def test_precio_invalido(self):
        """Test: Texto sin números debe retornar None"""
        assert clean_price_to_float("sin números") is None
    
    def test_precio_muy_grande(self):
        """Test: Precio de millones debe funcionar correctamente"""
        assert clean_price_to_float("$1.500.000") == 1500000.0


# ============================================
# TESTS: calculate_sale_price
# ============================================

class TestCalculateSalePrice:
    """Tests para el cálculo de precio de venta con margen del 20%"""
    
    def test_calculo_precio_venta_150000(self):
        """Test: Costo $150.000 -> Venta $187.500 (150000 / 0.8)"""
        cost = 150000.0
        expected = 187500.0  # 150000 / (1 - 0.20)
        result = calculate_sale_price(cost)
        assert result == expected
    
    def test_calculo_precio_venta_200000(self):
        """Test: Costo $200.000 -> Venta $250.000"""
        cost = 200000.0
        expected = 250000.0
        result = calculate_sale_price(cost)
        assert abs(result - expected) < 0.01  # Tolerancia para floats
    
    def test_precio_none_retorna_none(self):
        """Test: None debe retornar None"""
        assert calculate_sale_price(None) is None
    
    def test_precio_cero_retorna_none(self):
        """Test: Precio 0 debe retornar None"""
        assert calculate_sale_price(0) is None
    
    def test_precio_negativo_retorna_none(self):
        """Test: Precio negativo debe retornar None"""
        assert calculate_sale_price(-100) is None
    
    def test_margen_correcto_20_porciento(self):
        """Test: Verificar que el margen aplicado es exactamente 20%"""
        cost = 100000.0
        sale_price = calculate_sale_price(cost)
        margin = (sale_price - cost) / sale_price
        assert abs(margin - MARGIN_PERCENTAGE) < 0.001


# ============================================
# TESTS: extract_stock_number
# ============================================

class TestExtractStockNumber:
    """Tests para la extracción de números de stock"""
    
    def test_stock_solo_numero(self):
        """Test: "100" debe retornar 100"""
        assert extract_stock_number("100") == 100
    
    def test_stock_con_texto(self):
        """Test: "Disponible: 100 unidades" debe retornar 100"""
        assert extract_stock_number("Disponible: 100 unidades") == 100
    
    def test_stock_multiple_numeros_toma_primero(self):
        """Test: "Stock: 50 de 100" debe retornar 50 (primer número)"""
        assert extract_stock_number("Stock: 50 de 100") == 50
    
    def test_stock_sin_numeros_retorna_cero(self):
        """Test: "Sin stock" debe retornar 0"""
        assert extract_stock_number("Sin stock") == 0
    
    def test_stock_vacio_retorna_cero(self):
        """Test: String vacío debe retornar 0"""
        assert extract_stock_number("") == 0
    
    def test_stock_none_retorna_cero(self):
        """Test: None debe retornar 0"""
        assert extract_stock_number(None) == 0
    
    def test_stock_grande(self):
        """Test: Números grandes deben funcionar"""
        assert extract_stock_number("Stock: 5000 unidades") == 5000


# ============================================
# TESTS: Filtrado de Productos
# ============================================

class TestProductFiltering:
    """Tests para la lógica de filtrado de productos"""
    
    def test_filtro_stock_minimo(self):
        """Test: Producto con stock <= 50 debe ser filtrado"""
        stock_insuficiente = 49
        stock_suficiente = 51
        
        assert stock_insuficiente <= MIN_STOCK  # Debe filtrarse
        assert stock_suficiente > MIN_STOCK    # No debe filtrarse
    
    def test_filtro_precio_minimo(self):
        """Test: Producto con precio < $150.000 debe ser filtrado"""
        precio_insuficiente = 149999.0
        precio_suficiente = 150001.0
        
        assert precio_insuficiente < MIN_PRICE_COST  # Debe filtrarse
        assert precio_suficiente >= MIN_PRICE_COST   # No debe filtrarse
    
    def test_producto_cumple_ambos_filtros(self):
        """Test: Producto debe cumplir ambos filtros para procesarse"""
        stock = 100
        precio = 200000.0
        
        cumple_stock = stock > MIN_STOCK
        cumple_precio = precio >= MIN_PRICE_COST
        
        assert cumple_stock and cumple_precio  # Debe procesarse
    
    def test_producto_no_cumple_filtros(self):
        """Test: Producto que no cumple filtros debe ser rechazado"""
        stock = 30
        precio = 100000.0
        
        cumple_stock = stock > MIN_STOCK
        cumple_precio = precio >= MIN_PRICE_COST
        
        assert not (cumple_stock and cumple_precio)  # No debe procesarse


# ============================================
# TESTS: WooCommerce API - find_product_by_sku
# ============================================

class TestFindProductBySku:
    """Tests para la búsqueda de productos por SKU en WooCommerce"""
    
    @patch('sync_bot.API')
    def test_producto_existe_retorna_datos(self, mock_api_class):
        """Test: Si el producto existe, debe retornar sus datos"""
        # Mock de la respuesta de la API
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = [{"id": 123, "sku": "TEST-SKU", "name": "Producto Test"}]
        
        mock_wcapi = Mock()
        mock_wcapi.get.return_value = mock_response
        
        result = find_product_by_sku(mock_wcapi, "TEST-SKU")
        
        assert result is not None
        assert result["id"] == 123
        assert result["sku"] == "TEST-SKU"
        mock_wcapi.get.assert_called_once_with("products", params={"sku": "TEST-SKU", "per_page": 1})
    
    @patch('sync_bot.API')
    def test_producto_no_existe_retorna_none(self, mock_api_class):
        """Test: Si el producto no existe, debe retornar None"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = []
        
        mock_wcapi = Mock()
        mock_wcapi.get.return_value = mock_response
        
        result = find_product_by_sku(mock_wcapi, "SKU-INEXISTENTE")
        
        assert result is None
    
    @patch('sync_bot.API')
    def test_error_api_retorna_none(self, mock_api_class):
        """Test: Si hay error en la API, debe retornar None"""
        mock_wcapi = Mock()
        mock_wcapi.get.side_effect = Exception("Error de conexión")
        
        result = find_product_by_sku(mock_wcapi, "TEST-SKU")
        
        assert result is None


# ============================================
# TESTS: WooCommerce API - create_product_in_woocommerce
# ============================================

class TestCreateProductInWooCommerce:
    """Tests para la creación de productos en WooCommerce"""
    
    @patch('sync_bot.API')
    def test_crear_producto_exitoso(self, mock_api_class):
        """Test: Crear producto exitosamente debe retornar True"""
        product_data = {
            "title": "Producto Test",
            "description": "Descripción test",
            "sku": "TEST-001",
            "cost_price": 150000.0,
            "sale_price": 187500.0,
            "stock": 100,
            "image_url": "https://example.com/image.jpg"
        }
        
        mock_response = Mock()
        mock_response.status_code = 201
        mock_response.text = "Created"
        
        mock_wcapi = Mock()
        mock_wcapi.post.return_value = mock_response
        
        result = create_product_in_woocommerce(mock_wcapi, product_data)
        
        assert result is True
        mock_wcapi.post.assert_called_once()
        call_args = mock_wcapi.post.call_args
        assert call_args[0][0] == "products"
        data = call_args[0][1]  # data es el segundo argumento posicional
        assert data["name"] == "Producto Test"
        assert data["sku"] == "TEST-001"
        assert data["regular_price"] == "187500.0"
        assert data["stock_quantity"] == 100
    
    @patch('sync_bot.API')
    def test_crear_producto_con_envio_gratuito(self, mock_api_class):
        """Test: Producto debe crearse con envío gratuito"""
        product_data = {
            "title": "Producto Test",
            "sku": "TEST-002",
            "sale_price": 200000.0,
            "stock": 50,
            "image_url": "https://example.com/image.jpg"
        }
        
        mock_response = Mock()
        mock_response.status_code = 201
        
        mock_wcapi = Mock()
        mock_wcapi.post.return_value = mock_response
        
        create_product_in_woocommerce(mock_wcapi, product_data)
        
        call_args = mock_wcapi.post.call_args
        data = call_args[0][1]  # data es el segundo argumento posicional
        assert data["shipping_class"] == "free-shipping"
        assert {"name": "Envío Gratuito"} in data["tags"]
    
    @patch('sync_bot.API')
    def test_crear_producto_error_api(self, mock_api_class):
        """Test: Error en API debe retornar False"""
        product_data = {"title": "Test", "sku": "TEST-003", "sale_price": 100000.0, "stock": 10}
        
        mock_response = Mock()
        mock_response.status_code = 400
        mock_response.text = "Bad Request"
        
        mock_wcapi = Mock()
        mock_wcapi.post.return_value = mock_response
        
        result = create_product_in_woocommerce(mock_wcapi, product_data)
        
        assert result is False


# ============================================
# TESTS: WooCommerce API - update_product_in_woocommerce
# ============================================

class TestUpdateProductInWooCommerce:
    """Tests para la actualización de productos en WooCommerce"""
    
    @patch('sync_bot.API')
    def test_actualizar_producto_exitoso(self, mock_api_class):
        """Test: Actualizar producto exitosamente debe retornar True"""
        product_data = {
            "sku": "TEST-001",
            "sale_price": 200000.0,
            "stock": 150
        }
        
        mock_response = Mock()
        mock_response.status_code = 200
        
        mock_wcapi = Mock()
        mock_wcapi.put.return_value = mock_response
        
        result = update_product_in_woocommerce(mock_wcapi, 123, product_data)
        
        assert result is True
        mock_wcapi.put.assert_called_once()
        call_args = mock_wcapi.put.call_args
        assert call_args[0][0] == "products/123"
        data = call_args[0][1]  # data es el segundo argumento posicional
        assert data["regular_price"] == "200000.0"
        assert data["stock_quantity"] == 150
        assert data["stock_status"] == "instock"
    
    @patch('sync_bot.API')
    def test_actualizar_producto_sin_stock(self, mock_api_class):
        """Test: Producto sin stock debe marcarse como outofstock"""
        product_data = {
            "sku": "TEST-002",
            "sale_price": 150000.0,
            "stock": 0
        }
        
        mock_response = Mock()
        mock_response.status_code = 200
        
        mock_wcapi = Mock()
        mock_wcapi.put.return_value = mock_response
        
        update_product_in_woocommerce(mock_wcapi, 456, product_data)
        
        call_args = mock_wcapi.put.call_args
        data = call_args[0][1]  # data es el segundo argumento posicional
        assert data["stock_status"] == "outofstock"


# ============================================
# TESTS: Integración - Flujo Completo
# ============================================

class TestIntegrationFlow:
    """Tests de integración para el flujo completo de procesamiento"""
    
    def test_flujo_completo_producto_valido(self):
        """Test: Flujo completo desde precio hasta creación"""
        # Simular datos de producto extraído
        price_text = "$200.000"
        stock_text = "Disponible: 100 unidades"
        sku = "PROD-001"
        
        # Paso 1: Limpiar precio
        cost_price = clean_price_to_float(price_text)
        assert cost_price == 200000.0
        
        # Paso 2: Extraer stock
        stock = extract_stock_number(stock_text)
        assert stock == 100
        
        # Paso 3: Verificar filtros
        cumple_stock = stock > MIN_STOCK
        cumple_precio = cost_price >= MIN_PRICE_COST
        assert cumple_stock and cumple_precio
        
        # Paso 4: Calcular precio de venta
        sale_price = calculate_sale_price(cost_price)
        assert sale_price == 250000.0
        
        # Paso 5: Preparar datos
        product_data = {
            "title": "Producto Test",
            "sku": sku,
            "cost_price": cost_price,
            "sale_price": sale_price,
            "stock": stock
        }
        
        assert product_data["sale_price"] > product_data["cost_price"]
        assert product_data["stock"] > MIN_STOCK
    
    def test_flujo_producto_filtrado_por_stock(self):
        """Test: Producto debe ser filtrado si stock es insuficiente"""
        price_text = "$200.000"
        stock_text = "Stock: 30 unidades"
        
        cost_price = clean_price_to_float(price_text)
        stock = extract_stock_number(stock_text)
        
        cumple_stock = stock > MIN_STOCK
        cumple_precio = cost_price >= MIN_PRICE_COST
        
        # Debe ser filtrado por stock
        assert not cumple_stock
        assert cumple_precio
        assert not (cumple_stock and cumple_precio)
    
    def test_flujo_producto_filtrado_por_precio(self):
        """Test: Producto debe ser filtrado si precio es insuficiente"""
        price_text = "$100.000"
        stock_text = "Stock: 100 unidades"
        
        cost_price = clean_price_to_float(price_text)
        stock = extract_stock_number(stock_text)
        
        cumple_stock = stock > MIN_STOCK
        cumple_precio = cost_price >= MIN_PRICE_COST
        
        # Debe ser filtrado por precio
        assert cumple_stock
        assert not cumple_precio
        assert not (cumple_stock and cumple_precio)


# ============================================
# TESTS: Casos Edge y Validaciones
# ============================================

class TestEdgeCases:
    """Tests para casos límite y validaciones"""
    
    def test_precio_exacto_minimo(self):
        """Test: Precio exactamente en el mínimo debe pasar el filtro"""
        precio = MIN_PRICE_COST
        assert precio >= MIN_PRICE_COST
    
    def test_stock_exacto_minimo(self):
        """Test: Stock exactamente en el mínimo debe ser filtrado"""
        stock = MIN_STOCK
        assert stock <= MIN_STOCK  # Debe filtrarse (necesita > 50)
    
    def test_margen_calculo_preciso(self):
        """Test: Verificar precisión del cálculo de margen"""
        cost = 100000.0
        sale = calculate_sale_price(cost)
        # Verificar que el margen es exactamente 20%
        expected_margin = cost / (1 - MARGIN_PERCENTAGE)
        assert abs(sale - expected_margin) < 0.01


if __name__ == "__main__":
    # Ejecutar pruebas con pytest
    pytest.main([__file__, "-v", "--tb=short"])

