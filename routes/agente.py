from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from extensions import supabase
from routes.auth import login_required, role_required
import requests
import json

bp = Blueprint('agente', __name__)

def notificar_cadastro_n8n(numero_zap):
    """Envia notificação para o webhook do N8N para acionar o fluxo de mensagem no WhatsApp"""
    try:
        url = 'https://n8n.kelvin.home.nom.br/webhook-test/portal-cadastro'
        payload = {
            'numero_zap': numero_zap
        }
        headers = {
            'Content-Type': 'application/json'
        }
        
        response = requests.post(url, data=json.dumps(payload), headers=headers)
        
        if response.status_code == 200:
            print(f"[INFO] Webhook N8N acionado com sucesso para o número {numero_zap}")
            return True
        else:
            print(f"[ERROR] Falha ao acionar webhook N8N. Status code: {response.status_code}")
            print(f"[ERROR] Resposta: {response.text}")
            return False
    except Exception as e:
        print(f"[ERROR] Erro ao acionar webhook N8N: {str(e)}")
        return False

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
            
            if existing.data:                # Atualizar registro existente
                supabase.table('clientes_agentes').update({
                    'numero': numero,
                    'aceite_termos': True,
                    'usuario_ativo': True
                }).eq('user_id', user_id).execute()
                flash('Suas informações foram atualizadas com sucesso!', 'success')
                
                # Se o número mudou ou se o usuário foi reativado, enviar notificação pelo webhook
                old_numero = existing.data[0].get('numero') if existing.data else None
                old_ativo = existing.data[0].get('usuario_ativo', False) if existing.data else False
                
                if old_numero != numero or (not old_ativo and True):
                    webhook_success = notificar_cadastro_n8n(numero)
                    if webhook_success:
                        flash('Você receberá uma mensagem de boas-vindas no WhatsApp em instantes!', 'success')
                    else:
                        flash('Cadastro atualizado, mas não foi possível enviar mensagem de boas-vindas.', 'warning')
            else:                # Criar novo registro
                supabase.table('clientes_agentes').insert(data).execute()
                flash('Adesão ao Agente Unique realizada com sucesso!', 'success')
            
            # Atualizar status na sessão
            session['user']['agent_status'] = {
                'is_active': True,
                'numero': numero,
                'aceite_termos': True
            }
            
            # Enviar notificação para o N8N acionar o fluxo de mensagem no WhatsApp
            webhook_success = notificar_cadastro_n8n(numero)
            if webhook_success:
                flash('Você receberá uma mensagem de boas-vindas no WhatsApp em instantes!', 'success')
            else:
                flash('Cadastro realizado, mas não foi possível enviar mensagem de boas-vindas.', 'warning')
            
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