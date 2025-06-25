#!/usr/bin/env python3
"""
Script para adicionar os campos faltantes na tabela importacoes_processos
"""

import sys
import os

# Adicionar o diretório pai ao path para importar os módulos
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

try:
    from supabase import create_client
    from config import Config
    
    print("🔧 Adicionando Campos Faltantes - Unique Aduaneira")
    print("=" * 60)
    
    # Criar cliente do Supabase diretamente
    supabase_admin = create_client(Config.SUPABASE_URL, Config.SUPABASE_SERVICE_KEY)
    print("✅ Cliente Supabase criado com sucesso")
    
    # Comandos SQL para adicionar os campos faltantes
    alter_commands = [
        """
        ALTER TABLE public.importacoes_processos 
        ADD COLUMN IF NOT EXISTS data_registro timestamp without time zone;
        """,
        
        """
        ALTER TABLE public.importacoes_processos 
        ADD COLUMN IF NOT EXISTS ref_unique text;
        """,
        
        """
        ALTER TABLE public.importacoes_processos 
        ADD COLUMN IF NOT EXISTS observacoes text;
        """
    ]
    
    print("\n📝 Adicionando campos faltantes...")
    
    for i, command in enumerate(alter_commands, 1):
        try:
            print(f"🔄 Executando comando {i}...")
            
            # Executar via RPC function (se disponível) ou via SQL direto
            try:
                # Tentar usando a função RPC
                result = supabase_admin.rpc('execute_sql', {'sql_query': command.strip()}).execute()
                print(f"✅ Comando {i} executado via RPC")
            except Exception as rpc_error:
                print(f"⚠️ RPC falhou: {str(rpc_error)}")
                # Se RPC não funcionar, tentar método alternativo
                print("💡 Tentando método alternativo...")
                # Para Supabase, podemos tentar adicionar via PostgreSQL REST API
                print(f"⚠️ Comando {i} precisa ser executado manualmente no Supabase Dashboard")
                print(f"📝 SQL: {command.strip()}")
                
        except Exception as e:
            print(f"❌ Erro no comando {i}: {str(e)}")
    
    print("\n🔍 Verificando se os campos foram adicionados...")
    
    try:
        # Testar se os novos campos existem agora
        test_result = supabase_admin.table('importacoes_processos').select('data_registro', 'ref_unique', 'observacoes').limit(1).execute()
        
        if test_result.data:
            print("✅ Novos campos adicionados com sucesso!")
            
            # Mostrar a estrutura atualizada
            full_structure = supabase_admin.table('importacoes_processos').select('*').limit(1).execute()
            if full_structure.data:
                print("\n📋 Estrutura completa da tabela:")
                for field in sorted(full_structure.data[0].keys()):
                    print(f"   - {field}")
        else:
            print("⚠️ Não foi possível verificar os novos campos")
            
    except Exception as e:
        print(f"❌ Erro ao verificar campos: {str(e)}")
        print("\n💡 INSTRUÇÕES MANUAIS:")
        print("   Acesse o Supabase Dashboard > SQL Editor e execute:")
        print("   " + "="*50)
        for command in alter_commands:
            print(f"   {command.strip()}")
        print("   " + "="*50)
    
    print("\n🎉 Processo concluído!")
    
except Exception as e:
    print(f"❌ Erro geral: {str(e)}")

print("\n" + "=" * 60)
