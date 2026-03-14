import requests
import json
import time

class ShopifyClient:
    def __init__(self, shop_url, access_token=None, client_id=None, client_secret=None):
        """
        Initialize Shopify GraphQL Client
        :param shop_url: e.g. 'your-store.myshopify.com'
        :param access_token: Static Admin API access token (optional)
        :param client_id: For OAuth Client Credentials flow
        :param client_secret: For OAuth Client Credentials flow
        """
        self.shop_url = shop_url
        self.url = f"https://{shop_url}/admin/api/2026-01/graphql.json"
        
        # Priority: Always try to get a fresh token if Credentials exist 
        # (This prevents using a manual/stale token if both are provided)
        if client_id and client_secret:
            try:
                self.access_token = self._fetch_access_token(client_id, client_secret)
            except Exception as e:
                print(f"Auth Error: Could not fetch OAuth token: {e}")
                self.access_token = access_token # fallback to manual token
        else:
            self.access_token = access_token

        if not self.access_token:
            raise ValueError("No valid Shopify authentication provided (Access Token or Credentials).")

        self.headers = {
            "Content-Type": "application/json",
            "X-Shopify-Access-Token": self.access_token
        }

    def _fetch_access_token(self, client_id, client_secret):
        oauth_url = f"https://{self.shop_url}/admin/oauth/access_token"
        payload = {
            "grant_type": "client_credentials",
            "client_id": client_id,
            "client_secret": client_secret
        }
        res = requests.post(oauth_url, data=payload)
        if res.status_code == 200:
            return res.json().get("access_token")
        else:
            raise ValueError(f"Failed to fetch Shopify access token: {res.text}")

    def execute(self, query, variables=None):
        payload = {"query": query, "variables": variables}
        response = requests.post(self.url, headers=self.headers, json=payload)
        
        if response.status_code == 200:
            result = response.json()
            if "errors" in result:
                # Return the result anyway but we could format the errors
                pass
            return result
        else:
            return {"error": f"HTTP Error {response.status_code}", "details": response.text}

    def product_set(self, product_input):
        query = """
        mutation productSet($input: ProductSetInput!) {
          productSet(input: $input) {
            product {
              id
              title
              handle
            }
            userErrors {
              field
              message
            }
          }
        }
        """
        variables = {"input": product_input}
        return self.execute(query, variables)

    def product_create_media(self, product_id, media_urls):
        query = """
        mutation productCreateMedia($media: [CreateMediaInput!]!, $productId: ID!) {
          productCreateMedia(media: $media, productId: $productId) {
            media {
              status
            }
            userErrors {
              field
              message
            }
          }
        }
        """
        media_input = []
        for url in media_urls:
            media_input.append({
                "originalSource": url,
                "mediaContentType": "IMAGE"
            })
            
        variables = {
            "productId": product_id,
            "media": media_input
        }
        return self.execute(query, variables)

    def create_collection(self, title, description=""):
        mutation = """
        mutation collectionCreate($input: CollectionInput!) {
          collectionCreate(input: $input) {
            collection {
              id
              title
            }
            userErrors {
              field
              message
            }
          }
        }
        """
        variables = {
            "input": {
                "title": title,
                "descriptionHtml": description
            }
        }
        return self.execute(mutation, variables)

    def get_collections(self, first=50):
        query = """
        query getCollections($first: Int!) {
          collections(first: $first) {
            edges {
              node {
                id
                title
              }
            }
          }
        }
        """
        variables = {"first": first}
        return self.execute(query, variables)

    def collection_add_products(self, collection_id, product_ids):
        mutation = """
        mutation collectionAddProducts($id: ID!, $productIds: [ID!]!) {
          collectionAddProducts(id: $id, productIds: $productIds) {
            collection {
              id
              title
            }
            userErrors {
              field
              message
            }
          }
        }
        """
        variables = {
            "id": collection_id,
            "productIds": product_ids
        }
        return self.execute(mutation, variables)
