# Documento de Integração Yampi e Shopify

Este documento detalha as rotas, payloads e métodos de integração entre as plataformas Yampi e Shopify, com foco na sincronização de produtos, variantes (SKUs), imagens, categorias e coleções. As informações foram coletadas das documentações oficiais de ambas as plataformas para garantir a precisão e a conformidade com as melhores práticas de API.

## 1. Integração com Shopify

A Shopify oferece uma poderosa **GraphQL Admin API** para gerenciar dados da loja, sendo a abordagem recomendada para operações de sincronização complexas e em massa. A versão da API utilizada como referência é a `2026-01`.

### 1.1. Autenticação

Para interagir com a Shopify Admin API, é necessário criar um aplicativo personalizado (Custom App) na sua loja Shopify. Este aplicativo deve ter os escopos de acesso apropriados para leitura e escrita de produtos, inventário e coleções. Os escopos mínimos necessários incluem `write_products`, `read_products`, `write_inventory` e `read_inventory` [1]. A autenticação é realizada via OAuth, utilizando as chaves de API geradas para o aplicativo [2].

### 1.2. Produtos, Variantes (SKUs) e Inventário

Para a criação e atualização de produtos, variantes, mídias e inventário de forma eficiente, a mutação **`productSet`** é a mais indicada. Ela permite realizar múltiplas operações em um único request, sendo ideal para sincronização de dados de uma fonte externa como a Yampi [3].

#### 1.2.1. Criação/Atualização de Produtos com `productSet`

A mutação `productSet` aceita um objeto `ProductSetInput` que pode incluir o título do produto, opções, variantes, mídias e informações de inventário. É possível definir se a operação será síncrona ou assíncrona; para grandes volumes de dados, a execução assíncrona é recomendada para evitar timeouts [3].

**Exemplo de Payload (GraphQL `productSet`):**

```graphql
mutation productSet($input: ProductSetInput!) {
  productSet(input: $input) {
    product {
      id
      title
      variants(first: 10) {
        edges {
          node {
            id
            sku
            price
            inventoryItem {
              id
              inventoryLevels(first: 1) {
                edges {
                  node {
                    quantities {
                      quantity
                      name
                    }
                  }
                }
              }
            }
          }
        }
      }
      images(first: 5) {
        edges {
          node {
            url
            altText
          }
        }
      }
    }
    userErrors {
      field
      message
    }
    productSetOperation {
      id
      status
    }
  }
}

# Variáveis de Exemplo para a mutação productSet
{
  "input": {
    "id": "gid://shopify/Product/1234567890", # Opcional: ID do produto para atualização
    "title": "Camiseta Personalizada",
    "descriptionHtml": "<p>Uma camiseta de alta qualidade.</p>",
    "vendor": "Minha Marca",
    "productType": "Vestuário",
    "status": "ACTIVE",
    "options": [
      {
        "name": "Cor",
        "values": ["Azul", "Vermelho"]
      },
      {
        "name": "Tamanho",
        "values": ["P", "M", "G"]
      }
    ],
    "variants": [
      {
        "sku": "CAM-AZUL-P",
        "price": "29.90",
        "option1": "Azul",
        "option2": "P",
        "inventoryItem": {
          "tracked": true
        },
        "inventoryQuantities": [
          {
            "availableQuantity": 10,
            "locationId": "gid://shopify/Location/1234567890" # ID do local de inventário
          }
        ]
      },
      {
        "sku": "CAM-VERM-M",
        "price": "34.90",
        "option1": "Vermelho",
        "option2": "M",
        "inventoryItem": {
          "tracked": true
        },
        "inventoryQuantities": [
          {
            "availableQuantity": 5,
            "locationId": "gid://shopify/Location/1234567890"
          }
        ]
      }
    ],
    "media": [
      {
        "alt": "Camiseta Azul",
        "mediaContentType": "IMAGE",
        "originalSource": "https://example.com/imagem_camiseta_azul.jpg"
      },
      {
        "alt": "Camiseta Vermelha",
        "mediaContentType": "IMAGE",
        "originalSource": "https://example.com/imagem_camiseta_vermelha.jpg"
      }
    ]
  }
}
```

