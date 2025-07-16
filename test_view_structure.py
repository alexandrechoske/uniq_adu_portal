"""
Script para verificar a estrutura atual da view vw_importacoes_6_meses
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

def check_view_structure():
    """Verificar estrutura da view"""
    try:
        print("[DEBUG] Verificando estrutura da view vw_importacoes_6_meses...")
        
        # Buscar apenas 1 registro para ver as colunas
        result = supabase_admin.table('vw_importacoes_6_meses').select('*').limit(1).execute()
        
        if result.data:
            print(f"[DEBUG] Total de registros na view: {len(result.data)}")
            print(f"[DEBUG] Colunas disponíveis:")
            
            columns = list(result.data[0].keys())
            for i, col in enumerate(columns, 1):
                print(f"  {i:2d}. {col}")
            
            # Verificar se existem as colunas normalizadas
            normalized_columns = ['mercadoria_normalizado', 'urf_entrada_normalizado', 'urf_despacho_normalizado']
            print(f"\n[DEBUG] Colunas normalizadas:")
            for col in normalized_columns:
                exists = col in columns
                print(f"  - {col}: {'✓ EXISTE' if exists else '✗ NÃO EXISTE'}")
            
            # Mostrar exemplo de dados
            print(f"\n[DEBUG] Exemplo de dados:")
            sample = result.data[0]
            print(f"  - mercadoria: {sample.get('mercadoria', 'N/A')}")
            print(f"  - mercadoria_normalizado: {sample.get('mercadoria_normalizado', 'N/A')}")
            print(f"  - urf_entrada: {sample.get('urf_entrada', 'N/A')}")
            print(f"  - urf_entrada_normalizado: {sample.get('urf_entrada_normalizado', 'N/A')}")
            print(f"  - urf_despacho: {sample.get('urf_despacho', 'N/A')}")
            print(f"  - urf_despacho_normalizado: {sample.get('urf_despacho_normalizado', 'N/A')}")
        
        # Verificar total de registros
        total_result = supabase_admin.table('vw_importacoes_6_meses').select('*', count='exact').execute()
        print(f"\n[DEBUG] Total de registros na view: {total_result.count}")
        
    except Exception as e:
        print(f"[DEBUG] Erro: {str(e)}")

if __name__ == "__main__":
    check_view_structure()
