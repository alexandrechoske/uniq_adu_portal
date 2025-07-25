# --- IMPORTS E BLUEPRINT NO TOPO ---
from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify
from extensions import supabase, supabase_admin
from routes.auth import login_required, role_required
import requests
import json
import traceback
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

@bp.route('/', methods=['GET', 'POST'])
@login_required
@role_required(['cliente_unique', 'admin'])
def index():
    user_id = session['user']['id']
    print(f"[AGENTE DEBUG] Método: {request.method}, User ID: {user_id}")
    if request.method == 'POST':
        print(f"[AGENTE DEBUG] POST recebido. Form data: {dict(request.form)}")
        numero = request.form.get('numero_whatsapp')
        aceite_terms = request.form.get('aceite_terms') == 'on' or request.form.get('aceite_terms') == 'true' or request.form.get('aceite_terms') == 'checked'
        print(f"[AGENTE DEBUG] Número recebido: {numero}")
        print(f"[AGENTE DEBUG] Aceite termos recebido: {aceite_terms}")
        if not numero:
            print(f"[AGENTE DEBUG] Número não informado")
            flash('Por favor, informe seu número de WhatsApp.', 'error')
            return redirect(url_for('agente.index'))
        # Verificar se o usuário já aceitou os termos anteriormente
        user_record = supabase.table('clientes_agentes').select('aceite_termos').eq('user_id', user_id).execute()
        already_accepted_terms = user_record.data and user_record.data[0].get('aceite_termos', False)
        print(f"[AGENTE DEBUG] Termos já aceitos anteriormente: {already_accepted_terms}")
        if not aceite_terms and not already_accepted_terms:
            print(f"[AGENTE DEBUG] Usuário precisa aceitar os termos")
            flash('Você precisa aceitar os termos para continuar.', 'error')
            return redirect(url_for('agente.index'))
        try:
            # Verificar se o número já existe em qualquer usuário
            all_records = supabase.table('clientes_agentes').select('numero, user_id').eq('usuario_ativo', True).execute()
            print(f"[AGENTE DEBUG] Registros encontrados: {len(all_records.data) if all_records.data else 0}")
            for record in all_records.data if all_records.data else []:
                existing_numbers = record.get('numero', [])
                if isinstance(existing_numbers, str):
                    existing_numbers = [existing_numbers] if existing_numbers else []
                elif not isinstance(existing_numbers, list):
                    existing_numbers = []
                if numero in existing_numbers and record['user_id'] != user_id:
                    print(f"[AGENTE DEBUG] Número já cadastrado por outro usuário: {record['user_id']}")
                    flash('Este número já está cadastrado por outro usuário.', 'error')
                    return redirect(url_for('agente.index'))
            # Buscar ou criar registro do usuário
            user_record_full = supabase.table('clientes_agentes').select('*').eq('user_id', user_id).execute()
            print(f"[AGENTE DEBUG] Registro existente encontrado: {bool(user_record_full.data)}")
            if user_record_full.data:
                print(f"[AGENTE DEBUG] Atualizando registro existente...")
                current_numbers = user_record_full.data[0].get('numero', [])
                if isinstance(current_numbers, str):
                    current_numbers = [current_numbers] if current_numbers else []
                elif not isinstance(current_numbers, list):
                    current_numbers = []
                print(f"[AGENTE DEBUG] Números atuais: {current_numbers}")
                if numero in current_numbers:
                    print(f"[AGENTE DEBUG] Número já cadastrado para este usuário")
                    flash('Este número já está cadastrado para você.', 'error')
                    return redirect(url_for('agente.index'))
                current_numbers.append(numero)
                print(f"[AGENTE DEBUG] Novos números: {current_numbers}")
                update_data = {
                    'numero': current_numbers,
                    'usuario_ativo': True,
                    'aceite_termos': True if aceite_terms else already_accepted_terms
                }
                print(f"[AGENTE DEBUG] Dados para atualização: {update_data}")
                result = supabase.table('clientes_agentes').update(update_data).eq('user_id', user_id).execute()
                print(f"[AGENTE DEBUG] Resultado da atualização: {result.data}")
                flash('Número adicionado com sucesso!', 'success')
            else:
                print(f"[AGENTE DEBUG] Criando primeiro registro do usuário...")
                user_companies = get_user_companies(user_id)
                print(f"[AGENTE DEBUG] Empresas do usuário: {user_companies}")
                data = {
                    'user_id': user_id,
                    'numero': [numero],
                    'aceite_termos': True if aceite_terms else already_accepted_terms,
                    'usuario_ativo': True,
                    'empresa': user_companies
                }
                print(f"[AGENTE DEBUG] Dados para inserção: {data}")
                result = supabase.table('clientes_agentes').insert(data).execute()
                print(f"[AGENTE DEBUG] Resultado da inserção: {result.data}")
                flash('Primeiro número cadastrado com sucesso!', 'success')
            print(f"[AGENTE DEBUG] Processo concluído com sucesso. Redirecionando...")
            return redirect(url_for('agente.index'))
        except Exception as e:
            print(f"[AGENTE DEBUG] Erro ao processar adesão: {str(e)}")
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
    
    return render_template('agente.html', **context)

# --- AJAX: Adicionar número ---
@bp.route('/ajax/add-numero', methods=['POST'])
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

# --- AJAX: Remover número ---
@bp.route('/ajax/remove-numero', methods=['POST'])
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

# --- AJAX: Cancelar adesão ---
@bp.route('/ajax/cancelar-adesao', methods=['POST'])
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

# --- ÁREA ADMINISTRATIVA ---
@bp.route('/admin')
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
        
        return render_template('admin.html', agentes=agentes)
        
    except Exception as e:
        print(f"[ERROR] Erro ao buscar agentes: {str(e)}")
        import traceback
        traceback.print_exc()
        flash('Erro ao carregar dados dos agentes.', 'error')
        return render_template('admin.html', agentes=[])

@bp.route('/admin/toggle-user', methods=['POST'])
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

@bp.route('/admin/add-numero', methods=['POST'])
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

@bp.route('/admin/remove-numero', methods=['POST'])
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