**Observações Importantes:**

*   **SKU:** Cada variante deve ter um SKU único. O SKU é crucial para o rastreamento de inventário e para a identificação de produtos [4].
*   **Imagens (Mídias):** As imagens podem ser enviadas fornecendo a `originalSource` como uma URL externa. A Shopify fará o download e hospedará a imagem. É importante notar que a mutação `productCreateMedia` é considerada depreciada, e a recomendação é usar `productSet` ou `productUpdate` para gerenciar mídias [5].
*   **Inventário:** A quantidade de inventário (`availableQuantity`) é definida por variante e por `locationId`. É necessário obter o `locationId` da sua loja Shopify para atribuir o estoque corretamente [6].

### 1.3. Coleções

Para organizar produtos em coleções, a Shopify oferece a mutação **`collectionCreate`** para criar novas coleções [7]. Após a criação, os produtos podem ser associados a essas coleções. Existem dois tipos de coleções: **Custom Collections** (manuais) e **Smart Collections** (automáticas, baseadas em condições) [8]. Para a integração Yampi, as Custom Collections são mais adequadas para um controle direto.

**Exemplo de Payload (GraphQL `collectionCreate`):**

```graphql
mutation collectionCreate($input: CollectionInput!) {
  collectionCreate(input: $input) {
    collection {
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

# Variáveis de Exemplo para a mutação collectionCreate
{
  "input": {
    "title": "Novidades da Semana",
    "descriptionHtml": "<p>Confira os últimos lançamentos!</p>",
    "handle": "novidades-da-semana",
    "sortOrder": "ALPHA_ASC"
  }
}
```

### 1.4. Links da Documentação Oficial da Shopify

