"""
Debug endpoint para testar cache do dashboard_v2
"""
from flask import Blueprint, jsonify, session
from routes.auth import login_required, role_required
from services.data_cache import DataCacheService

bp = Blueprint('debug_cache_v2', __name__, url_prefix='/debug-cache-v2')

data_cache = DataCacheService()

@bp.route('/test-cache')
@login_required
@role_required(['admin', 'interno_unique', 'cliente_unique'])
def test_cache():
    """Testar se o cache está funcionando"""
    try:
        user_data = session.get('user', {})
        user_id = user_data.get('id')
        
        # Verificar cache
        cached_data = data_cache.get_cache(user_id, 'dashboard_v2_data')
        
        if cached_data:
            return jsonify({
                'success': True,
                'cache_found': True,
                'total_records': len(cached_data),
                'user_id': user_id,
                'sample_data': cached_data[:2] if len(cached_data) >= 2 else cached_data
            })
        else:
            return jsonify({
                'success': False,
                'cache_found': False,
                'user_id': user_id,
                'message': 'Cache não encontrado'
            })
            
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@bp.route('/force-load')
@login_required
@role_required(['admin', 'interno_unique', 'cliente_unique'])
def force_load():
    """Forçar carregamento dos dados para cache"""
    try:
        from extensions import supabase_admin
        from routes.api import get_user_companies
        
        user_data = session.get('user', {})
        user_id = user_data.get('id')
        user_role = user_data.get('role')
        
        # Query base da view
        query = supabase_admin.table('vw_importacoes_6_meses').select('*')
        
        # Filtrar por empresa se for cliente
        if user_role == 'cliente_unique':
            user_companies = get_user_companies()
            if user_companies:
                query = query.in_('cnpj_importador', user_companies)
        
        # Executar query
        result = query.execute()
        
        if result.data:
            # Armazenar no cache
            data_cache.set_cache(user_id, 'dashboard_v2_data', result.data)
            
            return jsonify({
                'success': True,
                'message': 'Dados carregados e armazenados no cache',
                'total_records': len(result.data),
                'user_id': user_id
            })
        else:
            return jsonify({
                'success': False,
                'message': 'Nenhum dado encontrado na view'
            })
            
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
