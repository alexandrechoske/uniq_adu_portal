
"""
Script de teste para verificar o funcionamento da API de páginas
"""

import os
import sys
import requests
import json
from dotenv import load_dotenv

# Carregar variáveis de ambiente
load_dotenv()

def test_paginas_api():
    """
    Testa a API de páginas simulando diferentes tipos de usuários
    """
    print("=== TESTE DA API DE PÁGINAS ===\n")
    
    # URL base do servidor (ajustar conforme necessário)
    base_url = "http://localhost:5000"  # ou a porta que o Flask está rodando
    
    # Testar sem autenticação
    print("1. Testando acesso sem autenticação...")
    try:
        response = requests.get(f"{base_url}/paginas/api")
        print(f"   Status: {response.status_code}")
        print(f"   Resposta: {response.json()}")
    except Exception as e:
        print(f"   Erro: {e}")
    
    print("\n" + "="*50)
    
    # Instruções para teste manual
    print("2. Para testar com usuário logado:")
    print("   - Execute o servidor Flask: python app.py")
    print("   - Faça login no portal via navegador")
    print("   - Acesse: http://localhost:5000/paginas/api")
    print("   - Verifique os logs no terminal do servidor")
    
    print("\n3. Logs esperados no servidor:")
    print("   [DEBUG] get_paginas: Iniciando função")
    print("   [DEBUG] get_paginas: Usuário logado - ID: X, Role: Y")
    print("   [DEBUG] get_paginas: Fazendo consulta no Supabase...")
    print("   [DEBUG] get_paginas: Dados recebidos: N registros")
    print("   [DEBUG] get_paginas: Dados brutos do Supabase:")
    print("   [DEBUG]   Página 1: ID=X, Nome=Y, Ativo=Z, Roles=[...]")

def test_supabase_direct():
    """
    Testa conexão direta com Supabase (mesmo teste do debug_paginas.py)
    """
    print("\n=== TESTE DIRETO SUPABASE ===\n")
    
    try:
        from supabase import create_client
        
        # Configurações do Supabase
        SUPABASE_URL = os.getenv('SUPABASE_URL')
        SUPABASE_KEY = os.getenv('SUPABASE_ANON_KEY')
        
        if not SUPABASE_URL or not SUPABASE_KEY:
            print("❌ Variáveis de ambiente SUPABASE_URL ou SUPABASE_ANON_KEY não encontradas")
            return
            
        print(f"🔗 Conectando ao Supabase: {SUPABASE_URL}")
        
        # Inicializar cliente Supabase
        supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
        
        # Testar consulta
        print("📊 Executando consulta: SELECT * FROM paginas_portal ORDER BY ordem")
        response = supabase.table('paginas_portal').select('*').order('ordem').execute()
        
        print(f"✅ Consulta executada com sucesso!")
        print(f"📈 Registros encontrados: {len(response.data) if response.data else 0}")
        
        if response.data:
            print(f"\n📋 Dados encontrados:")
            for i, record in enumerate(response.data, 1):
                print(f"   {i}. ID: {record.get('id')}")
                print(f"      Nome: {record.get('nome_pagina')}")
                print(f"      Ativo: {record.get('flg_ativo')}")
                print(f"      Roles: {record.get('roles')}")
                print(f"      Ícone: {record.get('icone')}")
                print(f"      URL: {record.get('url_rota')}")
                print(f"      Ordem: {record.get('ordem')}")
                print()
        else:
            print("⚠️  Nenhum registro encontrado na tabela 'paginas_portal'")
            
    except Exception as e:
        import traceback
        print(f"❌ Erro ao conectar com Supabase: {e}")
        print(f"🔍 Stack trace: {traceback.format_exc()}")

if __name__ == "__main__":
    print("Escolha o teste a executar:")
    print("1. Teste da API (requer servidor rodando)")
    print("2. Teste direto Supabase")
    print("3. Ambos")
    
    choice = input("\nDigite sua escolha (1, 2 ou 3): ").strip()
    
    if choice in ["1", "3"]:
        test_paginas_api()
    
    if choice in ["2", "3"]:
        test_supabase_direct()
    
    if choice not in ["1", "2", "3"]:
        print("Opção inválida. Executando teste direto Supabase...")
        test_supabase_direct()
