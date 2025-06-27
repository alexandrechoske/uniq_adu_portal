#!/bin/bash
set -e -E

GEMINI_API_KEY="$GEMINI_API_KEY"
MODEL_ID="gemini-2.5-flash-preview-04-17"
GENERATE_CONTENT_API="streamGenerateContent"

cat << EOF > request.json
{
    "contents": [
      {
        "role": "user",
        "parts": [
          {
            "inlineData": {
              "mimeType": "application/pdf",
              "data": "aqui vai o base64 do PDF"
            }
          },
          {
            "text": "leia esse arquivo o que ele se trata?"
          },
        ]
      },
      {
        "role": "model",
        "parts": [
          {
            "text": "**Deciphering the Document**\n\nI've initially recognized the user's query is in Portuguese. My focus shifted to identifying the languages within the document; it appears to contain both Swedish and Portuguese elements. My preliminary assumption is this could be a document discussing a trade or business transaction, but this is mere speculation. The presence of dates and supplier information is noted, pointing towards this interpretation. I am now working on understanding these elements in context.\n\n\n**Pinpointing the Key Elements**\n\nI've determined the document is an invoice, written primarily in Swedish and English, with a question in Portuguese.  I'm focusing on the financial aspects now: company names, invoice numbers, dates, and amounts. I'm also examining the terms of payment to further understand the nature of this transaction, and the customer/supplier information.  Next, I'll identify the products and how they relate to a potential transaction.\n\n\n**Clarifying the Document Type**\n\nI've determined that the document is an invoice from Humphree AB in Sweden to Azimut do Brasil.  My analysis now focuses on understanding the specific products listed and their corresponding amounts, to clarify the transaction details. I'm also examining the terms of the transaction, payment due dates, and delivery conditions to understand the overall nature of the transaction.\n\n\n**Summarizing the Invoice Details**\n\nI have determined that the document is an invoice from Humphree AB to Azimut do Brasil, related to the sale of stabilization equipment. I've focused on the key transactional details, like invoice date, due date, payment terms, and the specific items sold. Now, I'm verifying the total amount due, currency, and payment instructions.\n\n\n**Defining the Transaction's Context**\n\nI've determined that the document is an invoice from Humphree AB to Azimut do Brasil, related to maritime equipment. I'm now examining the specific item details to determine their function. I'm also analyzing the payment terms and shipping terms to fully understand the transaction's context and any applicable regulations. Finally, I'll be examining the \"Trim & Stabilisation\" products to gain insight into the specific equipment being sold.\n\n\n**Confirming the Transaction's Nature**\n\nI've determined that this is an international sales invoice from Humphree AB in Sweden to Azimut do Brasil. My analysis indicates a sale of \"Trim & Stabilisation\" equipment, specifically for maritime applications. Key information includes the invoice number, date, and payment terms, with a total value of 10,476.00 EUR. The invoice reflects international shipping arrangements and contains all the details that indicate it's a sales transaction.\n\n\n**Defining the Invoice's Function**\n\nI've determined that this is an invoice from Humphree AB to Azimut do Brasil, with the specific intent to facilitate an international sales transaction of maritime equipment. My focus is now on confirming the details of the products, their origins, and the financial and legal context of the transaction, and formulating a complete answer to the user's question, which will also give context about the sale.\n\n\\n\\n\nThis file is an Invoice or Fiscal Note. It is a commercial document that details a sale of products made by the company Humphree AB (located in Sweden) to the company Azimut do Brasil (located in Brazil). It lists the products sold (such as adapters, servo units, cables, installation kits, etc., which seem to be related to 'Trim & Stabilisation' systems), the quantities, weights, origin (Sweden), and the total value of the transaction (10,476.00 EUR). It also informs the invoice date (2025-01-22), payment terms (30 days net, due on 2025-02-22), Incoterms (Free Carrier), bank details for payment, and other references like the invoice number, customer's CNPJ, and Taric code. In summary, it is an international sales invoice for equipment for Azimut do Brasil.\n\n\n"
          },
          {
            "text": "Este arquivo é uma **Fatura (Invoice)** ou **Nota Fiscal** internacional.\n\nTrata-se de um documento comercial que detalha uma venda de produtos realizada pela empresa **Humphree AB** (localizada na Suécia) para a empresa **Azimut do Brasil** (localizada no Brasil).\n\nEle lista os produtos vendidos (como adaptadores, unidades servo, cabos, kits de instalação, etc., que parecem estar relacionados a sistemas de \"Trim & Stabilisation\"), as quantidades, pesos, origem (Suécia), e o valor total da transação (10.476,00 EUR).\n\nTambém informa a data da fatura (2025-01-22), as condições de pagamento (30 dias líquidos, com vencimento em 2025-02-22), os Incoterms (Free Carrier), dados bancários para pagamento, e outras referências como número da fatura, CNPJ do cliente e Taric code.\n\nEm resumo, é uma fatura de venda internacional de equipamentos para a Azimut do Brasil."
          },
        ]
      },
      {
        "role": "user",
        "parts": [
          {
            "text": "INSERT_INPUT_HERE"
          },
        ]
      },
    ],
    "generationConfig": {
      "thinkingConfig": {
        "thinkingBudget": -1,
      },
      "responseMimeType": "text/plain",
    },
}
EOF

