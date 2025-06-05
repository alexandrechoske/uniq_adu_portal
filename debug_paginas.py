#!/usr/bin/env python3
"""
Script de debug para investigar o problema com a API de páginas retornando dados vazios
"""

import os
import sys
from dotenv import load_dotenv
from supabase import create_client

# Carregar variáveis de ambiente
load_dotenv()

def test_paginas_table():
    """Testa a conexão e consulta à tabela paginas_portal"""
    
    try:
        # Configurar cliente Supabase
        supabase_url = os.getenv('SUPABASE_URL')
        supabase_key = os.getenv('SUPABASE_KEY')
        
        if not supabase_url or not supabase_key:
            print("❌ Variáveis de ambiente SUPABASE_URL ou SUPABASE_KEY não encontradas")
            return False
            
        print(f"🔗 Conectando ao Supabase: {supabase_url}")
        supabase = create_client(supabase_url, supabase_key)
        
        # Testar consulta simples
        print("\n📋 Testando consulta básica...")
        response = supabase.table('paginas_portal').select('*').execute()
        
        print(f"✅ Consulta executada com sucesso")
        print(f"📊 Número de registros encontrados: {len(response.data)}")
        
        if response.data:
            print("\n📄 Páginas encontradas:")
            for i, page in enumerate(response.data, 1):
                print(f"  {i}. ID: {page.get('id', 'N/A')}")
                print(f"     Nome: {page.get('nome_pagina', 'N/A')}")
                print(f"     Ativo: {page.get('flg_ativo', 'N/A')}")
                print(f"     Roles: {page.get('roles', 'N/A')}")
                print(f"     Ordem: {page.get('ordem', 'N/A')}")
                print()
                
        # Testar consulta com filtro e ordenação (como no código)
        print("📋 Testando consulta com ordem...")
        response_ordered = supabase.table('paginas_portal').select('*').order('ordem').execute()
        print(f"✅ Consulta ordenada executada: {len(response_ordered.data)} registros")
        
        # Testar consulta com filtro de páginas ativas
        print("\n📋 Testando consulta de páginas ativas...")
        response_active = supabase.table('paginas_portal').select('*').eq('flg_ativo', True).order('ordem').execute()
        print(f"✅ Páginas ativas encontradas: {len(response_active.data)}")
        
        if response_active.data:
            print("\n🟢 Páginas ativas:")
            for page in response_active.data:
                print(f"  - {page.get('nome_pagina', 'N/A')} (ordem: {page.get('ordem', 'N/A')})")
        
        return True
        
    except Exception as e:
        print(f"❌ Erro ao testar tabela paginas_portal: {e}")
        import traceback
        print(traceback.format_exc())
        return False

def test_user_permissions():
    """Testa a lógica de permissões para diferentes tipos de usuário"""
    
    print("\n🔐 Testando lógica de permissões...")
    
    # Simular dados de teste
    test_pages = [
        {'id': 1, 'nome_pagina': 'Dashboard', 'roles': ['admin', 'cliente_unique'], 'flg_ativo': True},
        {'id': 2, 'nome_pagina': 'Usuários', 'roles': ['admin'], 'flg_ativo': True},
        {'id': 3, 'nome_pagina': 'Agente', 'roles': ['cliente_unique'], 'flg_ativo': True},
        {'id': 4, 'nome_pagina': 'Página Inativa', 'roles': ['admin'], 'flg_ativo': False},
    ]
    
    # Testar para admin
    print("\n👑 Teste para usuário ADMIN:")
    admin_pages = test_pages  # Admin vê todas as páginas
    print(f"  Páginas visíveis: {len(admin_pages)}")
    for page in admin_pages:
        print(f"    - {page['nome_pagina']} (ativo: {page['flg_ativo']})")
    
    # Testar para cliente_unique
    print("\n👤 Teste para usuário CLIENTE_UNIQUE:")
    client_pages = [page for page in test_pages if page.get('roles') and 'cliente_unique' in page['roles']]
    print(f"  Páginas visíveis: {len(client_pages)}")
    for page in client_pages:
        print(f"    - {page['nome_pagina']} (ativo: {page['flg_ativo']})")

if __name__ == "__main__":
    print("🚀 SCRIPT DE DEBUG - PÁGINAS DO PORTAL")
    print("=" * 50)
    
    # Testar tabela
    if test_paginas_table():
        # Testar permissões
        test_user_permissions()
    
    print("\n✅ Debug concluído")
