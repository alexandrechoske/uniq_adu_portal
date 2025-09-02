from flask import Blueprint, render_template, request, session, jsonify, Response
from datetime import datetime, timedelta
from modules.auth.routes import login_required
from extensions import supabase_admin
import csv
import io
import re
import os

# Blueprint acessível por todas as roles
export_relatorios_bp = Blueprint(
    'export_relatorios',
    __name__,
    url_prefix='/export_relatorios',
    template_folder='templates',
    static_folder='static',
    static_url_path='/export_relatorios/static'
)

@export_relatorios_bp.route('/')
@login_required
def index():
    """Tela inicial de exportação de relatórios (processos > 6 meses).
    Primeira etapa: apenas layout base e endpoint para futura busca.
    """
    user = session.get('user', {})
    user_companies = user.get('user_companies') or []
    user_role = user.get('role', '')
    
    # Para clientes, mostrar os CNPJs que eles têm acesso
    security_info = {
        'role': user_role,
        'companies': user_companies,
        'has_companies': len(user_companies) > 0
    }
    
    return render_template('export_relatorios/export_relatorios.html', 
                         user=user, 
                         security_info=security_info)

@export_relatorios_bp.route('/api/processos_antigos')
@login_required
def api_processos_antigos():
    """Endpoint inicial para futura extração de processos antigos (> 6 meses).
    Nesta primeira etapa retornamos apenas um payload mock para validar a página.
    """
    try:
        cutoff_date = (datetime.now() - timedelta(days=180)).strftime('%Y-%m-%d')
        return jsonify({
            'success': True,
            'message': 'Endpoint inicial pronto. Implementação de consulta será adicionada.',
            'cutoff_date': cutoff_date,
            'data': []
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# ---------------------- NOVA IMPLEMENTAÇÃO DE BUSCA E EXPORTAÇÃO ----------------------

TABLE_COLUMNS = [
    'ref_unique','ref_importador','cnpj_importador','importador','modal','container','data_embarque',
    'data_chegada','transit_time_real','urf_despacho','exportador_fornecedor',
    'numero_di','data_registro','canal','data_desembaraco','mercadoria','status_processo',
    'peso_bruto','valor_fob_real','valor_cif_real','data_abertura','status_macro','status_macro_sistema','data_fechamento'
]

DATE_FIELDS = [c for c in TABLE_COLUMNS if c.startswith('data_')]

def parse_br_date(date_str):
    """Converte data em formato DD/MM/YYYY para datetime; retorna None se inválida."""
    if not date_str or not isinstance(date_str, str):
        return None
    date_str = date_str.strip()
    # Aceitar já formato ISO
    try:
        if re.match(r'^\d{4}-\d{2}-\d{2}$', date_str):
            return datetime.strptime(date_str, '%Y-%m-%d')
    except Exception:
        pass
    try:
        return datetime.strptime(date_str, '%d/%m/%Y')
    except Exception:
        return None

def build_base_query(user):
    """Constrói query base com segurança obrigatória por CNPJ do usuário."""
    q = supabase_admin.table('importacoes_processos_aberta').select('*')
    
    # SEGURANÇA OBRIGATÓRIA: Sempre filtrar por CNPJs do usuário
    user_role = user.get('role', '')
    user_companies = user.get('user_companies') or []
    perfil_principal = user.get('perfil_principal', '')
    is_admin_operacao = perfil_principal == 'admin_operacao'
    
    # Para clientes, SEMPRE restringir aos CNPJs associados
    if user_role == 'cliente_unique':
        if user_companies:
            print(f"[EXPORT_REL][SECURITY] Cliente {user.get('id')} restrito aos CNPJs: {user_companies}")
            q = q.in_('cnpj_importador', user_companies)
        else:
            # Se não tem empresas associadas, retorna query vazia por segurança
            print(f"[EXPORT_REL][SECURITY] Cliente {user.get('id')} sem CNPJs - bloqueando acesso")
            q = q.limit(0)
    
    # Para usuários internos com perfil admin_operacao, permitir ver todos os dados
    elif user_role == 'interno_unique' and is_admin_operacao:
        print(f"[EXPORT_REL][SECURITY] Usuário admin_operacao {user.get('id')} - acesso completo a todos os dados")
    
    # Para usuários internos normais, aplicar filtro se tiverem CNPJs específicos
    elif user_role == 'interno_unique' and user_companies:
        print(f"[EXPORT_REL][SECURITY] Usuário interno {user.get('id')} filtrado por CNPJs: {user_companies}")
        q = q.in_('cnpj_importador', user_companies)
    
    # Admins podem acessar todos os dados (sem filtro adicional)
    elif user_role == 'admin':
        print(f"[EXPORT_REL][SECURITY] Admin {user.get('id')} - acesso completo")
    
    else:
        # Usuários sem role definida ou roles desconhecidas = acesso negado
        print(f"[EXPORT_REL][SECURITY] Usuário {user.get('id')} com role '{user_role}' - acesso negado")
        q = q.limit(0)
    
    return q

def apply_query_filters(q, filters: dict, user: dict):
    """Aplica filtros adicionais, mas mantém a segurança de CNPJs do usuário."""
    import re
    user_role = user.get('role', '')
    user_companies = user.get('user_companies') or []
    
    # Campos que suportam busca múltipla (separados por vírgula)
    multi_search_fields = ['ref_importador', 'ref_unique', 'numero_di']
    
    # Campos que faremos server-side (igualdade ou like simples)
    for col, val in filters.items():
        if col in ['date_start','date_end','older_than_days','page','page_size','export']:
            continue
        if val is None or val == '':
            continue
            
        # SEGURANÇA CRÍTICA: Ignorar filtro de cnpj_importador do usuário
        # A segurança já foi aplicada em build_base_query()
        if col == 'cnpj_importador':
            print(f"[EXPORT_REL][SECURITY] Ignorando filtro cnpj_importador do usuário {user.get('id')} - segurança já aplicada")
            continue
        
        # Tratamento para campos de busca múltipla
        if col in multi_search_fields and isinstance(val, str):
            # Separar por vírgula e limpar espaços
            values = [v.strip() for v in val.split(',') if v.strip()]
            if len(values) > 1:
                # Múltiplos valores: usar filtro OR com in_()
                print(f"[EXPORT_REL][MULTI_SEARCH] Campo {col} com {len(values)} valores: {values}")
                q = q.in_(col, values)
                continue
            elif len(values) == 1:
                # Um único valor após limpeza
                val = values[0]
            
        # Tratamento numérico
        if col in ['transit_time_real','peso_bruto','valor_fob_real','valor_cif_real','firebird_di_codigo']:
            try:
                float(val)  # valida
                q = q.eq(col, val)
            except ValueError:
                pass
        else:
            # Usar ilike para texto quando cabível (evitar wildcard se usuário não fornecer)
            if isinstance(val, str) and ('%' in val or len(val) > 3):
                q = q.ilike(col, val if '%' in val else f"%{val}%")
            else:
                q = q.eq(col, val)
    return q

def validate_user_data_access(rows, user):
    """Validação adicional: verifica se todos os registros pertencem aos CNPJs do usuário.
    Esta é uma camada extra de segurança contra bypass de API.
    """
    user_role = user.get('role', '')
    user_companies = user.get('user_companies') or []
    perfil_principal = user.get('perfil_principal', '')
    is_admin_operacao = perfil_principal == 'admin_operacao'
    
    # Para clientes, verificar se TODOS os registros pertencem aos CNPJs permitidos
    if user_role == 'cliente_unique':
        if not user_companies:
            print(f"[EXPORT_REL][SECURITY_VALIDATION] Cliente {user.get('id')} sem CNPJs - removendo todos os registros")
            return []
        
        valid_rows = []
        blocked_count = 0
        
        for row in rows:
            row_cnpj = row.get('cnpj_importador', '')
            if row_cnpj in user_companies:
                valid_rows.append(row)
            else:
                blocked_count += 1
                print(f"[EXPORT_REL][SECURITY_VALIDATION] Bloqueado acesso ao CNPJ {row_cnpj} para cliente {user.get('id')}")
        
        if blocked_count > 0:
            print(f"[EXPORT_REL][SECURITY_VALIDATION] Total de {blocked_count} registros bloqueados por segurança")
        
        return valid_rows
    
    # Para usuários internos com perfil admin_operacao, permitir ver todos os dados
    elif user_role == 'interno_unique' and is_admin_operacao:
        print(f"[EXPORT_REL][SECURITY_VALIDATION] Usuário admin_operacao {user.get('id')} - acesso a todos os registros")
        return rows
    
    # Para usuários internos com CNPJs específicos, aplicar mesma validação
    elif user_role == 'interno_unique' and user_companies:
        valid_rows = []
        for row in rows:
            row_cnpj = row.get('cnpj_importador', '')
            if row_cnpj in user_companies:
                valid_rows.append(row)
        return valid_rows
    
    # Admins podem ver todos os dados
    elif user_role == 'admin':
        return rows
    
    # Outras roles = sem acesso
    else:
        print(f"[EXPORT_REL][SECURITY_VALIDATION] Role '{user_role}' não autorizada - removendo todos os registros")
        return []

def post_fetch_filter(rows, filters):
    """Filtragem em Python para datas (formato texto). Sem recorte automático se usuário não define intervalo."""
    date_start = filters.get('date_start')
    date_end = filters.get('date_end')
    # Identificadores que devem permitir ignorar o recorte padrão de 6 meses quando usados
    identifier_filters = ['ref_unique','numero_di','ref_importador','container']
    has_identifier = any(filters.get(f) for f in identifier_filters)

    dt_start = parse_br_date(date_start) if date_start else None
    dt_end = parse_br_date(date_end) if date_end else None
    cutoff = None  # Sem cutoff automático agora

    def row_pass(r):
        raw = r.get('data_abertura') or r.get('data_registro')
        dt = parse_br_date(raw)
        if cutoff and dt:
            if dt > cutoff:
                return False
        if dt_start and dt and dt < dt_start:
            return False
        if dt_end and dt and dt > dt_end:
            return False
        return True

    if dt_start or dt_end:
        before = len(rows)
        rows = [r for r in rows if row_pass(r)]
        after = len(rows)
        print(f"[EXPORT_REL][FILTRO_DATAS] has_identifier={has_identifier} dt_start={dt_start} dt_end={dt_end} antes={before} depois={after}")
    return rows
    """Filtragem em Python para datas (formato texto). Sem recorte automático se usuário não define intervalo."""
    date_start = filters.get('date_start')
    date_end = filters.get('date_end')
    # Identificadores que devem permitir ignorar o recorte padrão de 6 meses quando usados
    identifier_filters = ['ref_unique','numero_di','ref_importador','container']
    has_identifier = any(filters.get(f) for f in identifier_filters)

    dt_start = parse_br_date(date_start) if date_start else None
    dt_end = parse_br_date(date_end) if date_end else None
    cutoff = None  # Sem cutoff automático agora

    def row_pass(r):
        raw = r.get('data_abertura') or r.get('data_registro')
        dt = parse_br_date(raw)
        if cutoff and dt:
            if dt > cutoff:
                return False
        if dt_start and dt and dt < dt_start:
            return False
        if dt_end and dt and dt > dt_end:
            return False
        return True

    if dt_start or dt_end:
        before = len(rows)
        rows = [r for r in rows if row_pass(r)]
        after = len(rows)
        print(f"[EXPORT_REL][FILTRO_DATAS] has_identifier={has_identifier} dt_start={dt_start} dt_end={dt_end} antes={before} depois={after}")
    return rows

def paginate(rows, page, page_size):
    total = len(rows)
    start = (page - 1) * page_size
    end = start + page_size
    return rows[start:end], total

def extract_filters(req_json):
    filters = {}
    for col in TABLE_COLUMNS:
        if col in req_json:
            filters[col] = req_json.get(col)
    # Extras
    for extra in ['date_start','date_end','older_than_days','page','page_size','export']:
        if extra in req_json:
            filters[extra] = req_json.get(extra)
    return filters

@export_relatorios_bp.route('/api/search', methods=['POST'])
@login_required
def search_processos():
    """Executa busca com filtros e retorna JSON paginado."""
    started_at = datetime.now()
    user = session.get('user', {})
    payload = request.get_json(silent=True) or {}
    filters = extract_filters(payload)
    page = int(filters.get('page') or 1)
    page_size = min(int(filters.get('page_size') or 500), 5000)
    print(f"[EXPORT_REL] Busca iniciada user={user.get('id')} role={user.get('role')} filtros={filters}")
    try:
        q = build_base_query(user)
        q = apply_query_filters(q, filters, user)
        # Limite temporário grande para pós-filtragem; evitar extrair tudo indiscriminadamente
        raw = q.limit(20000).execute()
        rows = raw.data or []
        print(f"[EXPORT_REL] Registros retornados antes pós-filtro: {len(rows)}")
        
        # VALIDAÇÃO DE SEGURANÇA: Verificar se todos os registros pertencem ao usuário
        rows = validate_user_data_access(rows, user)
        print(f"[EXPORT_REL] Após validação de segurança: {len(rows)}")
        
        rows = post_fetch_filter(rows, filters)
        print(f"[EXPORT_REL] Após pós-filtro: {len(rows)}")
        page_rows, total = paginate(rows, page, page_size)
        duration = (datetime.now() - started_at).total_seconds()
        return jsonify({
            'success': True,
            'duration': duration,
            'page': page,
            'page_size': page_size,
            'returned': len(page_rows),
            'total': total,
            'columns': TABLE_COLUMNS,
            'rows': page_rows
        })
    except Exception as e:
        print(f"[EXPORT_REL][ERRO] {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@export_relatorios_bp.route('/api/export_csv', methods=['POST'])
@login_required
def export_csv():
    """Exporta CSV com os filtros informados (limite de segurança)."""
    started_at = datetime.now()
    user = session.get('user', {})
    payload = request.get_json(silent=True) or {}
    filters = extract_filters(payload)
    max_rows = 50000
    print(f"[EXPORT_REL] Export CSV iniciado user={user.get('id')} filtros={filters}")
    try:
        q = build_base_query(user)
        q = apply_query_filters(q, filters, user)
        raw = q.limit(max_rows + 1).execute()
        rows = raw.data or []
        
        # VALIDAÇÃO DE SEGURANÇA: Verificar se todos os registros pertencem ao usuário
        rows = validate_user_data_access(rows, user)
        print(f"[EXPORT_REL] Após validação de segurança: {len(rows)}")
        
        rows = post_fetch_filter(rows, filters)
        if len(rows) > max_rows:
            rows = rows[:max_rows]
        output = io.StringIO()
        writer = csv.writer(output, delimiter=';')
        writer.writerow(TABLE_COLUMNS)
        for r in rows:
            writer.writerow([r.get(col, '') if r.get(col) is not None else '' for col in TABLE_COLUMNS])
        csv_data = output.getvalue()
        output.close()
        duration = (datetime.now() - started_at).total_seconds()
        filename = f"export_processos_antigos_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        headers = {
            'Content-Disposition': f'attachment; filename={filename}',
            'X-Export-Duration': str(duration)
        }
        print(f"[EXPORT_REL] CSV gerado com {len(rows)} registros para usuário {user.get('id')}")
        return Response(csv_data, mimetype='text/csv; charset=utf-8', headers=headers)
    except Exception as e:
        print(f"[EXPORT_REL][ERRO_EXPORT] {e}")
        return jsonify({'success': False, 'error': str(e)}), 500
