#!/usr/bin/env python3
"""
Arquivo de teste para verificar a nova view vw_importacoes_6_meses
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from flask import Flask
from config import Config
from extensions import init_supabase

def test_view_vw_importacoes_6_meses():
    """Testar a view vw_importacoes_6_meses"""
    
    print("=== TESTE DA VIEW vw_importacoes_6_meses ===")
    
    # Criar app Flask para inicializar as extensões
    app = Flask(__name__)
    app.config.from_object(Config)
    
    # Inicializar Supabase
    init_supabase(app)
    
    # Importar depois da inicialização
    from extensions import supabase_admin
    
    try:
        # Verificar se a view existe
        print("1. Testando conexão com a view...")
        
        # Fazer uma query simples para verificar se funciona
        result = supabase_admin.table('vw_importacoes_6_meses').select('*').limit(5).execute()
        
        print(f"✓ View encontrada! Total de registros retornados: {len(result.data)}")
        
        if result.data:
            print("\n2. Estrutura da view (primeiros 5 registros):")
            
            # Mostrar as colunas disponíveis
            first_record = result.data[0]
            print(f"   Colunas disponíveis: {list(first_record.keys())}")
            
            # Mostrar alguns registros de exemplo
            for i, record in enumerate(result.data):
                print(f"\n   Registro {i+1}:")
                print(f"   - Processo: {record.get('ref_unique', 'N/A')}")
                print(f"   - Cliente: {record.get('importador', 'N/A')}")
                print(f"   - Data Abertura: {record.get('data_abertura', 'N/A')}")
                print(f"   - Modal: {record.get('modal', 'N/A')}")
                print(f"   - Mercadoria: {record.get('mercadoria', 'N/A')}")
                print(f"   - Despesas: {record.get('custo_total', 'N/A')}")
        
        # Contar total de registros
        print("\n3. Contando total de registros...")
        count_result = supabase_admin.table('vw_importacoes_6_meses').select('*', count='exact').execute()
        print(f"   Total de registros na view: {count_result.count}")
        
        # Verificar dados por modal
        print("\n4. Distribuição por Modal de Transporte:")
        modals_result = supabase_admin.table('vw_importacoes_6_meses').select('modal').execute()
        
        if modals_result.data:
            from collections import Counter
            modal_counts = Counter([r.get('modal', 'N/A') for r in modals_result.data])
            
            for modal, count in modal_counts.most_common():
                print(f"   - {modal}: {count} registros")
        
        print("\n✓ Teste concluído com sucesso!")
        
    except Exception as e:
        print(f"✗ Erro ao testar a view: {str(e)}")
        import traceback
        traceback.print_exc()
        return False
    
    return True

if __name__ == '__main__':
    success = test_view_vw_importacoes_6_meses()
    
    if success:
        print("\n🎉 A view vw_importacoes_6_meses está funcionando corretamente!")
        print("   Agora você pode acessar /dashboard-v2/ para ver a nova implementação.")
    else:
        print("\n❌ Houve problemas com a view. Verifique se ela foi criada corretamente no banco.")
