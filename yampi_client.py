import requests

class YampiClient:
    def __init__(self, user_token, user_secret, merchant_alias):
        """
        Initialize Yampi REST Client
        """
        self.base_url = f"https://api.dooki.com.br/v2/{merchant_alias}"
        self.headers = {
            "User-Token": user_token,
            "User-Secret-Key": user_secret,
            "Content-Type": "application/json"
        }

    def fetch_all(self, endpoint, include=None):
        """
        Generic method to fetch all items from an endpoint with pagination
        """
        results = []
        page = 1
        params = {"page": page}
        if include:
            params["include"] = include

        while True:
            response = requests.get(f"{self.base_url}/{endpoint}", headers=self.headers, params=params)
            if response.status_code != 200:
                print(f"Error fetching {endpoint}: {response.text}")
                break
            
            data = response.json()
            results.extend(data.get("data", []))
            
            meta = data.get("meta", {}).get("pagination", {})
            if page >= meta.get("total_pages", 1):
                break
            
            page += 1
            params["page"] = page
            
        return results

    def get_products(self):
        return self.fetch_all("catalog/products", include="skus,images,categories,collections,variations,prices")

    def get_categories(self):
        return self.fetch_all("catalog/categories")

    def get_collections(self):
        return self.fetch_all("catalog/collections")
