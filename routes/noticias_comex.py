"""API de notícias COMEX - Endpoints para galeria de notícias e indicadores econômicos."""
import os
from datetime import datetime
from typing import Any, Dict, List, Optional

from flask import Blueprint, jsonify, request

from extensions import supabase_admin

bp = Blueprint('noticias_comex', __name__)


def _check_bypass() -> bool:
    """Valida se a requisição possui API bypass válido."""
    api_bypass_key = os.getenv('API_BYPASS_KEY')
    return bool(api_bypass_key and request.headers.get('X-API-Key') == api_bypass_key)


def _serialize_news(record: Dict[str, Any]) -> Dict[str, Any]:
    """Converte registro do Supabase para o formato esperado pelo frontend."""
    created_at = record.get('created_at')
    if isinstance(created_at, datetime):
        created_at_iso = created_at.isoformat()
    else:
        created_at_iso = created_at

    return {
        'id': record.get('id'),
        'titulo': record.get('title') or '',
        'resumo': record.get('summary') or '',
        'categoria': record.get('source') or 'COMEX',
        'fonte': record.get('source') or 'COMEX',
        'link': record.get('link') or '',
        'imagem_url': record.get('imageUrl') or record.get('image_url') or '',
        'data_publicacao': record.get('publishedAt') or created_at_iso,
        'created_at': created_at_iso,
    }


def _fetch_news(limit: int, fonte: Optional[str] = None) -> List[Dict[str, Any]]:
    """Busca notícias no Supabase ordenadas por ID decrescente (mais recentes primeiro)."""
    query = supabase_admin.table('comex_news').select('*').eq('empresa', 'Unique').order('id', desc=True)

    if fonte:
        query = query.eq('source', fonte)

    response = query.limit(limit).execute()

    registros = response.data or []
    return [_serialize_news(record) for record in registros]


def _fetch_categories() -> List[str]:
    """Retorna lista de fontes/categorias disponíveis."""
    response = supabase_admin.table('comex_news').select('source').eq('empresa', 'Unique').execute()

    fontes = {row.get('source') or 'COMEX' for row in (response.data or [])}
    return sorted(fontes)


@bp.route('/api/noticias-comex', methods=['GET'])
def get_noticias():
    """
    Retorna lista de notícias COMEX
    
    Query params:
    - limit: número máximo de notícias (padrão: 10)
    - categoria / source: filtrar por fonte específica
    """
    try:
        if not _check_bypass():
            return jsonify({
                'error': 'Acesso não autorizado',
                'message': 'X-API-Key inválida ou não fornecida'
            }), 401

        # Obter parâmetros
        limit = max(1, min(request.args.get('limit', 10, type=int), 50))
        fonte = request.args.get('source') or request.args.get('categoria')

        noticias = _fetch_news(limit=limit, fonte=fonte)

        return jsonify({
            'success': True,
            'total': len(noticias),
            'noticias': noticias,
            'timestamp': datetime.now().isoformat()
        }), 200

    except Exception as e:
        print(f"❌ Erro ao buscar notícias: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Erro interno do servidor',
            'message': str(e)
        }), 500


