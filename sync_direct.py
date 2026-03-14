import os
import argparse
from shopify_client import ShopifyClient
from yampi_client import YampiClient
from dotenv import load_dotenv

def migrate_yampi_to_shopify(y_client, s_client, price_modifier=None, log_cb=print, dry_run=False):
    log_cb("Buscando produtos na API da Yampi...")
    y_products = y_client.get_products()
    log_cb(f"Encontrados {len(y_products)} produtos.")

    for i, y_prod in enumerate(y_products):
        log_cb(f"[{i+1}/{len(y_products)}] Sincronizando: {y_prod['name']}...")
        
        # Build Variants
        shopify_variants = []
        options_map = {} # To store option names and their index
        
        for y_sku in y_prod.get('skus', []):
            original_price = float(y_sku.get('price_sale', 0) or 0)
            final_price = original_price
            
            if price_modifier:
                ptype = price_modifier.get('type')
                pvalue = float(price_modifier.get('value', 0))
                
                if ptype == 'fixed':
                    final_price = pvalue
                elif ptype == 'percentage':
                    final_price = original_price * (1 + (pvalue / 100))
                    
            s_variant = {
                "sku": y_sku['sku'],
                "price": f"{final_price:.2f}",
                "inventoryItem": {"tracked": True},
                "inventoryQuantities": [
                    {
                        "quantity": y_sku.get('total_in_stock', 0),
                        "name": "available",
                        "locationId": os.getenv("SHOPIFY_LOCATION_ID")
                    }
                ],
                "optionValues": []
            }
            
            # Map variations
            # Yampi variations in SKU are like: [{"name": "Cor", "value": "Azul"}, ...]
            for variation in y_sku.get('variations', []):
                opt_name = variation['name']
                opt_value = variation['value']
                s_variant["optionValues"].append({
                    "optionName": opt_name,
                    "name": opt_value
                })
                
                if opt_name not in options_map:
                    options_map[opt_name] = set()
                options_map[opt_name].add(opt_value)
            
            shopify_variants.append(s_variant)

        # Build Options
        shopify_options = []
        for opt_name, values in options_map.items():
            shopify_options.append({
                "name": opt_name,
                "values": [{"name": v} for v in values]
            })

        # Build Media
        shopify_media_urls = [y_img['url'] for y_img in y_prod.get('images', [])]

        product_input = {
            "title": y_prod['name'],
            "descriptionHtml": y_prod.get('description', ''),
            "vendor": y_prod.get('brand', {}).get('name', ''),
            "status": "ACTIVE" if y_prod.get('active') else "ARCHIVED",
            "variants": shopify_variants
        }
        
        if shopify_options:
            product_input["productOptions"] = shopify_options

        if dry_run:
            log_cb(f"DRY RUN: O produto {y_prod['name']} seria sincronizado.")
        else:
            res = s_client.product_set(product_input)
            if res and 'data' in res and res['data'].get('productSet', {}).get('product'):
                p_id = res['data']['productSet']['product']['id']
                log_cb(f"Sucesso: {y_prod['name']} sincronizado (ID: {p_id}).")
                
                if shopify_media_urls:
                    s_client.product_create_media(p_id, shopify_media_urls)
                    log_cb(f"Media sincronizada para {y_prod['name']}.")
            else:
                log_cb(f"Falha ao sincronizar {y_prod['name']}. Resposta: {res}")
                
    log_cb("Sincronização por API finalizada.")

def run_api_sync(price_modifier=None, log_cb=print, dry_run=False):
    load_dotenv(override=True)

    
    # Yampi Credentials
    # Shopify Credentials
    shop_url = os.getenv("SHOPIFY_STORE_DOMAIN")
    access_token = os.getenv("SHOPIFY_ACCESS_TOKEN")
    client_id = os.getenv("SHOPIFY_CLIENT_ID")
    client_secret = os.getenv("SHOPIFY_CLIENT_SECRET")
    location_id = os.getenv("SHOPIFY_LOCATION_ID")
    
    yampi_token = os.getenv("YAMPI_USER_TOKEN")
    yampi_secret = os.getenv("YAMPI_USER_SECRET_KEY")
    yampi_alias = os.getenv("YAMPI_MERCHANT_ALIAS")
    
    if not shop_url or not location_id:
        log_cb("Erro: Credenciais de loja ou location da Shopify faltando no arquivo .env.")
        return
        
    if not access_token and (not client_id or not client_secret):
        log_cb("Erro: Falta credencial de autenticação da Shopify (Access Token OU Client ID/Secret) no arquivo .env.")
        return
        
    if not all([yampi_token, yampi_secret, yampi_alias]):
        log_cb("Erro: Credenciais da Yampi faltando no arquivo .env.")
        return

    # Initialize generic clients
    try:
        shopify_client = ShopifyClient(shop_url, access_token=access_token, client_id=client_id, client_secret=client_secret)
    except Exception as e:
        log_cb(f"Falha na autenticação da API Shopify: {e}")
        return

    yampi_client = YampiClient(yampi_token, yampi_secret, yampi_alias)

    migrate_yampi_to_shopify(yampi_client, shopify_client, price_modifier, log_cb, dry_run)

def main():
    parser = argparse.ArgumentParser(description='Directly sync Yampi API to Shopify')
    parser.add_argument('--dry-run', action='store_true', help='Do not upload to Shopify')
    args = parser.parse_args()
    
    run_api_sync(dry_run=args.dry_run)

if __name__ == "__main__":
    main()
