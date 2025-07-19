from flask import Blueprint, render_template, request, session, send_file
from extensions import supabase
from routes.auth import login_required, role_required
import tempfile
import os
from datetime import datetime

# Criar blueprint com configuração modular
relatorios_bp = Blueprint(
    'relatorios', 
    __name__,
    template_folder='templates',
    static_folder='static',
    static_url_path='/relatorios/static',
    url_prefix='/relatorios'
)

@relatorios_bp.route('/', methods=['GET', 'POST'])
@login_required
def index():
    user = session['user']
    start_date = request.form.get('start_date')
    end_date = request.form.get('end_date')
    
    # Buscar operações baseado no perfil
    query = supabase.table('operacoes_aduaneiras').select('*')
    
    if user['role'] not in ['admin', 'interno_unique']:
        query = query.eq('cliente_id', user['id'])
    
    if start_date:
        query = query.gte('data', start_date)
    if end_date:
        query = query.lte('data', end_date)
    
    operacoes = query.order('data', desc=True).execute()
    
    if request.form.get('generate_pdf'):
        # Gerar PDF
        html = render_template('pdf_template.html',
                             operacoes=operacoes.data,
                             start_date=start_date,
                             end_date=end_date,
                             generated_at=datetime.now().strftime('%d/%m/%Y %H:%M'))
          
    return render_template('relatorios.html',
                         operacoes=operacoes.data if operacoes.data else [],
                         start_date=start_date,
                         end_date=end_date)

@relatorios_bp.route('/pdf')
@login_required
def generate_pdf():
    user_role = session['user']['role']
    user_id = session['user']['id']
    
    # Get parameters
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    cliente_id = request.args.get('cliente_id')
    
    # Build query
    query = supabase.table('operacoes_aduaneiras').select('*')
    
    if user_role not in ['admin', 'interno_unique']:
        query = query.eq('cliente_id', user_id)
    elif cliente_id:
        query = query.eq('cliente_id', cliente_id)
    
    if start_date:
        query = query.gte('data', start_date)
    if end_date:
        query = query.lte('data', end_date)
    
    response = query.execute()
    operations = response.data
    
    # Generate HTML content
    html_content = render_template('pdf_template.html',
                                 operations=operations,
                                 start_date=start_date,
                                 end_date=end_date,
                                 generated_at=datetime.now().strftime('%d/%m/%Y %H:%M'))
    
    # Return PDF response (implementation would depend on PDF library used)
    return html_content
