# yampi-to-shopify-product-importer

Ferramenta em Python para **migrar e sincronizar produtos da Yampi para a Shopify**. Lê as exportações de produtos da Yampi (planilhas Excel) e cria/atualiza os produtos na Shopify — com variantes (SKUs), imagens, preços e inventário — usando a **GraphQL Admin API** da Shopify.

## Funcionalidades

- 📥 **Leitura robusta das planilhas da Yampi**: os `.xls` exportados pela Yampi costumam vir "corrompidos" (`Workbook corruption: seen[2] == 4`). O leitor tenta abrir ignorando a corrupção via `xlrd` e, se falhar, cai para extração bruta (HTML/CSV com vários encodings e delimitadores).
- 🔄 **Sincronização com a Shopify** via mutation `productSet` (cria/atualiza produto, variantes, mídias e inventário em uma única chamada).
- 🖥️ **Interface gráfica** (`gui.py`) com log de progresso, além do uso por linha de comando.
- 🔐 **Geração automática do `.env`** a partir de um arquivo de credenciais (`setup_env.py`).

## Arquivos

| Arquivo | Papel |
|---------|-------|
| `migrate.py` | Migração dos produtos (leitura da planilha + envio para a Shopify). |
| `sync_direct.py` | Sincronização direta de produtos. |
| `yampi_client.py` | Cliente da API da Yampi. |
| `shopify_client.py` | Cliente da GraphQL Admin API da Shopify. |
| `gui.py` | Interface gráfica. |
| `setup_env.py` | Gera o `.env` a partir de `credentials.md`. |
| `Documento de Integração Yampi e Shopify.md` | Documentação técnica das rotas, payloads e mutations. |

## Configuração

Crie um arquivo `.env` (ou gere com `python setup_env.py` a partir de um `credentials.md`) com:

```env
SHOPIFY_STORE_DOMAIN="sua-loja.myshopify.com"
SHOPIFY_CLIENT_ID="..."
SHOPIFY_CLIENT_SECRET="..."
SHOPIFY_ACCESS_TOKEN="..."
SHOPIFY_LOCATION_ID="..."
YAMPI_USER_TOKEN="..."
YAMPI_USER_SECRET_KEY="..."
YAMPI_MERCHANT_ALIAS="..."
```

> Escopos mínimos do app da Shopify: `write_products`, `read_products`, `write_inventory`, `read_inventory`. API de referência: `2026-01`.

## Como rodar

```bash
pip install -r requirements.txt   # (pandas, xlrd, requests, python-dotenv, ...)

python gui.py          # interface gráfica
# ou
python migrate.py      # via linha de comando
```

## Stack

- Python + **Pandas** + `xlrd` (leitura das planilhas Yampi)
- **Shopify GraphQL Admin API** (`productSet`)
- `requests` · `python-dotenv`
- Tkinter (GUI)

## Documentação

Detalhes das rotas, payloads e exemplos de mutations GraphQL estão em **`Documento de Integração Yampi e Shopify.md`**.
