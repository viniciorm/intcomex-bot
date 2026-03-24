import time
from woocommerce import API

class WooBatchManager:
    """
    Handles batch updates to WooCommerce to reduce network overhead.
    Groups updates into chunks of 100 as per WC API recommendations.
    """
    def __init__(self, wcapi, chunk_size=100):
        self.wcapi = wcapi
        self.chunk_size = chunk_size
        self.update_queue = []
        self.create_queue = []

    def add_update(self, product_id, data):
        """Adds a product update to the queue."""
        update_item = {"id": product_id}
        update_item.update(data)
        self.update_queue.append(update_item)
        if (len(self.update_queue) + len(self.create_queue)) >= self.chunk_size:
            self.flush()

    def add_create(self, data):
        """Adds a new product to the creation queue."""
        self.create_queue.append(data)
        if (len(self.update_queue) + len(self.create_queue)) >= self.chunk_size:
            self.flush()

    def flush(self):
        """Sends all queued updates and creations to WooCommerce."""
        if not self.update_queue and not self.create_queue:
            return 0
        
        up_count = len(self.update_queue)
        cr_count = len(self.create_queue)
        print(f"    [Batch] Sending {up_count} updates and {cr_count} creations...")
        
        try:
            payload = {}
            if self.update_queue: payload["update"] = self.update_queue
            if self.create_queue: payload["create"] = self.create_queue
            
            response = self.wcapi.put("products/batch", data=payload)
            
            if response.status_code in [200, 201]:
                print(f"    [Batch] Success! {up_count + cr_count} products processed.")
                # Si hubo creaciones, capturamos sus IDs (Opcional, pero util para actualizar el estado local inmediatamente)
                results = response.json()
                self.update_queue = []
                self.create_queue = []
                time.sleep(1)
                return results
            else:
                print(f"    [Batch] Error ({response.status_code}): {response.text[:200]}")
                return None
        except Exception as e:
            print(f"    [Batch] Exception: {e}")
            return None

    def get_product_id_by_sku(self, sku):
        """Utility to find product ID by SKU (caching could be added here later)."""
        try:
            res = self.wcapi.get("products", params={"sku": sku}).json()
            if res and len(res) > 0:
                return res[0]['id']
        except Exception as e:
            print(f"    [!] Error finding SKU {sku}: {e}")
        return None
