#!/usr/bin/env python3
"""
Script para aplicar o DDL das novas tabelas no Supabase
Execute este script para criar as tabelas importacoes_processos e importacoes_despesas
"""

import os
import sys
from extensions import supabase_admin
from config import Config

def apply_ddl():
    """
    Aplica o DDL das novas tabelas no Supabase
    """
    
    # DDL para criar/recriar as tabelas
    ddl_commands = [
        """
        -- Recria a tabela principal com todos os campos novos
        DROP TABLE IF EXISTS public.importacoes_processos CASCADE;
        """,
        
        """
        CREATE TABLE public.importacoes_processos (
          id bigint NOT NULL,
          numero text NULL,
          data_abertura timestamp without time zone NULL,
          local_embarque text NULL,
          data_embarque timestamp without time zone NULL,
          di_modalidade_despacho text NULL,
          diduimp_canal text NULL,
          via_transporte_descricao text NULL,
          previsao_chegada timestamp without time zone NULL,
          data_chegada timestamp without time zone NULL,
          carga_status text NULL,
          status_doc text NULL,
          situacao text NULL,
          tipo_operacao text NULL,
          resumo_mercadoria text NULL,
          cliente_cpfcnpj text NULL,
          cliente_razaosocial text NULL,
          total_vmle_real numeric(15,2) NULL,
          total_vmcv_real numeric(15,2) NULL,
          referencias jsonb NULL,
          armazens jsonb NULL,
          observacoes text NULL,
          ref_unique text NULL,
          data_registro timestamp without time zone NULL,
          created_at timestamp with time zone NULL DEFAULT now(),
          updated_at timestamp with time zone NULL DEFAULT now(),
          CONSTRAINT importacoes_processos_pkey PRIMARY KEY (id)
        ) TABLESPACE pg_default;
        """,
        
        """
        -- Cria a tabela de despesas (relacionamento 1:N)
        CREATE TABLE public.importacoes_despesas (
          id bigint NOT NULL,
          processo_id bigint NOT NULL,
          tipo integer NULL,
          valor_bruto numeric(15,2) NULL,
          valor_liquido numeric(15,2) NULL,
          valor_real numeric(15,2) NULL,
          descricao text NULL,
          situacao_descricao text NULL,
          forma_pagamento text NULL,
          created_at timestamp with time zone NULL DEFAULT now(),
          updated_at timestamp with time zone NULL DEFAULT now(),
          CONSTRAINT importacoes_despesas_pkey PRIMARY KEY (id),
          CONSTRAINT importacoes_despesas_processo_id_fkey 
            FOREIGN KEY (processo_id) REFERENCES public.importacoes_processos(id) 
            ON DELETE CASCADE
        ) TABLESPACE pg_default;
        """,
        
        """
        -- Cria índices para melhor performance
        CREATE INDEX IF NOT EXISTS idx_importacoes_processos_numero ON public.importacoes_processos(numero);
        """,
        
        """
        CREATE INDEX IF NOT EXISTS idx_importacoes_processos_cliente_cpfcnpj ON public.importacoes_processos(cliente_cpfcnpj);
        """,
        
        """
        CREATE INDEX IF NOT EXISTS idx_importacoes_processos_situacao ON public.importacoes_processos(situacao);
        """,
        
        """
        CREATE INDEX IF NOT EXISTS idx_importacoes_despesas_processo_id ON public.importacoes_despesas(processo_id);
        """,
        
        """
        CREATE INDEX IF NOT EXISTS idx_importacoes_despesas_situacao ON public.importacoes_despesas(situacao_descricao);
        """
    ]
    
    print("🚀 Iniciando aplicação do DDL no Supabase...")
    
    try:
        for i, command in enumerate(ddl_commands, 1):
            print(f"📝 Executando comando {i}/{len(ddl_commands)}...")
            
            # Usar supabase_admin para executar SQL direto
            result = supabase_admin.rpc('execute_sql', {'sql_query': command.strip()}).execute()
            
            if result.data:
                print(f"✅ Comando {i} executado com sucesso")
            else:
                print(f"⚠️ Comando {i} executado (sem retorno de dados)")
        
        print("🎉 DDL aplicado com sucesso!")
        print("✅ Tabela 'importacoes_processos' criada/atualizada")
        print("✅ Tabela 'importacoes_despesas' criada")
        print("✅ Índices criados")
        
        return True
        
    except Exception as e:
        print(f"❌ Erro ao aplicar DDL: {str(e)}")
        return False

def verify_tables():
    """
    Verifica se as tabelas foram criadas corretamente
    """
    print("\n🔍 Verificando se as tabelas foram criadas...")
    
    try:
        # Verificar tabela importacoes_processos
        result = supabase_admin.table('importacoes_processos').select('count', count='exact').limit(1).execute()
        print(f"✅ Tabela 'importacoes_processos' encontrada (count: {result.count})")
        
        # Verificar tabela importacoes_despesas  
        result = supabase_admin.table('importacoes_despesas').select('count', count='exact').limit(1).execute()
        print(f"✅ Tabela 'importacoes_despesas' encontrada (count: {result.count})")
        
        return True
        
    except Exception as e:
        print(f"❌ Erro ao verificar tabelas: {str(e)}")
        return False

def main():
    """
    Função principal
    """
    print("🔧 Script de Aplicação do DDL - Unique Aduaneira")
    print("=" * 50)
    
    # Verificar configurações
    if not hasattr(Config, 'SUPABASE_URL') or not Config.SUPABASE_URL:
        print("❌ SUPABASE_URL não configurado")
        return False
        
    if not hasattr(Config, 'SUPABASE_SERVICE_KEY') or not Config.SUPABASE_SERVICE_KEY:
        print("❌ SUPABASE_SERVICE_KEY não configurado")
        return False
    
    print(f"🔗 Conectando ao Supabase: {Config.SUPABASE_URL}")
    
    # Aplicar DDL
    if not apply_ddl():
        print("❌ Falha ao aplicar DDL")
        return False
    
    # Verificar tabelas
    if not verify_tables():
        print("❌ Falha ao verificar tabelas")
        return False
    
    print("\n🎉 Processo concluído com sucesso!")
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
