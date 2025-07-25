from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify
from extensions import supabase, supabase_admin
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
        
        user_data = None
        
        if user_record.data:
            record = user_record.data[0]
            numbers = record.get('numero', [])
            terms_accepted = record.get('aceite_termos', False)
            usuario_ativo = record.get('usuario_ativo', False)
            
            # Processar números - garantir que seja lista
            if isinstance(numbers, str):
                numbers = [numbers] if numbers else []
            elif not isinstance(numbers, list):
                numbers = []
            
            # Filtrar números vazios
            numbers = [num for num in numbers if num and num.strip()]
            
            # Processar empresas
            companies = record.get('empresa', [])
            if not isinstance(companies, list):
                companies = []
            
            user_data = {
                'id': record['id'],
                'numero': numbers,
                'aceite_termos': terms_accepted,
                'usuario_ativo': usuario_ativo,
                'empresa': companies,
                'nome': record.get('nome'),
                'created_at': record.get('created_at'),
                'updated_at': record.get('updated_at')
            }
        
        context = {
            'user_data': user_data
        }
    except Exception as e:
        print(f"[DEBUG] Erro ao buscar dados do usuário: {str(e)}")
        context = {
            'user_data': None
        }
    
    return render_template('agente/index.html', **context)

@bp.route('/agente/admin')
@login_required
@role_required(['admin'])
def admin():
    """Área administrativa para gerenciar todos os agentes"""
    try:
        # Buscar todos os registros de agentes
        agentes_data = supabase_admin.table('clientes_agentes').select('*').execute()
        
        # Buscar informações dos usuários
        users_data = supabase_admin.table('users').select('id, email, nome').execute()
        
        # Criar um mapeamento de usuários
        users_map = {}
        if users_data.data:
            for user in users_data.data:
                users_map[user['id']] = user
        
        agentes = []
        if agentes_data.data:
            for record in agentes_data.data:
                # Processar números
                numbers = record.get('numero', [])
                if isinstance(numbers, str):
                    numbers = [numbers] if numbers else []
                elif not isinstance(numbers, list):
                    numbers = []
                
                # Filtrar números vazios
                numbers = [num for num in numbers if num and num.strip()]
                
                # Processar empresas
                companies = record.get('empresa', [])
                if not isinstance(companies, list):
                    companies = []
                
                # Buscar informações do usuário
                user_info = users_map.get(record.get('user_id'), {})
                
                agentes.append({
                    'id': record.get('id'),
                    'user_id': record.get('user_id'),
                    'nome': record.get('nome') or user_info.get('nome'),
                    'email': user_info.get('email'),
                    'numeros': numbers,
                    'empresas': companies,
                    'aceite_termos': record.get('aceite_termos', False),
                    'usuario_ativo': record.get('usuario_ativo', False),
                    'created_at': record.get('created_at'),
                    'updated_at': record.get('updated_at')
                })
        
        return render_template('agente/admin.html', agentes=agentes)
        
    except Exception as e:
        print(f"[ERROR] Erro ao buscar agentes: {str(e)}")
        import traceback
        traceback.print_exc()
        flash('Erro ao carregar dados dos agentes.', 'error')
        return render_template('agente/admin.html', agentes=[])