@bp.route('/api/noticias-comex/<int:noticia_id>', methods=['GET'])
def get_noticia_detalhes(noticia_id):
    """Retorna detalhes de uma notícia específica"""
    try:
        if not _check_bypass():
            return jsonify({
                'error': 'Acesso não autorizado'
            }), 401

        response = (
            supabase_admin
            .table('comex_news')
            .select('*')
            .eq('empresa', 'Unique')
            .eq('id', noticia_id)
            .limit(1)
            .execute()
        )
        data = response.data or []
        if not data:
            return jsonify({
                'success': False,
                'error': 'Notícia não encontrada'
            }), 404

        return jsonify({
            'success': True,
            'noticia': _serialize_news(data[0])
        }), 200

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@bp.route('/api/noticias-comex/<int:noticia_id>/analytics', methods=['POST'])
def track_news_click(noticia_id):
    """
    Registra analytics de clique em notícia COMEX
    
    Body esperado:
    {
        "user_id": "uuid",  # Opcional - se não existir em auth.users, será NULL
        "user_email": "email@example.com",
        "user_name": "Nome do Usuário",
        "user_role": "admin",
        "news_title": "Título da Notícia",
        "news_source": "COMEX",
        "session_id": "session_id"
    }
    """
    try:
        if not _check_bypass():
            return jsonify({
                'error': 'Acesso não autorizado'
            }), 401

        data = request.get_json() or {}
        
        # Verificar se user_id existe em auth.users, senão usar NULL
        user_id = data.get('user_id')
        if user_id:
            try:
                # Verificar se o user_id existe
                user_check = supabase_admin.table('auth.users').select('id').eq('id', user_id).execute()
                if not user_check.data:
                    # User não existe, usar NULL
                    user_id = None
            except Exception as e:
                # Em caso de erro na verificação, usar NULL
                print(f"⚠️ Erro ao verificar user_id: {str(e)}")
                user_id = None
        
        # Preparar dados para access_logs
        log_entry = {
            'user_id': user_id,  # Pode ser NULL
            'user_email': data.get('user_email'),
            'user_name': data.get('user_name'),
            'user_role': data.get('user_role'),
            'action_type': 'news_click',
            'page_url': f'/menu?news_id={noticia_id}',
            'page_name': f'Notícia COMEX: {data.get("news_title", "")[:100]}',
            'module_name': 'menu',
            'ip_address': request.remote_addr,
            'user_agent': request.headers.get('User-Agent'),
            'session_id': data.get('session_id'),
            'success': True,
        }

        # Inserir no access_logs
        supabase_admin.table('access_logs').insert(log_entry).execute()

        return jsonify({
            'success': True,
            'message': 'Analytics registrado com sucesso',
            'news_id': noticia_id
        }), 200

    except Exception as e:
        print(f"❌ Erro ao registrar analytics: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Erro ao registrar analytics',
            'message': str(e)
        }), 500


@bp.route('/api/noticias-comex/categorias', methods=['GET'])
def get_categorias():
    """Retorna lista de categorias disponíveis"""
    try:
        if not _check_bypass():
            return jsonify({
                'error': 'Acesso não autorizado'
            }), 401

        categorias = _fetch_categories()

        return jsonify({
            'success': True,
            'categorias': categorias,
            'total': len(categorias)
        }), 200

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@bp.route('/api/comex-indicators', methods=['GET'])
def get_comex_indicators():
    """Retorna indicadores econômicos e comerciais do COMEX"""
    try:
        if not _check_bypass():
            return jsonify({
                'error': 'Acesso não autorizado'
            }), 401

        response = (
            supabase_admin
            .table('comex_ptaxes')
            .select('*')
            .order('created_at', desc=True)
            .limit(1)
            .execute()
        )
        
        data = response.data or []
        if not data:
            return jsonify({
                'success': False,
                'error': 'Dados não encontrados'
            }), 404

        indicators = data[0]
        
        return jsonify({
            'success': True,
            'indicators': {
                'selic_meta': indicators.get('selic_meta'),
                'selic_data_reuniao': indicators.get('selic_data_reuniao'),
                'ipca_acumulada_ano': indicators.get('ipca_acumulada_ano'),
                'ipca_12_meses': indicators.get('ipca_12_meses'),
                'ipca_meta': indicators.get('ipca_meta'),
                'dolar_compra': indicators.get('dolar_compra'),
                'dolar_venda': indicators.get('dolar_venda'),
                'euro_compra': indicators.get('euro_compra'),
                'euro_venda': indicators.get('euro_venda'),
                'expo_bi': indicators.get('expo_bi'),
                'impo_bi': indicators.get('impo_bi'),
                'saldo_comex': indicators.get('saldo_comex'),
            }
        }), 200

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
