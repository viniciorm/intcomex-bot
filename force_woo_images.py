import json
from woocommerce import API
from credentials import WC_URL, WC_CONSUMER_KEY, WC_CONSUMER_SECRET
from woo_batch_manager import WooBatchManager

def main():
    wcapi = API(
        url=WC_URL,
        consumer_key=WC_CONSUMER_KEY,
        consumer_secret=WC_CONSUMER_SECRET,
        version="wc/v3",
        timeout=60
    )
    
    with open("data_activa/estado_productos.json", "r", encoding="utf-8") as f:
        estado = json.load(f)
        
    skus = list(estado.keys())
    
    # Pre-cargar IDs de Woo
    print("Obteniendo IDs de WooCommerce...")
    import concurrent.futures
    sku_to_pid = {}
    def fetch_id(sku):
        try:
            res = wcapi.get("products", params={"sku": sku, "per_page": 1}).json()
            if res:
                return sku, res[0]['id']
        except:
            pass
        return sku, None

    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        for sku, pid in executor.map(fetch_id, skus):
            if pid:
                sku_to_pid[sku] = pid
                
    # Update Woo with correct Media IDs
    batch = WooBatchManager(wcapi, chunk_size=50)
    count = 0
    for sku, data in estado.items():
        if data.get("woo_media_id") and sku in sku_to_pid:
            payload = {
                "images": [{"id": data["woo_media_id"]}]
            }
            batch.add_update(sku_to_pid[sku], payload)
            count += 1
            
    print(f"Forzando actualización de {count} imágenes en Woo...")
    batch.flush()
    print("✅ Completado.")

if __name__ == "__main__":
    main()
