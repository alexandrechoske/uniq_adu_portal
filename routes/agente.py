from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from extensions import supabase
from routes.auth import login_required, role_required

bp = Blueprint('agente', __name__)

@bp.route('/agente', methods=['GET', 'POST'])
@login_required
@role_required(['cliente_unique'])
def index():
    user_id = session['user']['id']
    agent_status = session['user'].get('agent_status', {})
    
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
                'aceite_termos': True,
                'usuario_ativo': True
            }
            
            # Verificar se já existe registro
            existing = supabase.table('clientes_agentes').select('*').eq('user_id', user_id).execute()
            
            if existing.data:
                # Atualizar registro existente
                supabase.table('clientes_agentes').update({
                    'numero': numero,
                    'aceite_termos': True,
                    'usuario_ativo': True
                }).eq('user_id', user_id).execute()
                flash('Suas informações foram atualizadas com sucesso!', 'success')
            else:
                # Criar novo registro
                supabase.table('clientes_agentes').insert(data).execute()
                flash('Adesão ao Agente Unique realizada com sucesso!', 'success')
            
            # Atualizar status na sessão
            session['user']['agent_status'] = {
                'is_active': True,
                'numero': numero,
                'aceite_termos': True
            }
            
            return redirect(url_for('agente.index'))
            
        except Exception as e:
            print(f"[DEBUG] Erro ao processar adesão: {str(e)}")
            flash('Erro ao processar sua adesão. Tente novamente.', 'error')
            return redirect(url_for('agente.index'))
    
    # Usar informações da sessão para o contexto
    context = {
        'existing': None
    }
    
    if agent_status.get('is_active'):
        context['existing'] = {
            'numero': agent_status.get('numero'),
            'aceite_termos': agent_status.get('aceite_termos')
        }
    
    return render_template('agente/index.html', **context)

@bp.route('/agente/descadastrar', methods=['POST'])
@login_required
@role_required(['cliente_unique'])
def descadastrar():
    user_id = session['user']['id']
    try:
        # Atualiza o registro marcando como inativo
        data = {
            'usuario_ativo': False,
            'aceite_termos': False
        }
        supabase.table('clientes_agentes').update(data).eq('user_id', user_id).execute()
        
        # Atualizar status na sessão
        session['user']['agent_status'] = {
            'is_active': False,
            'numero': None,
            'aceite_termos': False
        }
        
        flash('Você foi descadastrado do Agente Unique com sucesso.', 'success')
    except Exception as e:
        print(f"[DEBUG] Erro ao descadastrar: {str(e)}")
        flash('Erro ao processar seu descadastro. Tente novamente.', 'error')
    
    return redirect(url_for('agente.index'))