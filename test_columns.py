#!/usr/bin/env python3
"""
Script para testar e verificar as colunas da tabela importacoes_processos
"""

from extensions import init_supabase

# Inicializar o Supabase
supabase, supabase_admin = init_supabase()

try:
    # Fazer uma consulta simples para verificar quais campos existem
    print("Testando consulta básica...")
    response = supabase.table('importacoes_processos').select('*').limit(1).execute()
    
    if response.data:
        print("\n=== CAMPOS DISPONÍVEIS NA TABELA ===")
        for field in response.data[0].keys():
            print(f"- {field}")
        
        print(f"\nTotal de campos: {len(response.data[0].keys())}")
        print("Consulta realizada com sucesso!")
    else:
        print("Nenhum dado encontrado na tabela")
        
except Exception as e:
    print(f"Erro ao consultar tabela: {e}")
    print(f"Tipo do erro: {type(e)}")