@bp.route('/agente/ajax/add-numero', methods=['POST'])
@login_required
@role_required(['cliente_unique', 'admin'])
def ajax_add_numero():
    """Adicionar novo número via AJAX"""
    try:
        data = request.get_json()
        numero = data.get('numero', '').strip()
        user_id = session['user']['id']
        
        if not numero:
            return jsonify({'success': False, 'message': 'Número é obrigatório'})
        
        # Verificar se o número já existe em qualquer usuário
        all_records = supabase.table('clientes_agentes').select('numero, user_id').eq('usuario_ativo', True).execute()
        
        for record in all_records.data if all_records.data else []:
            existing_numbers = record.get('numero', [])
            if isinstance(existing_numbers, str):
                existing_numbers = [existing_numbers] if existing_numbers else []
            elif not isinstance(existing_numbers, list):
                existing_numbers = []
            
            if numero in existing_numbers and record['user_id'] != user_id:
                return jsonify({'success': False, 'message': 'Este número já está cadastrado por outro usuário'})
        
        # Buscar registro do usuário
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
                return jsonify({'success': False, 'message': 'Este número já está cadastrado para você'})
            
            # Adicionar novo número
            current_numbers.append(numero)
            
            # Atualizar registro existente
            supabase.table('clientes_agentes').update({
                'numero': current_numbers,
                'usuario_ativo': True
            }).eq('user_id', user_id).execute()
            
            # Enviar notificação para o N8N
            notificar_cadastro_n8n(numero)
            
            return jsonify({'success': True, 'message': 'Número adicionado com sucesso!'})
        else:
            return jsonify({'success': False, 'message': 'Usuário não encontrado no sistema de agentes'})
            
    except Exception as e:
        print(f"[ERROR] Erro ao adicionar número: {str(e)}")
        return jsonify({'success': False, 'message': 'Erro interno do servidor'})

@bp.route('/agente/ajax/remove-numero', methods=['POST'])
@login_required
@role_required(['cliente_unique', 'admin'])
def ajax_remove_numero():
    """Remover número via AJAX"""
    try:
        data = request.get_json()
        numero = data.get('numero', '').strip()
        user_id = session['user']['id']
        
        if not numero:
            return jsonify({'success': False, 'message': 'Número é obrigatório'})
        
        # Buscar registro do usuário
        user_record = supabase.table('clientes_agentes').select('numero').eq('user_id', user_id).execute()
        
        if user_record.data:
            numbers = user_record.data[0].get('numero', [])
            if isinstance(numbers, str):
                numbers = [numbers] if numbers else []
            elif not isinstance(numbers, list):
                numbers = []
            
            if numero in numbers:
                # Remover o número do array
                numbers.remove(numero)
                
                # Se não sobrou nenhum número, desativar o usuário
                if not numbers:
                    supabase.table('clientes_agentes').update({
                        'usuario_ativo': False,
                        'aceite_termos': False,
                        'numero': []
                    }).eq('user_id', user_id).execute()
                    return jsonify({'success': True, 'message': 'Último número removido. Você foi descadastrado do Agente Unique.'})
                else:
                    # Atualizar array sem o número removido
                    supabase.table('clientes_agentes').update({
                        'numero': numbers
                    }).eq('user_id', user_id).execute()
                    return jsonify({'success': True, 'message': f'Número {numero} removido com sucesso!'})
            else:
                return jsonify({'success': False, 'message': 'Número não encontrado'})
        else:
            return jsonify({'success': False, 'message': 'Usuário não encontrado'})
            
    except Exception as e:
        print(f"[ERROR] Erro ao remover número: {str(e)}")
        return jsonify({'success': False, 'message': 'Erro interno do servidor'})

@bp.route('/agente/ajax/cancelar-adesao', methods=['POST'])
@login_required
@role_required(['cliente_unique', 'admin'])
def ajax_cancelar_adesao():
    """Cancelar adesão via AJAX"""
    try:
        user_id = session['user']['id']
        
        # Remover todos os números do usuário
        supabase.table('clientes_agentes').update({
            'usuario_ativo': False,
            'aceite_termos': False,
            'numero': []
        }).eq('user_id', user_id).execute()
        
        return jsonify({'success': True, 'message': 'Adesão cancelada com sucesso!'})
        
    except Exception as e:
        print(f"[ERROR] Erro ao cancelar adesão: {str(e)}")
        return jsonify({'success': False, 'message': 'Erro interno do servidor'})