*   **Criação de Apps:** [https://shopify.dev/docs/apps/getting-started](https://shopify.dev/docs/apps/getting-started) [1]
*   **Autenticação OAuth:** [https://shopify.dev/docs/apps/auth/oauth](https://shopify.dev/docs/apps/auth/oauth) [2]
*   **Mutação `productSet` (GraphQL):** [https://shopify.dev/docs/api/admin-graphql/latest/mutations/productSet](https://shopify.dev/docs/api/admin-graphql/latest/mutations/productSet) [3]
*   **Objeto `ProductVariant` (GraphQL):** [https://shopify.dev/docs/api/admin-graphql/latest/objects/ProductVariant](https://shopify.dev/docs/api/admin-graphql/latest/objects/ProductVariant) [4]
*   **Mutação `productCreateMedia` (GraphQL - Depreciada):** [https://shopify.dev/docs/api/admin-graphql/latest/mutations/productCreateMedia](https://shopify.dev/docs/api/admin-graphql/latest/mutations/productCreateMedia) [5]
*   **Recurso `InventoryLevel` (REST):** [https://shopify.dev/docs/api/admin-rest/latest/resources/inventorylevel](https://shopify.dev/docs/api/admin-rest/latest/resources/inventorylevel) [6]
*   **Mutação `collectionCreate` (GraphQL):** [https://shopify.dev/docs/api/admin-graphql/latest/mutations/collectioncreate](https://shopify.dev/docs/api/admin-graphql/latest/mutations/collectioncreate) [7]
*   **Recurso `CustomCollection` (REST):** [https://shopify.dev/docs/api/admin-rest/latest/resources/customcollection](https://shopify.dev/docs/api/admin-rest/latest/resources/customcollection) [8]

## 2. Integração com Yampi

A Yampi disponibiliza uma **API REST** para acesso e manipulação dos dados da loja. A documentação oficial é um recurso valioso para entender os endpoints e payloads [9].

### 2.1. Autenticação

A autenticação na API da Yampi é realizada através de `User-Token` e `User-Secret-Key`, que devem ser enviados como headers em todas as requisições. O `Content-Type` deve ser `application/json` [9].

### 2.2. Produtos, Variantes (SKUs), Categorias, Coleções e Estoque

A Yampi oferece endpoints para listar e gerenciar produtos, SKUs, categorias, coleções e estoques. É possível incluir relacionamentos adicionais nas requisições GET para obter um payload mais completo [10].

#### 2.2.1. Listar Produtos

**Rota:** `GET https://api.dooki.com.br/v2/{merchantAlias}/catalog/products`

**Headers:**
*   `User-Token: <seu_user_token>`
*   `User-Secret-Key: <seu_user_secret_key>`
*   `Content-Type: application/json`

**Query Parameters (Exemplo com `include`):**

`?include=skus,images,categories,collections,variations,prices`

Este parâmetro permite obter informações detalhadas sobre SKUs, imagens, categorias, coleções, variações e preços associados aos produtos em uma única requisição [10].

**Exemplo de Resposta (Estrutura Simplificada):**

```json
{
  "data": [
    {
      "id": 12345678,
      "name": "Nome do Produto Yampi",
      "sku": "SKU-PRINCIPAL-YAMPI",
      "total_in_stock": 100,
      "variations": [
        "Cor",
        "Tamanho"
      ],
      "skus": [
        {
          "id": 123,
          "sku": "SKU-AZUL-P",
          "title": "Produto Yampi - Azul P",
          "price_sale": 29.90,
          "total_in_stock": 50,
          "variations": [
            {
              "name": "Cor",
              "value": "Azul"
            },
            {
              "name": "Tamanho",
              "value": "P"
            }
          ]
        }
      ],
      "images": [
        {
          "url": "https://yampi.com.br/imagem_produto_yampi.jpg",
          "alt": "Imagem do Produto Yampi"
        }
      ],
      "categories": [
        {
          "id": 1,
          "name": "Categoria Yampi 1"
        }
      ],
      "collections": [
        {
          "id": 10,
          "name": "Coleção Yampi Destaques"
        }
      ]
    }
  ],
  "meta": {
    "pagination": {
      "total": 1,
      "count": 1,
      "per_page": 10,
      "current_page": 1,
      "total_pages": 1
    }
  }
}
```

#### 2.2.2. Listar SKUs

**Rota:** `GET https://api.dooki.com.br/v2/{merchantAlias}/catalog/skus`

Este endpoint retorna uma lista de SKUs disponíveis, com detalhes como preço, estoque e variações associadas [11].

#### 2.2.3. Listar Categorias

**Rota:** `GET https://api.dooki.com.br/v2/{merchantAlias}/catalog/categories`

Retorna uma lista de categorias do catálogo, incluindo informações como nome, slug e URL [12].

#### 2.2.4. Listar Coleções

**Rota:** `GET https://api.dooki.com.br/v2/{merchantAlias}/catalog/collections`

Este endpoint fornece uma lista de coleções, com detalhes como nome, descrição e produtos associados (se incluído no parâmetro `include`) [13].

#### 2.2.5. Listar Estoques de SKU

**Rota:** `GET https://api.dooki.com.br/v2/{merchantAlias}/catalog/skus/{skuId}/stocks`

Retorna os níveis de estoque para um SKU específico, incluindo a quantidade disponível e a quantidade mínima [14].

### 2.3. Links da Documentação Oficial da Yampi

*   **Yampi Developer Portal:** [https://docs.yampi.com.br](https://docs.yampi.com.br) [9]
*   **Visão Geral da API:** [https://yampi.mintlify.app/introduction](https://yampi.mintlify.app/introduction) [9]
*   **Listar Produtos:** [https://yampi.mintlify.app/api-reference/catalogo/produtos/listar-produtos](https://yampi.mintlify.app/api-reference/catalogo/produtos/listar-produtos) [10]
*   **Listar SKUs:** [https://yampi.mintlify.app/api-reference/catalogo/skus/listar-skus](https://yampi.mintlify.app/api-reference/catalogo/skus/listar-skus) [11]
*   **Listar Categorias:** [https://yampi.mintlify.app/api-reference/catalogo/categorias/listar-categorias](https://yampi.mintlify.app/api-reference/catalogo/categorias/listar-categorias) [12]
*   **Listar Coleções:** [https://yampi.mintlify.app/api-reference/catalogo/colecoes/listar-colecoes](https://yampi.mintlify.app/api-reference/catalogo/colecoes/listar-colecoes) [13]
*   **Listar Estoques de SKU:** [https://yampi.mintlify.app/api-reference/catalogo/skus/estoques-de-sku/listar-estoques](https://yampi.mintlify.app/api-reference/catalogo/skus/estoques-de-sku/listar-estoques) [14]

## Referências

[1] Shopify. (n.d.). *Criação de Apps*. Disponível em: [https://shopify.dev/docs/apps/getting-started](https://shopify.dev/docs/apps/getting-started)
[2] Shopify. (n.d.). *Autenticação OAuth*. Disponível em: [https://shopify.dev/docs/apps/auth/oauth](https://shopify.dev/docs/apps/auth/oauth)
[3] Shopify. (n.d.). *productSet - GraphQL Admin*. Disponível em: [https://shopify.dev/docs/api/admin-graphql/latest/mutations/productSet](https://shopify.dev/docs/api/admin-graphql/latest/mutations/productSet)
[4] Shopify. (n.d.). *ProductVariant - GraphQL Admin*. Disponível em: [https://shopify.dev/docs/api/admin-graphql/latest/objects/ProductVariant](https://shopify.dev/docs/api/admin-graphql/latest/objects/ProductVariant)
[5] Shopify. (n.d.). *productCreateMedia - GraphQL Admin*. Disponível em: [https://shopify.dev/docs/api/admin-graphql/latest/mutations/productCreateMedia](https://shopify.dev/docs/api/admin-graphql/latest/mutations/productCreateMedia)
[6] Shopify. (n.d.). *InventoryLevel - Shopify Dev Docs*. Disponível em: [https://shopify.dev/docs/api/admin-rest/latest/resources/inventorylevel](https://shopify.dev/docs/api/admin-rest/latest/resources/inventorylevel)
[7] Shopify. (n.d.). *collectionCreate - GraphQL Admin*. Disponível em: [https://shopify.dev/docs/api/admin-graphql/latest/mutations/collectioncreate](https://shopify.dev/docs/api/admin-graphql/latest/mutations/collectioncreate)
[8] Shopify. (n.d.). *CustomCollection*. Disponível em: [https://shopify.dev/docs/api/admin-rest/latest/resources/customcollection](https://shopify.dev/docs/api/admin-rest/latest/resources/customcollection)
[9] Yampi. (n.d.). *Yampi Developer Portal*. Disponível em: [https://docs.yampi.com.br](https://docs.yampi.com.br)
[10] Yampi. (n.d.). *Listar produtos*. Disponível em: [https://yampi.mintlify.app/api-reference/catalogo/produtos/listar-produtos](https://yampi.mintlify.app/api-reference/catalogo/produtos/listar-produtos)
[11] Yampi. (n.d.). *Listar SKUs*. Disponível em: [https://yampi.mintlify.app/api-reference/catalogo/skus/listar-skus](https://yampi.mintlify.app/api-reference/catalogo/skus/listar-skus)
[12] Yampi. (n.d.). *Listar categorias*. Disponível em: [https://yampi.mintlify.app/api-reference/catalogo/categorias/listar-categorias](https://yampi.mintlify.app/api-reference/catalogo/categorias/listar-categorias)
[13] Yampi. (n.d.). *Listar coleções*. Disponível em: [https://yampi.mintlify.app/api-reference/catalogo/colecoes/listar-colecoes](https://yampi.mintlify.app/api-reference/catalogo/colecoes/listar-colecoes)
[14] Yampi. (n.d.). *Listar estoques*. Disponível em: [https://yampi.mintlify.app/api-reference/catalogo/skus/estoques-de-sku/listar-estoques](https://yampi.mintlify.app/api-reference/catalogo/skus/estoques-de-sku/listar-estoques)
