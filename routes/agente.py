from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from extensions import supabase
from routes.auth import login_required, role_required

bp = Blueprint('agente', __name__)

def get_company_info(cnpj):
    """Get company information from operacoes_aduaneiras table."""
    try:
        result = supabase.table('operacoes_aduaneiras') \
            .select('cliente_cpf_cnpj, cliente_razao_social') \
            .eq('cliente_cpf_cnpj', cnpj) \
            .limit(1) \
            .execute()
        return result.data[0] if result.data else None
    except Exception as e:
        print(f"Error getting company info: {str(e)}")
        return None

def get_user_companies(user_id):
    """Get all companies associated with a user from clientes_agentes."""
    try:
        result = supabase.table('clientes_agentes') \
            .select('empresas') \
            .eq('user_id', user_id) \
            .execute()
        
        if result.data and result.data[0]['empresas']:
            # Ensure proper string handling
            empresas = result.data[0]['empresas']
            if isinstance(empresas, str):
                # Remove any unwanted characters and split
                empresas = empresas.replace('[', '').replace(']', '').replace('"', '')
                cnpjs = [cnpj.strip() for cnpj in empresas.split(',') if cnpj.strip()]
            elif isinstance(empresas, list):
                cnpjs = empresas
            else:
                cnpjs = []
                
            companies = []
            for cnpj in cnpjs:
                company_info = get_company_info(cnpj.strip())
                if company_info:
                    companies.append({
                        'cnpj': company_info['cliente_cpf_cnpj'],
                        'razao_social': company_info['cliente_razao_social']
                    })
            return companies
        return []
    except Exception as e:
        print(f"Error getting user companies: {str(e)}")
        return []

@bp.route('/agente', methods=['GET', 'POST'])
@login_required
@role_required(['cliente_unique'])
def index():
    # Verificar se o usuário já tem um registro
    user_id = session['user']['id']
    existing = supabase.table('clientes_agentes').select('*').eq('user_id', user_id).execute()
    
    if request.method == 'POST':
        numero = request.form.get('numero_whatsapp')
        aceite_terms = request.form.get('aceite_terms') == 'on'
        selected_empresas = request.form.get('selected_empresas', '').strip()

        if not numero:
            flash('Por favor, informe seu número de WhatsApp.', 'error')
            return redirect(url_for('agente.index'))
            
        if not aceite_terms:
            flash('Você precisa aceitar os termos para continuar.', 'error')
            return redirect(url_for('agente.index'))
            
        if not selected_empresas:
            flash('Por favor, selecione pelo menos uma empresa.', 'error')
            return redirect(url_for('agente.index'))
        
        try:
            # Clean up selected_empresas
            empresas = selected_empresas.split(',')
            empresas = [empresa.strip() for empresa in empresas if empresa.strip()]
            
            data = {
                'user_id': user_id,
                'numero': numero,
                'aceite_termos': True,
                'empresas': empresas  # Store as array in Supabase
            }
            
            if not existing.data:
                # Criar novo registro
                supabase.table('clientes_agentes').insert(data).execute()
                flash('Adesão ao Agente Unique realizada com sucesso!', 'success')
            else:
                # Atualizar registro existente
                supabase.table('clientes_agentes').update(data).eq('user_id', user_id).execute()
                flash('Suas informações foram atualizadas com sucesso!', 'success')
                
            return redirect(url_for('agente.index'))
            
        except Exception as e:
            print(f"Erro ao processar adesão: {str(e)}")
            flash('Erro ao processar sua adesão. Tente novamente.', 'error')
            return redirect(url_for('agente.index'))
    
    # Get existing record with company information
    context = {
        'existing': None,
        'empresas_info': []
    }
    
    if existing.data:
        context['existing'] = existing.data[0]
        context['empresas_info'] = get_user_companies(user_id)
    
    return render_template('agente/index.html', **context)

@bp.route('/agente/descadastrar', methods=['POST'])
@login_required
@role_required(['cliente_unique'])
def descadastrar():
    user_id = session['user']['id']
    try:
        # Remove o registro do usuário
        supabase.table('clientes_agentes').delete().eq('user_id', user_id).execute()
        flash('Você foi descadastrado do Agente Unique com sucesso.', 'success')
    except Exception as e:
        flash('Erro ao processar seu descadastro. Tente novamente.', 'error')
    
    return redirect(url_for('agente.index'))