@bp.route('/agente/admin/toggle-user', methods=['POST'])
@login_required
@role_required(['admin'])
def admin_toggle_user():
    """Admin: Ativar/desativar usuário"""
    try:
        data = request.get_json()
        user_id = data.get('user_id')
        ativo = data.get('ativo', False)
        
        if not user_id:
            return jsonify({'success': False, 'message': 'ID do usuário é obrigatório'})
        
        supabase_admin.table('clientes_agentes').update({
            'usuario_ativo': ativo
        }).eq('user_id', user_id).execute()
        
        status = 'ativado' if ativo else 'desativado'
        return jsonify({'success': True, 'message': f'Usuário {status} com sucesso!'})
        
    except Exception as e:
        print(f"[ERROR] Erro ao alterar status do usuário: {str(e)}")
        return jsonify({'success': False, 'message': 'Erro interno do servidor'})

@bp.route('/agente/admin/add-numero', methods=['POST'])
@login_required
@role_required(['admin'])
def admin_add_numero():
    """Admin: Adicionar número para usuário"""
    try:
        data = request.get_json()
        user_id = data.get('user_id')
        numero = data.get('numero', '').strip()
        
        if not user_id or not numero:
            return jsonify({'success': False, 'message': 'ID do usuário e número são obrigatórios'})
        
        # Verificar se o número já existe em qualquer usuário
        all_records = supabase_admin.table('clientes_agentes').select('numero, user_id').eq('usuario_ativo', True).execute()
        
        for record in all_records.data if all_records.data else []:
            existing_numbers = record.get('numero', [])
            if isinstance(existing_numbers, str):
                existing_numbers = [existing_numbers] if existing_numbers else []
            elif not isinstance(existing_numbers, list):
                existing_numbers = []
            
            if numero in existing_numbers:
                return jsonify({'success': False, 'message': 'Este número já está cadastrado'})
        
        # Buscar registro do usuário
        user_record = supabase_admin.table('clientes_agentes').select('*').eq('user_id', user_id).execute()
        
        if user_record.data:
            # Usuário já tem registro, adicionar número à lista
            current_numbers = user_record.data[0].get('numero', [])
            if isinstance(current_numbers, str):
                current_numbers = [current_numbers] if current_numbers else []
            elif not isinstance(current_numbers, list):
                current_numbers = []
            
            current_numbers.append(numero)
            
            # Atualizar registro existente
            supabase_admin.table('clientes_agentes').update({
                'numero': current_numbers,
                'usuario_ativo': True
            }).eq('user_id', user_id).execute()
            
            return jsonify({'success': True, 'message': 'Número adicionado com sucesso!'})
        else:
            return jsonify({'success': False, 'message': 'Usuário não encontrado'})
            
    except Exception as e:
        print(f"[ERROR] Erro ao adicionar número (admin): {str(e)}")
        return jsonify({'success': False, 'message': 'Erro interno do servidor'})

@bp.route('/agente/admin/remove-numero', methods=['POST'])
@login_required
@role_required(['admin'])
def admin_remove_numero():
    """Admin: Remover número de usuário"""
    try:
        data = request.get_json()
        user_id = data.get('user_id')
        numero = data.get('numero', '').strip()
        
        if not user_id or not numero:
            return jsonify({'success': False, 'message': 'ID do usuário e número são obrigatórios'})
        
        # Buscar registro do usuário
        user_record = supabase_admin.table('clientes_agentes').select('numero').eq('user_id', user_id).execute()
        
        if user_record.data:
            numbers = user_record.data[0].get('numero', [])
            if isinstance(numbers, str):
                numbers = [numbers] if numbers else []
            elif not isinstance(numbers, list):
                numbers = []
            
            if numero in numbers:
                # Remover o número do array
                numbers.remove(numero)
                
                # Atualizar array
                supabase_admin.table('clientes_agentes').update({
                    'numero': numbers
                }).eq('user_id', user_id).execute()
                
                return jsonify({'success': True, 'message': f'Número {numero} removido com sucesso!'})
            else:
                return jsonify({'success': False, 'message': 'Número não encontrado'})
        else:
            return jsonify({'success': False, 'message': 'Usuário não encontrado'})
            
    except Exception as e:
        print(f"[ERROR] Erro ao remover número (admin): {str(e)}")
        return jsonify({'success': False, 'message': 'Erro interno do servidor'})

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