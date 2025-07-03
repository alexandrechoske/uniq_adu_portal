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

@bp.route('/agente', methods=['GET', 'POST'])
@login_required
@role_required(['cliente_unique', 'admin'])
def index():
    user_id = session['user']['id']
    
    if request.method == 'POST':
        numero = request.form.get('numero_whatsapp')
        aceite_terms = request.form.get('aceite_terms') == 'on'

        if not numero:
            flash('Por favor, informe seu número de WhatsApp.', 'error')
            return redirect(url_for('agente.index'))
        
        # Se o usuário já aceitou os termos anteriormente, não precisa aceitar novamente
        user_record = supabase.table('clientes_agentes').select('aceite_termos').eq('user_id', user_id).execute()
        already_accepted_terms = user_record.data and user_record.data[0].get('aceite_termos', False)
        
        if not aceite_terms and not already_accepted_terms:
            flash('Você precisa aceitar os termos para continuar.', 'error')
            return redirect(url_for('agente.index'))
        
        try:
            # Verificar se o número já existe em qualquer usuário
            all_records = supabase.table('clientes_agentes').select('numero, user_id').eq('usuario_ativo', True).execute()
            
            for record in all_records.data if all_records.data else []:
                existing_numbers = record.get('numero', [])
                if isinstance(existing_numbers, str):
                    existing_numbers = [existing_numbers] if existing_numbers else []
                elif not isinstance(existing_numbers, list):
                    existing_numbers = []
                
                if numero in existing_numbers and record['user_id'] != user_id:
                    flash('Este número já está cadastrado por outro usuário.', 'error')
                    return redirect(url_for('agente.index'))
            
            # Buscar ou criar registro do usuário
            user_record = supabase.table('clientes_agentes').select('*').eq('user_id', user_id).execute()
            
            if user_record.data:
                # Usuário já tem registro, adicionar número à lista
                current_numbers = user_record.data[0].get('numero', [])
                if isinstance(current_numbers, str):
                    current_numbers = [current_numbers] if current_numbers else []
                elif not isinstance(current_numbers, list):
                    current_numbers = []
                
                # Verificar se o número já existe para este usuário
                if numero in current_numbers:
                    flash('Este número já está cadastrado para você.', 'error')
                    return redirect(url_for('agente.index'))
                
                # Adicionar novo número
                current_numbers.append(numero)
                
                # Atualizar registro existente
                update_data = {
                    'numero': current_numbers,
                    'usuario_ativo': True
                }
                
                # Se o usuário está aceitando os termos agora, atualizar
                if aceite_terms:
                    update_data['aceite_termos'] = True
                
                supabase.table('clientes_agentes').update(update_data).eq('user_id', user_id).execute()
                flash('Número adicionado com sucesso!', 'success')
                
            else:
                # Primeiro registro do usuário
                # Buscar empresas do sistema principal (você deve implementar esta lógica)
                user_companies = []  # TODO: Implementar busca de empresas do usuário
                
                data = {
                    'user_id': user_id,
                    'numero': [numero],  # Array com o primeiro número
                    'aceite_termos': aceite_terms or already_accepted_terms,
                    'usuario_ativo': True,
                    'empresa': user_companies
                }
                supabase.table('clientes_agentes').insert(data).execute()
                flash('Primeiro número cadastrado com sucesso!', 'success')
            
            # Enviar notificação para o N8N
            webhook_success = notificar_cadastro_n8n(numero)
            if webhook_success:
                flash('Você receberá uma mensagem de boas-vindas no WhatsApp em instantes!', 'success')
            else:
                flash('Número cadastrado, mas não foi possível enviar mensagem de boas-vindas.', 'warning')
            
            return redirect(url_for('agente.index'))
            
        except Exception as e:
            print(f"[DEBUG] Erro ao processar adesão: {str(e)}")
            import traceback
            traceback.print_exc()
            flash('Erro ao processar sua adesão. Tente novamente.', 'error')
            return redirect(url_for('agente.index'))
    
    # Buscar registro do usuário com todos os números
    try:
        user_record = supabase.table('clientes_agentes').select('*').eq('user_id', user_id).execute()
        
        registered_numbers = []
        terms_accepted = False
        
        if user_record.data:
            record = user_record.data[0]
            numbers = record.get('numero', [])
            terms_accepted = record.get('aceite_termos', False)
            
            if isinstance(numbers, str):
                numbers = [numbers] if numbers else []
            elif not isinstance(numbers, list):
                numbers = []
            
            # Criar lista de objetos para compatibilidade com o template
            for i, number in enumerate(numbers):
                if number:  # Só incluir números não vazios
                    registered_numbers.append({
                        'id': f"{record['id']}_{i}",
                        'numero': number
                    })
        
        context = {
            'registered_numbers': registered_numbers,
            'terms_accepted': terms_accepted
        }
    except Exception as e:
        print(f"[DEBUG] Erro ao buscar números cadastrados: {str(e)}")
        context = {
            'registered_numbers': [],
            'terms_accepted': False
        }
    
    return render_template('agente/index.html', **context)

@bp.route('/agente/descadastrar', methods=['POST'])
@login_required
@role_required(['cliente_unique'])
def descadastrar():
    user_id = session['user']['id']
    numero_id = request.form.get('numero_id')
    
    try:
        if numero_id:
            # Se numero_id contém o número específico (formato: "record_id_index")
            if '_' in numero_id:
                # Extrair o índice do número
                parts = numero_id.split('_')
                if len(parts) >= 2:
                    try:
                        index = int(parts[-1])
                    except ValueError:
                        flash('ID de número inválido.', 'error')
                        return redirect(url_for('agente.index'))
                    
                    # Buscar registro do usuário
                    user_record = supabase.table('clientes_agentes').select('numero').eq('user_id', user_id).execute()
                    
                    if user_record.data:
                        numbers = user_record.data[0].get('numero', [])
                        if isinstance(numbers, str):
                            numbers = [numbers] if numbers else []
                        elif not isinstance(numbers, list):
                            numbers = []
                        
                        if 0 <= index < len(numbers):
                            # Remover o número do array
                            numero_removido = numbers.pop(index)
                            
                            # Se não sobrou nenhum número, desativar o usuário
                            if not numbers:
                                supabase.table('clientes_agentes').update({
                                    'usuario_ativo': False,
                                    'aceite_termos': False,
                                    'numero': []
                                }).eq('user_id', user_id).execute()
                                flash('Último número removido. Você foi descadastrado do Agente Unique.', 'success')
                            else:
                                # Atualizar array sem o número removido
                                supabase.table('clientes_agentes').update({
                                    'numero': numbers
                                }).eq('user_id', user_id).execute()
                                flash(f'Número {numero_removido} removido com sucesso!', 'success')
                        else:
                            flash('Número não encontrado.', 'error')
                    else:
                        flash('Usuário não encontrado.', 'error')
                else:
                    flash('ID de número inválido.', 'error')
            else:
                flash('Formato de ID inválido.', 'error')
        else:
            # Remover todos os números do usuário
            supabase.table('clientes_agentes').update({
                'usuario_ativo': False,
                'aceite_termos': False,
                'numero': []
            }).eq('user_id', user_id).execute()
            
            flash('Todos os números foram removidos do Agente Unique!', 'success')
            
    except Exception as e:
        print(f"[DEBUG] Erro ao descadastrar: {str(e)}")
        import traceback
        traceback.print_exc()
        flash('Erro ao processar remoção. Tente novamente.', 'error')
    
    return redirect(url_for('agente.index'))