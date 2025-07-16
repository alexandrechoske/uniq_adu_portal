"""
Teste para debug da view vw_importacoes_6_meses
"""
import os
from dotenv import load_dotenv
from supabase import create_client

# Carregar variáveis de ambiente
load_dotenv()

# Configurar Supabase
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY")

supabase_admin = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

def test_view_full():
    """Testar a view completa"""
    try:
        print("[DEBUG] Testando view completa...")
        
        # Query completa sem filtros
        result = supabase_admin.table('vw_importacoes_6_meses').select('*').execute()
        
        print(f"[DEBUG] Total de registros na view: {len(result.data)}")
        
        if result.data:
            print(f"[DEBUG] Colunas disponíveis: {list(result.data[0].keys())}")
            
            # Verificar distribuição por modal
            modals = {}
            for row in result.data:
                modal = row.get('modal', 'N/A')
                modals[modal] = modals.get(modal, 0) + 1
            
            print(f"[DEBUG] Distribuição por modal: {modals}")
            
            # Verificar alguns CNPJs
            cnpjs = set()
            for row in result.data[:10]:
                cnpjs.add(row.get('cnpj_importador', 'N/A'))
            
            print(f"[DEBUG] Primeiros 10 CNPJs únicos: {list(cnpjs)}")
            
            # Testar com filtro de usuário admin (como no dashboard_v2)
            print("\n[DEBUG] Testando com possível filtro de admin...")
            
            # Verificar se há filtro por data ou outros campos
            print(f"[DEBUG] Exemplo de registro:")
            print(f"  - ref_unique: {result.data[0].get('ref_unique')}")
            print(f"  - importador: {result.data[0].get('importador')}")
            print(f"  - data_abertura: {result.data[0].get('data_abertura')}")
            print(f"  - modal: {result.data[0].get('modal')}")
            print(f"  - cnpj_importador: {result.data[0].get('cnpj_importador')}")
            
    except Exception as e:
        print(f"[DEBUG] Erro: {str(e)}")

if __name__ == "__main__":
    test_view_full()
