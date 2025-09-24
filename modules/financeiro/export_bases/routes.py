from flask import Blueprint, render_template, session, jsonify, request, make_response
from modules.auth.routes import login_required
from decorators.perfil_decorators import perfil_required
from extensions import supabase_admin
import csv
import io
from datetime import datetime

# Blueprint para Export de Bases Financeiras
export_bases_financeiro_bp = Blueprint(
    'fin_export_bases', 
    __name__,
    url_prefix='/financeiro/export-bases',
    template_folder='templates',
    static_folder='static'
)

# Definição das colunas otimizadas para cada base (nomes reais do banco)
COLUNAS_OTIMIZADAS = {
    'fin_despesa_anual': [
        'data_sincronizacao', 'data', 'centro_resultado', 'categoria', 
        'classe', 'codigo', 'descricao', 'valor'
    ],
    'fin_faturamento_anual': [
        'data_sincronizacao', 'empresa', 'centro_resultado', 'categoria', 
        'classe', 'cliente', 'data', 'fatura', 'id', 'operacao', 'valor'
    ],
    'fin_resultado_anual': [
        'data_sincronizacao', 'centro_resultado', 'categoria', 'classe', 
        'codigo', 'tipo', 'valor'
    ]
}

@export_bases_financeiro_bp.route('/')
@login_required
@perfil_required('financeiro', 'export_bases')
def index():
    """Tela de Exportação de Bases Financeiras"""
    # Log de acesso à página
    print(f"[EXPORT_BASES] Usuário {session.get('user_id')} acessou página de exportação de bases")
    return render_template('export_bases_financeiro.html')

@export_bases_financeiro_bp.route('/api/bases-disponiveis')
@login_required
@perfil_required('financeiro', 'export_bases')
def api_bases_disponiveis():
    """API para listar as bases disponíveis para exportação"""
    try:
        bases = [
            {
                'id': 'fin_despesa_anual',
                'nome': 'Despesas Anuais',
                'descricao': 'Base completa de despesas por ano com todas as categorias',
                'icon': 'mdi-credit-card-minus',
                'total_registros': 0,
                'cor': 'danger'
            },
            {
                'id': 'fin_faturamento_anual',
                'nome': 'Faturamento Anual',
                'descricao': 'Base completa de faturamento por ano com todas as receitas',
                'icon': 'mdi-cash-plus',
                'total_registros': 0,
                'cor': 'success'
            },
            {
                'id': 'fin_resultado_anual',
                'nome': 'Resultado Anual',
                'descricao': 'Base consolidada de resultados (receitas - despesas) por ano',
                'icon': 'mdi-chart-line',
                'total_registros': 0,
                'cor': 'primary'
            }
        ]
        
        # Buscar o total de registros para cada base
        for base in bases:
            try:
                response = supabase_admin.table(base['id']).select('id', count='exact').execute()
                base['total_registros'] = response.count if hasattr(response, 'count') else 0
            except Exception as e:
                print(f"Erro ao buscar registros da base {base['id']}: {e}")
                base['total_registros'] = 0
                
        return jsonify({
            'success': True,
            'data': bases
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Erro ao buscar bases disponíveis: {str(e)}'
        }), 500

@export_bases_financeiro_bp.route('/api/exportar/<base_id>')
@login_required
@perfil_required('financeiro', 'export_bases')
def api_exportar_base(base_id):
    """API para exportar base específica em CSV"""
    try:
        # Validar se a base é válida
        bases_validas = ['fin_despesa_anual', 'fin_faturamento_anual', 'fin_resultado_anual']
        
        if base_id not in bases_validas:
            return jsonify({
                'success': False,
                'message': 'Base não encontrada ou não autorizada'
            }), 400
        
        # Obter colunas otimizadas para esta base
        colunas_base = COLUNAS_OTIMIZADAS.get(base_id, [])
        if not colunas_base:
            return jsonify({
                'success': False,
                'message': 'Configuração de colunas não encontrada para esta base'
            }), 500
        
        # Parâmetros de filtro opcionais
        ano = request.args.get('ano')
        limite = request.args.get('limite', type=int)
        
        # Construir query com apenas as colunas otimizadas
        query = supabase_admin.table(base_id).select(','.join(colunas_base))
        
        # Aplicar filtros se fornecidos
        if ano:
            query = query.gte('data', f'{ano}-01-01').lte('data', f'{ano}-12-31')
            
        if limite:
            query = query.limit(limite)
            
        # Ordenar por data decrescente
        query = query.order('data', desc=True)
        
        # Executar query
        response = query.execute()
        
        if not response.data:
            return jsonify({
                'success': False,
                'message': 'Nenhum dado encontrado para exportação'
            }), 404
        
        # Criar CSV em memória
        output = io.StringIO()
        
        if response.data:
            # Usar as colunas otimizadas definidas para esta base
            writer = csv.DictWriter(output, fieldnames=colunas_base)
            writer.writeheader()
            
            for row in response.data:
                writer.writerow(row)
        
        # Criar resposta de download
        output.seek(0)
        
        # Nome do arquivo com timestamp
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        nome_base = base_id.replace('_', '-')
        filename = f'export-{nome_base}-{timestamp}.csv'
        
        # Configurar resposta para download
        response = make_response(output.getvalue())
        response.headers['Content-Type'] = 'text/csv; charset=utf-8'
        response.headers['Content-Disposition'] = f'attachment; filename={filename}'
        
        # Log da exportação
        print(f"[EXPORT_BASES] Usuário {session.get('user_id')} exportou base {base_id} com {len(response.data)} registros - Filtros: ano={ano}, limite={limite}")
        
        print(f"[EXPORT] Usuário {session.get('user_id')} exportou base {base_id} com {len(response.data)} registros")
        
        return response
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Erro ao exportar base: {str(e)}'
        }), 500

@export_bases_financeiro_bp.route('/api/preview/<base_id>')
@login_required
@perfil_required('financeiro', 'export_bases')
def api_preview_base(base_id):
    """API para preview de dados da base (primeiras 5 linhas)"""
    try:
        # Validar se a base é válida
        bases_validas = ['fin_despesa_anual', 'fin_faturamento_anual', 'fin_resultado_anual']
        
        if base_id not in bases_validas:
            return jsonify({
                'success': False,
                'message': 'Base não encontrada ou não autorizada'
            }), 400
        
        # Obter colunas otimizadas para esta base
        colunas_base = COLUNAS_OTIMIZADAS.get(base_id, [])
        if not colunas_base:
            return jsonify({
                'success': False,
                'message': 'Configuração de colunas não encontrada para esta base'
            }), 500
        
        # Buscar apenas os primeiros 5 registros para preview com colunas otimizadas
        response = supabase_admin.table(base_id) \
            .select(','.join(colunas_base)) \
            .order('data', desc=True) \
            .limit(5) \
            .execute()
        
        # Log de preview
        print(f"[EXPORT_BASES] Usuário {session.get('user_id')} visualizou preview da base {base_id} - {len(response.data) if response.data else 0} registros de amostra")
        
        return jsonify({
            'success': True,
            'data': response.data,
            'total_preview': len(response.data) if response.data else 0
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Erro ao carregar preview: {str(e)}'
        }), 500