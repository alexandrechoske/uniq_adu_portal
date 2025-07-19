from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from extensions import supabase
from routes.auth import login_required, role_required
import requests
import json

# Blueprint com configuração para templates e static locais
bp = Blueprint('agente', __name__, 
               url_prefix='/agente',
               template_folder='templates',
               static_folder='static',
               static_url_path='/agente/static')

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

def get_user_companies(user_id):
    """
    Busca todas as empresas que o usuário tem acesso.
    Retorna uma lista única de CNPJs.
    """
    try:
        # Buscar o registro do usuário
        user_agent = supabase.table('clientes_agentes').select('empresa').eq('user_id', user_id).eq('usuario_ativo', True).execute()
        
        if not user_agent.data:
            return []
        
        # O campo empresa é um array JSONB
        companies = user_agent.data[0].get('empresa', [])
        if isinstance(companies, list):
            return companies
        
        return []
    
    except Exception as e:
        print(f"[ERROR] Erro ao buscar empresas do usuário: {str(e)}")
        return []

def sync_user_companies_to_agent_numbers(user_id, companies):
    """
    Sincroniza as empresas que o usuário tem acesso para todos os seus números do agente.
    Útil quando o usuário ganha/perde acesso a empresas.
    """
    try:
        # Atualizar o registro do usuário com as empresas
        supabase.table('clientes_agentes').update({
            'empresa': companies
        }).eq('user_id', user_id).eq('usuario_ativo', True).execute()
        
        print(f"[INFO] Empresas sincronizadas para o usuário {user_id}")
        return True
        
    except Exception as e:
        print(f"[ERROR] Erro ao sincronizar empresas: {str(e)}")
        return False

@bp.route('/')
@login_required
@role_required(['cliente_unique', 'admin'])
def index():
    user_id = session['user']['id']
    
    # Buscar dados do usuário agente
    user_record = supabase.table('clientes_agentes').select('*').eq('user_id', user_id).execute()
    user_data = user_record.data[0] if user_record.data else None
    
    # Buscar empresas disponíveis se for admin
    empresas_disponiveis = []
    if session['user']['role'] == 'admin':
        empresas_response = supabase.table('vw_aux_cnpj_importador').select('cnpj, razao_social').execute()
        empresas_disponiveis = empresas_response.data if empresas_response.data else []
    
    return render_template('index.html', 
                         user_data=user_data, 
                         empresas_disponiveis=empresas_disponiveis)

@bp.route('/cadastrar', methods=['POST'])
@login_required
@role_required(['cliente_unique', 'admin'])
def cadastrar():
    user_id = session['user']['id']
    numero = request.form.get('numero_whatsapp')
    aceite_terms = request.form.get('aceite_terms') == 'on'

    if not numero:
        flash('Por favor, informe seu número de WhatsApp.', 'error')
        return redirect(url_for('agente.index'))
    
    # Verificar se já aceitou os termos
    user_record = supabase.table('clientes_agentes').select('aceite_termos').eq('user_id', user_id).execute()
    already_accepted_terms = user_record.data and user_record.data[0].get('aceite_termos', False)
    
    if not aceite_terms and not already_accepted_terms:
        flash('Você precisa aceitar os termos para continuar.', 'error')
        return redirect(url_for('agente.index'))
    
    try:
        # Verificar se o número já existe
        all_records = supabase.table('clientes_agentes').select('numero, user_id').eq('usuario_ativo', True).execute()
        
        for record in all_records.data if all_records.data else []:
            if record.get('numero') == numero and record.get('user_id') != user_id:
                flash('Este número já está cadastrado para outro usuário.', 'error')
                return redirect(url_for('agente.index'))
        
        # Buscar empresas do usuário
        companies = get_user_companies(user_id)
        
        # Dados para inserir/atualizar
        agent_data = {
            'user_id': user_id,
            'numero': numero,
            'empresa': companies,
            'usuario_ativo': True,
            'aceite_termos': True
        }
        
        # Verificar se já existe registro para este usuário
        existing_record = supabase.table('clientes_agentes').select('id').eq('user_id', user_id).execute()
        
        if existing_record.data:
            # Atualizar registro existente
            supabase.table('clientes_agentes').update(agent_data).eq('user_id', user_id).execute()
            flash('Número do WhatsApp atualizado com sucesso!', 'success')
        else:
            # Inserir novo registro
            supabase.table('clientes_agentes').insert(agent_data).execute()
            flash('Cadastro realizado com sucesso!', 'success')
        
        # Notificar N8N
        if notificar_cadastro_n8n(numero):
            flash('Notificação enviada! Você receberá uma mensagem no WhatsApp em breve.', 'info')
        
        return redirect(url_for('agente.index'))
        
    except Exception as e:
        print(f"[ERROR] Erro no cadastro: {str(e)}")
        flash('Erro interno do servidor. Tente novamente.', 'error')
        return redirect(url_for('agente.index'))

@bp.route('/desativar', methods=['POST'])
@login_required
@role_required(['cliente_unique', 'admin'])
def desativar():
    user_id = session['user']['id']
    
    try:
        # Desativar o agente
        supabase.table('clientes_agentes').update({
            'usuario_ativo': False
        }).eq('user_id', user_id).execute()
        
        flash('Agente desativado com sucesso.', 'success')
        
    except Exception as e:
        print(f"[ERROR] Erro ao desativar agente: {str(e)}")
        flash('Erro ao desativar o agente.', 'error')
    
    return redirect(url_for('agente.index'))

@bp.route('/admin')
@login_required
@role_required(['admin'])
def admin():
    """Página administrativa para gerenciar todos os agentes"""
    try:
        # Buscar todos os agentes ativos
        agentes_response = supabase.table('clientes_agentes').select('*').eq('usuario_ativo', True).execute()
        agentes = agentes_response.data if agentes_response.data else []
        
        # Buscar dados dos usuários
        user_ids = [agente['user_id'] for agente in agentes]
        users_response = supabase.table('users').select('id, name, email').in_('id', user_ids).execute()
        users_dict = {user['id']: user for user in users_response.data} if users_response.data else {}
        
        # Combinar dados
        for agente in agentes:
            user_data = users_dict.get(agente['user_id'], {})
            agente['user_name'] = user_data.get('name', 'Usuário não encontrado')
            agente['user_email'] = user_data.get('email', '')
        
        return render_template('admin.html', agentes=agentes)
        
    except Exception as e:
        print(f"[ERROR] Erro ao carregar dados administrativos: {str(e)}")
        flash('Erro ao carregar dados dos agentes.', 'error')
        return render_template('admin.html', agentes=[])

@bp.route('/admin/toggle/<user_id>')
@login_required
@role_required(['admin'])
def admin_toggle(user_id):
    """Ativar/desativar agente"""
    try:
        # Buscar estado atual
        current_state = supabase.table('clientes_agentes').select('usuario_ativo').eq('user_id', user_id).execute()
        
        if current_state.data:
            new_state = not current_state.data[0]['usuario_ativo']
            supabase.table('clientes_agentes').update({
                'usuario_ativo': new_state
            }).eq('user_id', user_id).execute()
            
            action = 'ativado' if new_state else 'desativado'
            flash(f'Agente {action} com sucesso.', 'success')
        else:
            flash('Agente não encontrado.', 'error')
            
    except Exception as e:
        print(f"[ERROR] Erro ao alterar estado do agente: {str(e)}")
        flash('Erro ao alterar estado do agente.', 'error')
    
    return redirect(url_for('agente.admin'))
