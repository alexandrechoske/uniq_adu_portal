from flask import Blueprint, jsonify, request
from extensions import supabase
from routes.auth import login_required, role_required

bp = Blueprint('api', __name__, url_prefix='/api')

@bp.route('/search_companies', methods=['GET'])
@login_required
def search_companies():
    try:
        print("\n[DEBUG] ===== /search_companies =====")
        print(f"[DEBUG] Request args: {request.args}")
        print(f"[DEBUG] Request path: {request.path}")
        print(f"[DEBUG] Request full path: {request.full_path}")
        
        term = request.args.get('term', '').strip()
        print(f"[DEBUG] Original search term: {term}")
        
        if len(term) < 2:
            print("[DEBUG] Term too short, returning empty list")
            return jsonify([])
            
        # Clean CNPJ by removing formatting
        clean_term = term.replace('.', '').replace('/', '').replace('-', '')
        print(f"[DEBUG] Cleaned search term: {clean_term}")
        
        # Primeiro tenta busca exata por CNPJ
        result = supabase.table('operacoes_aduaneiras')\
            .select('cliente_cpf_cnpj, cliente_razao_social')\
            .or_(f'cliente_cpf_cnpj.eq.{term},cliente_cpf_cnpj.eq.{clean_term}')\
            .execute()
            
        # Se não encontrar, tenta busca por contém
        if not result.data:
            result = supabase.table('operacoes_aduaneiras')\
                .select('cliente_cpf_cnpj, cliente_razao_social')\
                .or_(f'cliente_razao_social.ilike.%{term}%,cliente_cpf_cnpj.ilike.%{clean_term}%')\
                .execute()
                
        print(f"[DEBUG] Raw result: {result.data}")
        
        # Remove duplicatas e formata resultado
        companies = {}
        for row in result.data:
            cnpj = row['cliente_cpf_cnpj']
            if cnpj:
                # Clean stored CNPJ for comparison
                clean_cnpj = cnpj.replace('.', '').replace('/', '').replace('-', '')
                if clean_cnpj not in companies:
                    companies[clean_cnpj] = {
                        'cnpj': cnpj,  # Keep formatted CNPJ for display
                        'razao_social': row['cliente_razao_social']
                    }
        
        response_data = list(companies.values())
        print(f"[DEBUG] Formatted response: {response_data}")
        return jsonify(response_data)

    except Exception as e:
        print(f"[DEBUG] Error searching companies: {str(e)}")
        import traceback
        print("[DEBUG] Stack trace:", traceback.format_exc())
        return jsonify({'error': str(e)}), 500

@bp.route('/company_info/<cnpj>')
@login_required
def get_company_info(cnpj):
    try:
        print("\n[DEBUG] ===== /company_info/{cnpj} =====")
        print(f"[DEBUG] CNPJ requested: {cnpj}")
        
        cnpj = cnpj.strip()
        print(f"[DEBUG] Searching for CNPJ: {cnpj}")
        
        result = supabase.table('operacoes_aduaneiras')\
            .select('cliente_cpf_cnpj, cliente_razao_social')\
            .eq('cliente_cpf_cnpj', cnpj)\
            .limit(1)\
            .execute()
        
        print(f"[DEBUG] Raw result: {result.data}")
        
        if result.data:
            response_data = {
                'cnpj': result.data[0]['cliente_cpf_cnpj'],
                'razao_social': result.data[0]['cliente_razao_social']
            }
            print(f"[DEBUG] Returning data: {response_data}")
            return jsonify(response_data)
            
        print("[DEBUG] No data found")
        return jsonify(None)
        
    except Exception as e:
        print(f"[DEBUG] Error getting company info: {str(e)}")
        import traceback
        print("[DEBUG] Stack trace:", traceback.format_exc())
        return jsonify({'error': str(e)}), 500

@bp.route('/get_user_companies/<user_id>', methods=['GET'])
@login_required
def get_user_companies(user_id):
    try:
        result = supabase.table('clientes_agentes')\
            .select('empresa')\
            .eq('user_id', user_id)\
            .execute()
            
        # Converter lista de empresas se existir
        empresas = []
        if result.data and result.data[0].get('empresa'):
            raw_empresas = result.data[0]['empresa']
            if isinstance(raw_empresas, str):
                empresas = raw_empresas.split(',')
            else:
                empresas = raw_empresas
        
        return jsonify({'companies': empresas})
    except Exception as e:
        print(f"Error fetching user companies: {str(e)}")
        return jsonify({'error': 'Failed to fetch companies'}), 500
