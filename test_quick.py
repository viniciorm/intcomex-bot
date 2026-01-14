# test_quick.py
# Script de prueba rápida para validar funciones principales sin APIs reales

from sync_bot import (
    clean_price_to_float,
    calculate_sale_price,
    extract_stock_number,
    MIN_STOCK,
    MIN_PRICE_COST
)

def test_price_conversion():
    """Prueba rápida de conversión de precios"""
    print("=" * 60)
    print("PRUEBA: Conversion de Precios")
    print("=" * 60)
    
    test_cases = [
        ("$ 150.000", 150000.0),
        ("$200.500", 200500.0),
        ("$1.500.000", 1500000.0),
        ("150000", 150000.0)
    ]
    
    for price_text, expected in test_cases:
        result = clean_price_to_float(price_text)
        status = "[OK]" if result == expected else "[FAIL]"
        print(f"{status} '{price_text}' -> {result} (esperado: {expected})")
    
    print()

def test_sale_price_calculation():
    """Prueba rápida de cálculo de precio de venta"""
    print("=" * 60)
    print("PRUEBA: Calculo de Precio de Venta (Margen 20%)")
    print("=" * 60)
    
    test_cases = [
        (150000.0, 187500.0),
        (200000.0, 250000.0),
        (300000.0, 375000.0)
    ]
    
    for cost, expected_sale in test_cases:
        sale = calculate_sale_price(cost)
        margin = ((sale - cost) / sale) * 100
        status = "[OK]" if abs(sale - expected_sale) < 0.01 else "[FAIL]"
        print(f"{status} Costo: ${cost:,.0f} -> Venta: ${sale:,.0f} (Margen: {margin:.1f}%)")
    
    print()

def test_stock_extraction():
    """Prueba rápida de extracción de stock"""
    print("=" * 60)
    print("PRUEBA: Extraccion de Stock")
    print("=" * 60)
    
    test_cases = [
        ("Disponible: 100 unidades", 100),
        ("Stock: 50", 50),
        ("Sin stock", 0),
        ("150 unidades disponibles", 150)
    ]
    
    for stock_text, expected in test_cases:
        result = extract_stock_number(stock_text)
        status = "[OK]" if result == expected else "[FAIL]"
        print(f"{status} '{stock_text}' -> {result} (esperado: {expected})")
    
    print()

def test_product_filtering():
    """Prueba rápida de filtrado de productos"""
    print("=" * 60)
    print("PRUEBA: Filtrado de Productos")
    print("=" * 60)
    print(f"Filtros activos: Stock > {MIN_STOCK}, Precio >= ${MIN_PRICE_COST:,} CLP\n")
    
    test_products = [
        {"name": "Producto A", "stock": 100, "price": 200000.0, "should_pass": True},
        {"name": "Producto B", "stock": 30, "price": 200000.0, "should_pass": False},  # Stock bajo
        {"name": "Producto C", "stock": 100, "price": 100000.0, "should_pass": False},  # Precio bajo
        {"name": "Producto D", "stock": 51, "price": 150000.0, "should_pass": True},    # Límites exactos
        {"name": "Producto E", "stock": 50, "price": 150000.0, "should_pass": False},   # Stock exacto (debe filtrarse)
    ]
    
    for product in test_products:
        stock_ok = product["stock"] > MIN_STOCK
        price_ok = product["price"] >= MIN_PRICE_COST
        passes = stock_ok and price_ok
        
        status = "[OK]" if passes == product["should_pass"] else "[FAIL]"
        result_text = "PASA" if passes else "FILTRADO"
        print(f"{status} {product['name']}: Stock={product['stock']}, Precio=${product['price']:,.0f} -> {result_text}")
    
    print()

def test_integration_flow():
    """Prueba de flujo completo de integración"""
    print("=" * 60)
    print("PRUEBA: Flujo Completo de Integracion")
    print("=" * 60)
    
    # Simular producto extraído de Intcomex
    price_text = "$200.000"
    stock_text = "Disponible: 100 unidades"
    sku = "TEST-001"
    
    print(f"Producto simulado: SKU={sku}")
    print(f"  Precio texto: {price_text}")
    print(f"  Stock texto: {stock_text}\n")
    
    # Paso 1: Limpiar precio
    cost_price = clean_price_to_float(price_text)
    print(f"1. Precio limpio: ${cost_price:,.0f} CLP")
    
    # Paso 2: Extraer stock
    stock = extract_stock_number(stock_text)
    print(f"2. Stock extraído: {stock} unidades")
    
    # Paso 3: Verificar filtros
    cumple_stock = stock > MIN_STOCK
    cumple_precio = cost_price >= MIN_PRICE_COST
    print(f"3. Filtros: Stock OK={cumple_stock}, Precio OK={cumple_precio}")
    
    if cumple_stock and cumple_precio:
        # Paso 4: Calcular precio de venta
        sale_price = calculate_sale_price(cost_price)
        print(f"4. Precio de venta: ${sale_price:,.0f} CLP")
        
        # Paso 5: Preparar datos
        product_data = {
            "title": "Producto Test",
            "sku": sku,
            "cost_price": cost_price,
            "sale_price": sale_price,
            "stock": stock
        }
        
        print(f"5. Datos preparados para WooCommerce:")
        print(f"   - Título: {product_data['title']}")
        print(f"   - SKU: {product_data['sku']}")
        print(f"   - Precio costo: ${product_data['cost_price']:,.0f} CLP")
        print(f"   - Precio venta: ${product_data['sale_price']:,.0f} CLP")
        print(f"   - Stock: {product_data['stock']} unidades")
        print("\n[OK] Flujo completo exitoso - Producto listo para sincronizar")
    else:
        print("\n[FILTRADO] Producto filtrado - No se procesara")
    
    print()

if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("PRUEBAS RAPIDAS - Sync Bot")
    print("=" * 60 + "\n")
    
    try:
        test_price_conversion()
        test_sale_price_calculation()
        test_stock_extraction()
        test_product_filtering()
        test_integration_flow()
        
        print("=" * 60)
        print("[OK] TODAS LAS PRUEBAS RAPIDAS COMPLETADAS")
        print("=" * 60)
        print("\nPara ejecutar todas las pruebas automatizadas:")
        print("   pytest test_sync_bot.py -v")
        
    except Exception as e:
        print(f"\n[ERROR] Error durante las pruebas: {e}")
        import traceback
        traceback.print_exc()

