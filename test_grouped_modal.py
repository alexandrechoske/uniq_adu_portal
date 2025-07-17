from flask import Blueprint, jsonify, request
from extensions import supabase_admin
import pandas as pd

bp = Blueprint('test_grouped_modal', __name__)

@bp.route('/test-grouped-modal-data')
def test_grouped_modal_data():
    """Teste direto para verificar dados do gráfico agrupado modal"""
    try:
        print("[TEST] Iniciando teste do gráfico agrupado modal...")
        
        # Obter dados direto do Supabase
        query = supabase_admin.table('vw_importacoes_6_meses').select('*')
        result = query.limit(500).execute()
        
        if not result.data:
            return jsonify({
                'success': False,
                'error': 'Nenhum dado encontrado',
                'data': {}
            })
        
        print(f"[TEST] Total de registros: {len(result.data)}")
        
        df = pd.DataFrame(result.data)
        
        # Verificar colunas
        print(f"[TEST] Colunas disponíveis: {df.columns.tolist()}")
        
        # Verificar se as colunas existem
        has_modal = 'modal' in df.columns
        has_custo = 'custo_total' in df.columns
        has_ref = 'ref_unique' in df.columns
        
        print(f"[TEST] Colunas: modal={has_modal}, custo_total={has_custo}, ref_unique={has_ref}")
        
        if has_modal:
            print(f"[TEST] Valores únicos de modal: {df['modal'].unique()}")
            print(f"[TEST] Contagem por modal: {df['modal'].value_counts().to_dict()}")
        
        if has_custo:
            print(f"[TEST] Valores de custo_total (primeiros 10): {df['custo_total'].head(10).tolist()}")
            print(f"[TEST] Soma total de custo_total: {df['custo_total'].sum()}")
            print(f"[TEST] Valores nulos em custo_total: {df['custo_total'].isnull().sum()}")
        
        if has_ref:
            print(f"[TEST] Valores de ref_unique (primeiros 5): {df['ref_unique'].head(5).tolist()}")
        
        # Tentar fazer o groupby se as colunas existirem
        result_data = {}
        
        if has_modal and has_custo and has_ref:
            try:
                modal_group = df.groupby('modal').agg({
                    'ref_unique': 'count',
                    'custo_total': 'sum'
                }).reset_index()
                
                print(f"[TEST] Resultado do groupby: {modal_group.to_dict('records')}")
                
                result_data = {
                    'labels': modal_group['modal'].tolist(),
                    'processes': modal_group['ref_unique'].tolist(),
                    'values': modal_group['custo_total'].tolist()
                }
                
                print(f"[TEST] Dados finais formatados: {result_data}")
                
            except Exception as e:
                print(f"[TEST] Erro no groupby: {str(e)}")
                result_data = {'error': str(e)}
        
        return jsonify({
            'success': True,
            'columns': df.columns.tolist(),
            'has_modal': has_modal,
            'has_custo': has_custo,
            'has_ref': has_ref,
            'total_records': len(df),
            'data': result_data
        })
        
    except Exception as e:
        print(f"[TEST] Erro: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e),
            'data': {}
        })

# Registrar o blueprint temporariamente
if __name__ == '__main__':
    from flask import Flask
    app = Flask(__name__)
    app.register_blueprint(bp)
