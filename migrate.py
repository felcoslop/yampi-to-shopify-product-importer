import pandas as pd
import os
import json
import argparse
from shopify_client import ShopifyClient
from dotenv import load_dotenv

import io

import xlrd

def robust_read(filepath, log_cb):
    """
    Reads .xls using xlrd with corruption bypassed, or .xlsx normally.
    Yampi exports are notorious for 'Workbook corruption: seen[2] == 4'.
    """
    try:
        if filepath.endswith('.xls'):
            log_cb(f"Abrindo XLS (tentando ignorar corrupção padrão da Yampi)...")
            book = xlrd.open_workbook(filepath, ignore_workbook_corruption=True)
            sheet = book.sheet_by_index(0)
            
            # Convert xlrd sheet to pandas dataframe
            data = []
            for rx in range(sheet.nrows):
                data.append(sheet.row_values(rx))
                
            if data:
                columns = [str(c).strip().lower() for c in data[0]]
                df = pd.DataFrame(data[1:], columns=columns)
                log_cb(f"Arquivo lido com sucesso usando xlrd nativo. Linhas extraídas: {len(df)}")
                return df
            else:
                raise ValueError("Planilha vazia.")
        else:
            return pd.read_excel(filepath)
            
    except Exception as e1:
        log_cb(f"Leitura Excel com xlrd falhou ({e1}). Tentando extrações adicionais (HTML/CSV)...")
        # Fallback para texto bruto/HTML caso Yampi mude o formato no futuro
        try:
            with open(filepath, 'rb') as f:
                raw_bytes = f.read()
            
            encodings_to_try = ['utf-8', 'iso-8859-1', 'cp1252', 'utf-16', 'utf-16le', 'utf-16be']
            delimiters_to_try = ['\t', ',', ';']
            
            for enc in encodings_to_try:
                try:
                    text_data = raw_bytes.decode(enc)
                    for delim in delimiters_to_try:
                        df = pd.read_csv(io.StringIO(text_data), sep=delim, on_bad_lines='skip', low_memory=False)
                        df.columns = [str(col).strip().lower() for col in df.columns]
                        if 'id' in df.columns:
                            return df
                except Exception:
                    continue
            raise ValueError("Não foi possível processar o arquivo de nenhuma das formas.")
        except Exception as e3:
            log_cb(f"Falha total ao ler o arquivo {filepath}: {e3}")
            raise

def parse_excel_migration(products_file, skus_file, price_modifier=None, log_cb=print):
    """
    Parses and merges Excel files from Yampi exports.
    """
    log_cb(f"Carregando {products_file}...")
    try:
        df_products = robust_read(products_file, log_cb)
    except Exception:
        return []

    log_cb(f"Carregando {skus_file}...")
    try:
        df_skus = robust_read(skus_file, log_cb)
    except Exception:
        return []

    # Basic data cleaning
    df_products = df_products.fillna('')
    df_skus = df_skus.fillna('')

    migration_data = []

    # Iterate through products
    for _, prod in df_products.iterrows():
        prod_id = prod['id']
        
        # Find variants for this product
        # The column in SKUs is 'id_produto'
        variants = df_skus[df_skus['id_produto'] == prod_id]
        
        if variants.empty:
            log_cb(f"Warning: No variants found for product ID {prod_id} ({prod['nome']})")
            continue

        # Prepare Shopify ProductSetInput
        # Mapping:
        # nome -> title
        # descricao -> descriptionHtml
        # link_foto_principal -> originalSource in media
        
        # Prepare Shopify ProductSetInput
        shopify_variants = []
        options_values_tracker = {} # {opt_name: set(values)}
        
        for _, var in variants.iterrows():
            variation_str = var.get('valores_de_variacoes', '')
            opt_values = {}
            if variation_str:
                parts = [p.strip() for p in str(variation_str).split(',')]
                for i, p in enumerate(parts):
                    if ':' in p:
                        kv = p.split(':')
                        k, v = kv[0].strip(), kv[1].strip()
                    else:
                        k = "Tamanho" if i == 0 else f"Opção {i+1}"
                        v = p.strip()
                    
                    opt_values[k] = v
                    if k not in options_values_tracker:
                        options_values_tracker[k] = set()
                    options_values_tracker[k].add(v)
            elif variants.shape[0] > 1:
                k = "Título"
                v = var['nome_produto'] if 'nome_produto' in var else f"Variante {var['id']}"
                opt_values[k] = v
                if k not in options_values_tracker:
                    options_values_tracker[k] = set()
                options_values_tracker[k].add(v)

            # Handle price modifier
            original_price = float(var.get('preco_venda', 0) or 0)
            final_price = original_price
            
            if price_modifier:
                ptype = price_modifier.get('type')
                pvalue = float(price_modifier.get('value', 0))
                
                if ptype == 'fixed':
                    final_price = pvalue
                elif ptype == 'percentage':
                    final_price = original_price * (1 + (pvalue / 100))

            # Create variant for Shopify
            s_variant = {
                "sku": str(var['sku']),
                "price": f"{final_price:.2f}",
                "inventoryItem": {"tracked": True},
                "inventoryQuantities": [
                    {
                        "quantity": 9999, # User requested 9999 units
                        "name": "available",
                        "locationId": os.getenv("SHOPIFY_LOCATION_ID")
                    }
                ],
                "optionValues": []
            }
            
            # Map options to optionValues
            for opt_name, opt_val in opt_values.items():
                s_variant["optionValues"].append({
                    "optionName": opt_name,
                    "name": opt_val
                })
            
            shopify_variants.append(s_variant)

        # Build options list for Shopify
        shopify_options = []
        for opt_name, val_set in options_values_tracker.items():
            shopify_options.append({
                "name": opt_name,
                "values": [{"name": v} for v in val_set]
            })

        product_input = {
            "title": prod['nome'],
            "descriptionHtml": prod['descricao'],
            "vendor": prod['marca'] if 'marca' in prod else '',
            "status": "ACTIVE" if prod['ativo'] == 'Sim' or prod['ativo'] is True else "ARCHIVED",
            "variants": shopify_variants
        }

        if shopify_variants:
            # If no options were captured but we have variants, Shopify will fail.
            # We already handled dummy options above, but as a final safety:
            if not shopify_options:
                shopify_options = [{"name": "Title", "values": [{"name": "Default Title"}]}]
                for v in shopify_variants:
                    if not v.get("optionValues"):
                        v["optionValues"] = [{"optionName": "Title", "name": "Default Title"}]
            
            product_input["productOptions"] = shopify_options
        
        # Media (Simplified string list)
        product_media = []
        if prod['link_foto_principal']:
            product_media = [prod['link_foto_principal']]

        migration_data.append({
            "product": product_input,
            "media": product_media,
            "category": prod.get('categoria', '').strip()
        })

    return migration_data

