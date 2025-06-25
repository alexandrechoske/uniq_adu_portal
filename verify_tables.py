#!/usr/bin/env python3
"""
Script simples para verificar a estrutura atual da tabela importacoes_processos
e executar alguns comandos de teste
"""

import sys
import os

# Adicionar o diretório pai ao path para importar os módulos
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

try:
    from supabase import create_client
    from config import Config
    
    print("🔧 Verificação da Estrutura das Tabelas - Unique Aduaneira")
    print("=" * 60)
    
    # Criar cliente do Supabase diretamente
    print(f"🔗 URL do Supabase: {Config.SUPABASE_URL}")
    
    # Verificar se as configurações existem
    if not hasattr(Config, 'SUPABASE_URL') or not Config.SUPABASE_URL:
        print("❌ SUPABASE_URL não configurado")
        sys.exit(1)
        
    if not hasattr(Config, 'SUPABASE_SERVICE_KEY') or not Config.SUPABASE_SERVICE_KEY:
        print("❌ SUPABASE_SERVICE_KEY não configurado")
        sys.exit(1)
    
    # Criar cliente admin
    supabase_admin = create_client(Config.SUPABASE_URL, Config.SUPABASE_SERVICE_KEY)
    print("✅ Cliente Supabase criado com sucesso")
    
    # Tentar acessar a tabela importacoes_processos
    try:
        print("\n📊 Verificando tabela 'importacoes_processos'...")
        result = supabase_admin.table('importacoes_processos').select('count', count='exact').limit(1).execute()
        print(f"✅ Tabela 'importacoes_processos' encontrada")
        print(f"📈 Total de registros: {result.count}")
        
        # Mostrar alguns registros como exemplo
        sample_result = supabase_admin.table('importacoes_processos').select('*').limit(3).execute()
        if sample_result.data:
            print(f"📋 Campos disponíveis no primeiro registro:")
            for field in sample_result.data[0].keys():
                print(f"   - {field}")
            
            print(f"\n📝 Exemplo de registros:")
            for i, record in enumerate(sample_result.data[:2], 1):
                print(f"   Registro {i}:")
                print(f"      - numero: {record.get('numero', 'N/A')}")
                print(f"      - data_embarque: {record.get('data_embarque', 'N/A')}")
                print(f"      - carga_status: {record.get('carga_status', 'N/A')}")
                print(f"      - via_transporte_descricao: {record.get('via_transporte_descricao', 'N/A')}")
                print(f"      - data_registro: {record.get('data_registro', 'N/A')}")
                print(f"      - ref_unique: {record.get('ref_unique', 'N/A')}")
                print(f"      - observacoes: {record.get('observacoes', 'N/A')}")
        
    except Exception as e:
        print(f"❌ Erro ao acessar 'importacoes_processos': {str(e)}")
    
    # Tentar acessar a tabela importacoes_despesas
    try:
        print("\n📊 Verificando tabela 'importacoes_despesas'...")
        result = supabase_admin.table('importacoes_despesas').select('count', count='exact').limit(1).execute()
        print(f"✅ Tabela 'importacoes_despesas' encontrada")
        print(f"📈 Total de registros: {result.count}")
        
    except Exception as e:
        print(f"❌ Erro ao acessar 'importacoes_despesas': {str(e)}")
        print("💡 A tabela pode não existir ainda - isso é normal se o DDL não foi aplicado")
    
    # Verificar algumas queries básicas
    try:
        print("\n🔍 Testando queries básicas...")
        
        # Query 1: Contar por status
        status_result = supabase_admin.table('importacoes_processos').select('carga_status').limit(5).execute()
        if status_result.data:
            statuses = [r.get('carga_status') for r in status_result.data if r.get('carga_status')]
            print(f"✅ Query por carga_status funcionando - exemplos: {list(set(statuses))[:3]}")
        
        # Query 2: Contar por modal de transporte
        modal_result = supabase_admin.table('importacoes_processos').select('via_transporte_descricao').limit(5).execute()
        if modal_result.data:
            modals = [r.get('via_transporte_descricao') for r in modal_result.data if r.get('via_transporte_descricao')]
            print(f"✅ Query por via_transporte_descricao funcionando - exemplos: {list(set(modals))}")
        
        # Query 3: Verificar se novos campos existem
        new_fields_test = supabase_admin.table('importacoes_processos').select('data_registro', 'ref_unique', 'observacoes').limit(1).execute()
        if new_fields_test.data and new_fields_test.data[0]:
            has_data_registro = 'data_registro' in new_fields_test.data[0]
            has_ref_unique = 'ref_unique' in new_fields_test.data[0]
            has_observacoes = 'observacoes' in new_fields_test.data[0]
            
            print(f"✅ Novos campos disponíveis:")
            print(f"   - data_registro: {'✅' if has_data_registro else '❌'}")
            print(f"   - ref_unique: {'✅' if has_ref_unique else '❌'}")
            print(f"   - observacoes: {'✅' if has_observacoes else '❌'}")
            
            if has_data_registro and has_ref_unique and has_observacoes:
                print("🎉 Todos os novos campos estão disponíveis!")
            else:
                print("⚠️ Alguns novos campos podem estar faltando")
        else:
            print(f"⚠️ Não foi possível verificar os novos campos")
            
    except Exception as e:
        print(f"❌ Erro ao testar queries: {str(e)}")
    
    print("\n🎉 Verificação concluída!")
    
except ImportError as e:
    print(f"❌ Erro ao importar módulos: {str(e)}")
    print("💡 Certifique-se de que está executando no diretório correto")
except Exception as e:
    print(f"❌ Erro geral: {str(e)}")

print("\n" + "=" * 60)