curl \
-X POST \
-H "Content-Type: application/json" \
"https://generativelanguage.googleapis.com/v1beta/models/${MODEL_ID}:${GENERATE_CONTENT_API}?key=${GEMINI_API_KEY}" -d '@request.json'




REQUISIÇÃO EM PYTHON:

# To run this code you need to install the following dependencies:
# pip install google-genai

import base64
import os
from google import genai
from google.genai import types


def generate():
    client = genai.Client(
        api_key=os.environ.get("GEMINI_API_KEY"),
    )

    model = "gemini-2.5-flash-preview-04-17"
    contents = [
        types.Content(
            role="user",
            parts=[
                types.Part.from_bytes(
                    mime_type="application/pdf",
                    data=base64.b64decode(
                        """aqui vai o códigodo pdf, base64"""
                    ),
                ),
                types.Part.from_text(text="""esse é um prompt exemplo de entrada"""),
            ],
        ),
        types.Content(
            role="model",
            parts=[
                types.Part.from_text(text="""**Extracting Key Data**

I'm currently working on identifying the key information fields within the multi-page scanned invoice document. Page one's focus is on the header, specifically the company name and logo, which will be the first data point I extract. The structural approach I'm taking is to first identify the most likely regions, and then use content matching to pinpoint the correct data.


**Mapping Invoice Fields**

I've made significant progress in identifying and mapping the key fields across the first page. I've successfully extracted the company details, invoice and order numbers, customer information, and the billing and shipping addresses. I am now working on extracting the critical line item information including descriptions, quantities, prices, and totals from the table.


**Detailing Page Data**

I'm now fully immersed in the details of the first two pages. Page 1 data, like company and customer addresses, invoice and order numbers, along with line items including descriptions, quantities, and prices, are mapped. The second page's continuation, with a focus on item descriptions and supplier details, is also under analysis.


**Analyzing Invoice Data**

I've completed the initial analysis of all three pages, focusing on extracting sender, receiver, and invoice details. Line item data, including descriptions, quantities, and prices, are now being accurately categorized. Payment terms and the total amount are also under consideration, which will provide a complete understanding of the financial aspects.


**Mapping Data Points**

My focus has shifted to the granular extraction of data points from each page. I've successfully identified and categorized the fundamental data, including sender, receiver, invoice details, line items with complete descriptions. I will focus on extraction, cleaning, and validating the extracted data. I will include HS Codes, Countries of Origin, Manufacturers and Exporters in item 3's description.


"""),
                types.Part.from_text(text="""```json
{
  \"invoice_number\": \"236439\",
  \"invoice_date\": \"11.12.2023\",
  \"customer_id\": \"12445\",
  \"order_number\": \"234164\",
  \"customer_order_reference\": \"4500005083 - Ship 2 Bianca Pita\",
  \"sender\": {
    \"name\": \"Wieland Eucaro GmbH\",
    \"address\": \"Senator-Helmken-Straße 3\",
    \"city\": \"Bremen\",
    \"zip_code\": \"28197\",
    \"country\": \"Germany\",
    \"phone\": \"+49 421 52025 0\",
    \"email\": \"eucaro@wieland.com\",
    \"website\": \"www.wieland.com/eucaro\",
    \"tax_id\": \"DE 811 398 151\",
    \"bank_details\": {
      \"bank_name\": \"Commerzbank\",
      \"iban\": \"DE 86 2908 0010 0101 6714 00\",
      \"bic\": \"DRESDEFF290\"
    }
  },
  \"recipient\": {
    \"name\": \"AGUAS AZUIS CONSTRUCAO NAVAL SPE LTDA.\",
    \"address\": \"Rua Eugenio Pezzini, 355\",
    \"city\": \"Itajai\",
    \"zip_code\": \"8831-060\",
    \"country\": \"Brazil\",
    \"cnpj\": \"36.277.163/001-63\"
  },
  \"delivery_address\": {
    \"name\": \"AGUAS AZUIS CONSTRUCAO NAVAL SPE LTDA.\",
    \"address\": \"Rua Eugenio Pezzini, 355\",
    \"city\": \"Itajai\",
    \"zip_code\": \"BR8831-060\",
    \"country\": \"Brazil\"
  },
  \"delivery_terms\": \"FCA\",
  \"transport_method\": \"Collection\",
  \"agent\": \"Minura\",
  \"items\": [
    {
      \"item_number\": 1,
      \"article_number\": \"319100007248\",
      \"description\": \"Outer flange DIN 2642 DN 20/OD 25 G-CuSn10Zn PN10/16 EHN 9512/630/03 T01\",
      \"delivery_date\": \"48-2023\",
      \"quantity\": 4.00,
      \"unit\": \"pce\",
      \"unit_price\": 226.50,
      \"total_price\": 906.00,
      \"currency\": \"EUR\",
      \"hs_code\": \"74122000\",
      \"country_of_origin\": \"Germany\",
      \"material_number\": \"9500403534\"
    },
    {
      \"item_number\": 2,
      \"article_number\": \"RORN10110200\",
      \"description\": \"Pipe DIN 86019 OD 10x1,0 EUCARO10 EUCARO10 = CuNi10Fe1,6Mn F30 EHN 9412/121/01 Rev. 10 36 Meter\",
      \"delivery_date\": \"48-2023\",
      \"quantity\": 9.00,
      \"unit\": \"kgs\",
      \"unit_price\": 32.50,
      \"total_price\": 292.50,
      \"currency\": \"EUR\",
      \"hs_code\": \"74112200\",
      \"country_of_origin\": \"Austria\",
      \"material_number\": \"9500505421\",
      \"notes\": \"Pipes must be protected with end caps on both sides\"
    },
    {
      \"item_number\": 3,
      \"article_number\": \"ZEUG3.1\",
      \"description\": \"Inspection certificate 3.1 EN 10204-2005 for all items\",
      \"delivery_date\": \"48-2023\",
      \"quantity\": 1.00,
      \"unit\": \"pce\",
      \"unit_price\": 0.00,
      \"total_price\": 0.00,
      \"currency\": \"EUR\",
      \"notes\": \"Description of goods: Fittings of copper nickel alloy\"
    }
  ],
  \"subtotal\": 1198.50,
  \"total_amount_net\": 1198.50,
  \"total_amount_eur\": 1198.50,
  \"currency\": \"EUR\",
  \"payment_terms\": \"60 days net cash\",
  \"payment_due_dates\": [
    \"09.02.2024\"
  ],
  \"additional_information\": {
    \"manufacturers\": [
      {
        \"item_reference\": \"Item. 1\",
        \"name\": \"Raguse + Voss GmbH\",
        \"address\": \"Grauwallring 24 27580 Bremerhaven, Germany\"
      },
      {
        \"item_reference\": \"Item. 2\",
        \"name\": \"Wieland Austria Ges.m.b.H\",
        \"address\": \"Fabrikstraße 4 3300 Amstetten, Austria\"
      }
    ],
    \"exporter\": {
      \"name\": \"Wieland Eucaro GmbH\",
      \"address\": \"Senator-Helmken-Str. 3 28197 Bremen, Germany\"
    },
    \"package_details\": [
      {
        \"reference\": \"2367\",
        \"description\": \"case\",
        \"dimensions\": \"6,10x0,25x0,20mtr.\",
        \"gross_weight_kg\": 34.00,
        \"net_weight_kg\": 9.00
      },
      {
        \"reference\": \"2248\",
        \"description\": \"packed to order\",
        \"order_number\": \"234160\",
        \"net_weight_kg\": 3.68
      }
    ]
  }
}
```"""),
            ],
        ),
        types.Content(
            role="user",
            parts=[
                types.Part.from_text(text="""INSERT_INPUT_HERE"""),
            ],
        ),
    ]
    generate_content_config = types.GenerateContentConfig(
        thinking_config = types.ThinkingConfig(
            thinking_budget=-1,
        ),
        response_mime_type="text/plain",
    )

    for chunk in client.models.generate_content_stream(
        model=model,
        contents=contents,
        config=generate_content_config,
    ):
        print(chunk.text, end="")

if __name__ == "__main__":
    generate()
