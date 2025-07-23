import requests
import os

# Teste direto da API de documentos
# Para confirmar se o problema é RLS ou lógica da aplicação

def test_documents_api():
    base_url = "http://127.0.0.1:5000"
    
    # 1. Testar com bypass key (deve funcionar)
    print("=== TESTE 1: API com bypass key ===")
    headers_bypass = {
        'X-API-Key': 'test-bypass-key-2024'
    }
    
    response = requests.get(
        f"{base_url}/api/documents/process/UN25%2F6555",
        headers=headers_bypass
    )
    
    print(f"Status: {response.status_code}")
    print(f"Response: {response.text}")
    print()
    
    # 2. Testar sem bypass key (simulando cliente logado)
    print("=== TESTE 2: API sem bypass key ===")
    
    response = requests.get(
        f"{base_url}/api/documents/process/UN25%2F6555"
    )
    
    print(f"Status: {response.status_code}")
    print(f"Response: {response.text}")
    print()
    
    # 3. Testar se o documento realmente existe no banco
    print("=== TESTE 3: Verificar documentos no banco ===")
    print("Execute no Supabase SQL Editor:")
    print("""
    SELECT 
        dp.id,
        dp.ref_unique,
        dp.nome_exibicao,
        dp.visivel_cliente,
        dp.ativo,
        ip.cnpj_importador,
        ip.importador
    FROM documentos_processos dp
    JOIN importacoes_processos_aberta ip ON dp.ref_unique = ip.ref_unique
    WHERE dp.ref_unique = 'UN25/6555';
    """)

if __name__ == "__main__":
    test_documents_api()
