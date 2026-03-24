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
        self.queue = []

    def add_update(self, product_id, data):
        """Adds a product update to the queue."""
        update_item = {"id": product_id}
        update_item.update(data)
        self.queue.append(update_item)
        
        if len(self.queue) >= self.chunk_size:
            self.flush()

    def flush(self):
        """Sends all queued updates to the WooCommerce Batch endpoint."""
        if not self.queue:
            return 0
        
        print(f"    [Batch] Sending {len(self.queue)} updates to WooCommerce...")
        sent_count = len(self.queue)
        
        try:
            payload = {"update": self.queue}
            response = self.wcapi.put("products/batch", data=payload)
            
            if response.status_code in [200, 201]:
                print(f"    [Batch] Success! {sent_count} products updated.")
                self.queue = []
                # Small pause to avoid hitting rate limits too hard
                time.sleep(1)
                return sent_count
            else:
                print(f"    [Batch] Error ({response.status_code}): {response.text[:200]}")
                # If batch fails, we might want to log or handle differently
                return 0
        except Exception as e:
            print(f"    [Batch] Exception: {e}")
            return 0

    def get_product_id_by_sku(self, sku):
        """Utility to find product ID by SKU (caching could be added here later)."""
        try:
            res = self.wcapi.get("products", params={"sku": sku}).json()
            if res and len(res) > 0:
                return res[0]['id']
        except Exception as e:
            print(f"    [!] Error finding SKU {sku}: {e}")
        return None
