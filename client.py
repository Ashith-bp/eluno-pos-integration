import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

class ElunoAPIClient:
    def __init__(self, base_url="http://localhost:8787", api_version="admin/api/2026-10"):
        self.base_url = f"{base_url.rstrip('/')}/{api_version.strip('/')}"
        self.root_url = base_url.rstrip('/')
        
        # Session setup with retry policy for transient 429/5xx errors
        self.session = requests.Session()
        retries = Retry(
            total=3,
            backoff_factor=0.5,
            status_forcelist=[429, 500, 502, 503, 504],
            raise_on_status=False
        )
        adapter = HTTPAdapter(max_retries=retries)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)

    def get_products(self) -> dict:
        """Fetch all products from the mock Shopify Admin API."""
        response = self.session.get(f"{self.base_url}/products.json")
        response.raise_for_status()
        return response.json()

    def get_locations(self) -> dict:
        """Fetch all registered store locations."""
        response = self.session.get(f"{self.base_url}/locations.json")
        response.raise_for_status()
        return response.json()

    def search_customers(self, phone: str) -> dict:
        """Search customer database by phone number."""
        response = self.session.get(
            f"{self.base_url}/customers/search.json",
            params={"query": f"phone:{phone}"}
        )
        response.raise_for_status()
        return response.json()

    def get_inventory(self, location_ids: str, inventory_item_ids: str = None) -> dict:
        """Fetch inventory levels for specific locations and inventory items."""
        params = {"location_ids": location_ids}
        if inventory_item_ids:
            params["inventory_item_ids"] = inventory_item_ids
            
        response = self.session.get(f"{self.base_url}/inventory_levels.json", params=params)
        response.raise_for_status()
        return response.json()

    def create_terminal_charge(self, amount_paise: int, order_ref: str, method: str = "upi") -> dict:
        """Initiate a terminal charge using integer paise."""
        payload = {
            "amount_paise": amount_paise,
            "order_ref": order_ref,
            "method": method
        }
        response = self.session.post(f"{self.root_url}/terminal/charges", json=payload)
        response.raise_for_status()
        return response.json()

    def refund_terminal_charge(self, charge_id: str, amount_paise: int, reason: str) -> dict:
        """Issue full or partial refund against a captured terminal charge."""
        payload = {
            "charge_id": charge_id,
            "amount_paise": amount_paise,
            "reason": reason
        }
        response = self.session.post(f"{self.root_url}/terminal/refunds", json=payload)
        response.raise_for_status()
        return response.json()

    def create_order(self, order_payload: dict, idempotency_key: str = None) -> dict:
        """Submit completed order to mock admin API with idempotency support."""
        headers = {}
        if idempotency_key:
            headers["X-Idempotency-Key"] = idempotency_key
        
        response = self.session.post(
            f"{self.base_url}/orders.json",
            json=order_payload,
            headers=headers
        )
        response.raise_for_status()
        return response.json()

if __name__ == "__main__":
    # Integration test flow
    client = ElunoAPIClient()
    print("Testing client connection...")
    products = client.get_products().get("products", [])
    locations = client.get_locations().get("locations", [])
    print(f"Connection verified: {len(products)} products, {len(locations)} locations retrieved.")