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
        numero_whatsapp = request.form.get('numero_whatsapp')
        aceite_terms = request.form.get('aceite_terms') == 'on'
        
        if not numero_whatsapp:
            flash('Por favor, informe seu número de WhatsApp.', 'error')
            return redirect(url_for('agente.index'))
            
        if not aceite_terms:
            flash('Você precisa aceitar os termos para continuar.', 'error')
            return redirect(url_for('agente.index'))
        
        try:
            if existing.data:
                # Atualizar registro existente
                supabase.table('clientes_agentes').update({
                    'numero_whatsapp': numero_whatsapp,
                    'aceite_terms': aceite_terms
                }).eq('user_id', user_id).execute()
            else:
                # Criar novo registro
                supabase.table('clientes_agentes').insert({
                    'user_id': user_id,
                    'numero_whatsapp': numero_whatsapp,
                    'aceite_terms': aceite_terms
                }).execute()
            
            flash('Dados salvos com sucesso!', 'success')
            return redirect(url_for('dashboard.index'))
            
        except Exception as e:
            flash('Erro ao salvar os dados. Tente novamente.', 'error')
    
    return render_template('agente/index.html', existing=existing.data[0] if existing.data else None) 