from flask import Blueprint, render_template, session
from extensions import supabase
from routes.auth import login_required, role_required
import plotly.express as px
import pandas as pd

bp = Blueprint('dashboard', __name__)

@bp.route('/dashboard')
@login_required
def index():
    user = session['user']
    
    # Buscar operações baseado no perfil
    if user['role'] == 'admin':
        operacoes = supabase.table('operacoes').select('*').order('data', desc=True).limit(5).execute()
    elif user['role'] == 'interno_unique':
        operacoes = supabase.table('operacoes').select('*').order('data', desc=True).limit(5).execute()
    else:  # cliente
        operacoes = supabase.table('operacoes').select('*').eq('cliente_id', user['id']).order('data', desc=True).limit(5).execute()
    
    # Buscar estatísticas
    if user['role'] == 'admin':
        total = supabase.table('operacoes').select('id', count='exact').execute()
        imports = supabase.table('operacoes').select('id', count='exact').eq('tipo', 'importacao').execute()
        exports = supabase.table('operacoes').select('id', count='exact').eq('tipo', 'exportacao').execute()
    elif user['role'] == 'interno_unique':
        total = supabase.table('operacoes').select('id', count='exact').execute()
        imports = supabase.table('operacoes').select('id', count='exact').eq('tipo', 'importacao').execute()
        exports = supabase.table('operacoes').select('id', count='exact').eq('tipo', 'exportacao').execute()
    else:  # cliente
        total = supabase.table('operacoes').select('id', count='exact').eq('cliente_id', user['id']).execute()
        imports = supabase.table('operacoes').select('id', count='exact').eq('cliente_id', user['id']).eq('tipo', 'importacao').execute()
        exports = supabase.table('operacoes').select('id', count='exact').eq('cliente_id', user['id']).eq('tipo', 'exportacao').execute()
    
    # Create Plotly figure for operations by type
    df = pd.DataFrame(operacoes.data)
    if not df.empty:
        fig = px.pie(df, names='tipo', title='Operações por Tipo')
        operations_chart = fig.to_html(full_html=False)
    else:
        operations_chart = None
    
    return render_template('dashboard/index.html',
                         operacoes=operacoes.data if operacoes.data else [],
                         total_operations=total.count if total.count else 0,
                         imports=imports.count if imports.count else 0,
                         exports=exports.count if exports.count else 0,
                         operations_chart=operations_chart,
                         user_role=user['role'])

@bp.route('/dashboard/operations')
@login_required
def operations():
    user_role = session['user']['role']
    user_id = session['user']['id']
    
    # Fetch operations with pagination
    page = request.args.get('page', 1, type=int)
    per_page = 10
    
    if user_role in ['admin', 'interno_unique']:
        response = supabase.table('operacoes')\
            .select('*')\
            .range((page-1)*per_page, page*per_page-1)\
            .execute()
    else:
        response = supabase.table('operacoes')\
            .select('*')\
            .eq('cliente_id', user_id)\
            .range((page-1)*per_page, page*per_page-1)\
            .execute()
    
    operations = response.data
    
    return render_template('dashboard/operations.html',
                         operations=operations,
                         page=page,
                         user_role=user_role) 