def run_migration(products_file, skus_file, price_modifier=None, log_cb=print, dry_run=False):
    load_dotenv(override=True)
    
    shop_url = os.getenv("SHOPIFY_STORE_DOMAIN")
    access_token = os.getenv("SHOPIFY_ACCESS_TOKEN")
    client_id = os.getenv("SHOPIFY_CLIENT_ID")
    client_secret = os.getenv("SHOPIFY_CLIENT_SECRET")
    location_id = os.getenv("SHOPIFY_LOCATION_ID")
    
    if not shop_url or not location_id:
        log_cb("Erro: Credenciais de loja ou location faltando no arquivo .env.")
        return
        
    if not access_token and (not client_id or not client_secret):
        log_cb("Erro: Falta credencial de autenticação (Access Token OU Client ID/Secret) no arquivo .env.")
        return

    data = parse_excel_migration(products_file, skus_file, price_modifier, log_cb)

    try:
        client = ShopifyClient(shop_url, access_token=access_token, client_id=client_id, client_secret=client_secret)
    except Exception as e:
        log_cb(f"Falha na autenticação da API: {e}")
        return

    # Cache for collections
    collection_map = {}
    try:
        existing = client.get_collections()
        if existing and 'data' in existing:
            for edge in existing['data']['collections']['edges']:
                node = edge['node']
                collection_map[node['title'].lower()] = node['id']
    except Exception as e:
        log_cb(f"Aviso: Não foi possível buscar coleções existentes: {e}")

    for i, item in enumerate(data):
        prod_title = item['product']['title']
        category_name = item.get('category')
        log_cb(f"[{i+1}/{len(data)}] Migrating: {prod_title}...")
        
        if dry_run:
            log_cb(f"DRY RUN: Payload for {prod_title} would be sent. Variants count: {len(item['product'].get('variants', []))}. Categoria: {category_name}")
        else:
            res = client.product_set(item['product'])
            if res and 'data' in res and res['data'].get('productSet', {}).get('product'):
                p_id = res['data']['productSet']['product']['id']
                log_cb(f"Sucesso: {prod_title} migrado (ID: {p_id}).")
                
                # Step 2: Media
                if item['media']:
                    client.product_create_media(p_id, item['media'])
                    log_cb(f"Media enviada para {prod_title}.")
                
                # Step 3: Collection/Category
                if category_name:
                    c_id = collection_map.get(category_name.lower())
                    if not c_id:
                        log_cb(f"Criando coleção: {category_name}")
                        c_res = client.create_collection(category_name)
                        if c_res and 'data' in c_res and c_res['data']['collectionCreate']['collection']:
                            c_id = c_res['data']['collectionCreate']['collection']['id']
                            collection_map[category_name.lower()] = c_id
                    
                    if c_id:
                        client.collection_add_products(c_id, [p_id])
                        log_cb(f"Produto adicionado à coleção: {category_name}")
            else:
                log_cb(f"Falha ao migrar {prod_title}. Resposta: {res}")
                
    log_cb("Migração por Excel finalizada.")

def main():
    parser = argparse.ArgumentParser(description='Migrate Yampi Excel to Shopify')
    parser.add_argument('--dry-run', action='store_true', help='Do not upload to Shopify')
    args = parser.parse_args()

    products_file = "products-69b337642d0b4.xls"
    skus_file = "pequenocraque-skus-12_03_2026_19_02_39-ZZQkJ.xlsx"

    run_migration(products_file, skus_file, dry_run=args.dry_run)

if __name__ == "__main__":
    main()

