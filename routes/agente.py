from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from extensions import supabase
from routes.auth import login_required, role_required

bp = Blueprint('agente', __name__)

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

        if not numero:
            flash('Por favor, informe seu número de WhatsApp.', 'error')
            return redirect(url_for('agente.index'))
            
        if not aceite_terms:
            flash('Você precisa aceitar os termos para continuar.', 'error')
            return redirect(url_for('agente.index'))
        
        try:
            data = {
                'user_id': user_id,
                'numero': numero,
                'aceite_termos': True
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
    
    # Get existing record
    context = {
        'existing': None
    }
    
    if existing.data:
        context['existing'] = existing.data[0]
    
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