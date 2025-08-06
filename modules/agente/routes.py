# --- IMPORTS E BLUEPRINT NO TOPO ---
from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify
from extensions import supabase, supabase_admin
from routes.auth import login_required, role_required
import json
import requests
import traceback
from datetime import datetime

# Blueprint com configuração para templates e static locais
bp = Blueprint('agente', __name__, 
               url_prefix='/agente',
               template_folder='templates',
               static_folder='static',
               static_url_path='/agente/static')

def format_date_br(date_str):
    """Converte data ISO para formato brasileiro DD/MM/AAAA"""
    if not date_str:
        return "Data não informada"
    
    try:
        # Se for string de data ISO
        if isinstance(date_str, str):
            # Pegar apenas a parte da data (YYYY-MM-DD)
            date_part = date_str.split('T')[0] if 'T' in date_str else date_str
            # Converter para datetime
            dt = datetime.strptime(date_part, '%Y-%m-%d')
            # Retornar no formato brasileiro
            return dt.strftime('%d/%m/%Y')
        else:
            return str(date_str)
    except:
        return date_str

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

def format_phone_number(numero):
    """
    Formata número de telefone para o padrão esperado pela constraint.
    A constraint parece esperar formato: +5511999999999 (14 dígitos com +55)
    """
    import re
    
    if not numero:
        return None
    
    # Remove todos os caracteres não numéricos
    cleaned = re.sub(r'\D', '', str(numero))
    
    print(f"[FORMAT DEBUG] Input: '{numero}' → Cleaned: '{cleaned}' (length: {len(cleaned)})")
    
    # Se já tem 13 dígitos e começa com 55, adiciona +
    if len(cleaned) == 13 and cleaned.startswith('55'):
        formatted = f"+{cleaned}"
    
    # Se tem 12 dígitos e começa com 55 (caso específico: 554196650141)
    elif len(cleaned) == 12 and cleaned.startswith('55'):
        # 554196650141 → 55 + 41 + 96650141 (8 dígitos no telefone)
        # Precisa adicionar o 9: +5541966650141 (14 caracteres)
        area_code = cleaned[2:4]  # 41
        phone_part = cleaned[4:]  # 96650141 (8 dígitos)
        if len(phone_part) == 8:
            # Adicionar o 9 para celular: 96650141 → 996650141
            formatted = f"+55{area_code}9{phone_part}"
        else:
            # Se já tem 9 dígitos ou mais, usar direto
            formatted = f"+55{cleaned[2:]}"
    
    # Se tem 11 dígitos (formato brasileiro sem código de país)
    elif len(cleaned) == 11:
        formatted = f"+55{cleaned}"
    
    # Se tem 10 dígitos (sem o 9 no celular), adiciona o 9
    elif len(cleaned) == 10 and cleaned[2] in ['6', '7', '8', '9']:
        formatted = f"+55{cleaned[:2]}9{cleaned[2:]}"
    
    # Se tem 14 dígitos e começa com 55, remove um dígito extra
    elif len(cleaned) == 14 and cleaned.startswith('55'):
        formatted = f"+{cleaned[:13]}"
    
    # Se já tem 15 dígitos e começa com 55, remove dígitos extras para 14
    elif len(cleaned) == 15 and cleaned.startswith('55'):
        formatted = f"+{cleaned[:13]}"
    
    # Se não conseguiu identificar o padrão, tenta formato mínimo +55
    elif len(cleaned) >= 10:
        # Pega os últimos dígitos como número brasileiro
        if len(cleaned) >= 11:
            phone_part = cleaned[-11:]
            formatted = f"+55{phone_part}"
        else:
            # Muito poucos dígitos, adiciona zeros se necessário
            phone_part = cleaned.zfill(11)
            formatted = f"+55{phone_part}"
    
    else:
        # Formato inválido
        raise ValueError(f"Formato de número inválido: {numero} (muito poucos dígitos)")
    
    print(f"[FORMAT DEBUG] Output: '{formatted}' (length: {len(formatted)})")
    return formatted

def validate_phone_number(numero):
    """Valida se o número formatado está no padrão correto"""
    try:
        formatted = format_phone_number(numero)
        
        if not formatted:
            return False, "Número não pode estar vazio"
        
        # Deve ter exatamente 14 caracteres (+5511999999999)
        if len(formatted) != 14:
            return False, f"Número deve ter 14 caracteres, encontrado: {len(formatted)}"
        
        # Deve começar com +55
        if not formatted.startswith('+55'):
            return False, "Número deve começar com +55"
        
        # Parte do telefone deve ter 11 dígitos
        phone_part = formatted[3:]  # Remove +55
        if len(phone_part) != 11:
            return False, f"Parte do telefone deve ter 11 dígitos, encontrado: {len(phone_part)}"
        
        # Primeiro dígito deve ser 1, 2, 3, 4, 5, 6, 7, 8 ou 9 (código de área)
        area_code = phone_part[:2]
        if not area_code.isdigit() or int(area_code) < 11 or int(area_code) > 99:
            return False, f"Código de área inválido: {area_code}"
        
        # Terceiro dígito deve ser 9 (celular) ou 2,3,4,5 (fixo)
        first_digit = phone_part[2]
        if first_digit not in ['2', '3', '4', '5', '9']:
            return False, f"Primeiro dígito do telefone inválido: {first_digit}"
        
        return True, formatted
        
    except Exception as e:
        return False, str(e)

def get_user_whatsapp_numbers(user_id):
    """
    Busca todos os números WhatsApp do usuário na nova estrutura.
    Retorna lista de dicts com número, nome e demais informações.
    """
    try:
        whatsapp_query = supabase.table('user_whatsapp').select('*').eq('user_id', user_id).eq('ativo', True).order('principal', desc=True).execute()
        
        if not whatsapp_query.data:
            return []
        
        print(f"[INFO] Encontrados {len(whatsapp_query.data)} números WhatsApp para usuário {user_id}")
        return whatsapp_query.data
    
    except Exception as e:
        print(f"[ERROR] Erro ao buscar números WhatsApp do usuário: {str(e)}")
        return []

def get_user_companies(user_id):
    """
    Busca todas as empresas que o usuário tem acesso via nova estrutura user_empresas.
    Retorna uma lista de empresas com detalhes.
    """
    try:
        # Buscar empresas vinculadas via user_empresas
        empresas_query = supabase.table('user_empresas').select(
            '*, cad_clientes_sistema!inner(id, nome_cliente, cnpjs)'
        ).eq('user_id', user_id).eq('ativo', True).execute()
        
        if not empresas_query.data:
            return []
        
        empresas = []
        for vinculo in empresas_query.data:
            empresa_info = vinculo.get('cad_clientes_sistema', {})
            
            # Garantir que os dados não sejam None
            nome_cliente = empresa_info.get('nome_cliente') or 'Empresa não identificada'
            cnpjs = empresa_info.get('cnpjs') or []
            data_vinculo = vinculo.get('data_vinculo')
            
            # Formatar data para o formato brasileiro
            data_vinculo_formatada = format_date_br(data_vinculo)
            
            empresas.append({
                'id': empresa_info.get('id'),
                'nome_cliente': nome_cliente,
                'cnpjs': cnpjs,
                'data_vinculo': data_vinculo,  # Data original
                'data_vinculo_formatada': data_vinculo_formatada,  # Data formatada
                'total_cnpjs': len(cnpjs) if cnpjs else 0
            })
        
        print(f"[INFO] Encontradas {len(empresas)} empresas para usuário {user_id}")
        return empresas
    
    except Exception as e:
        print(f"[ERROR] Erro ao buscar empresas do usuário: {str(e)}")
        import traceback
        traceback.print_exc()
        return []

def render_admin_panel():
    """Renderiza o painel administrativo para admins - NOVA ESTRUTURA"""
    try:
        # Buscar todos os usuários com números WhatsApp
        whatsapp_query = supabase_admin.table('user_whatsapp').select('''
            id,
            user_id,
            numero_whatsapp,
            nome_contato,
            tipo_numero,
            ativo,
            principal,
            created_at
        ''').execute()
        
        # Buscar informações dos usuários
        users_query = supabase_admin.table('users').select('id, email, name, role').execute()
        
        # Criar mapeamento de usuários
        users_map = {}
        if users_query.data:
            for user in users_query.data:
                users_map[user['id']] = {
                    'email': user.get('email', 'N/A'),
                    'nome': user.get('name', 'Sem nome'),
                    'role': user.get('role', 'N/A')
                }
        
        # Buscar empresas vinculadas
        empresas_query = supabase_admin.table('user_empresas').select('''
            user_id,
            cad_clientes_sistema!inner(
                nome_cliente
            )
        ''').eq('ativo', True).execute()
        
        # Mapear empresas por usuário
        empresas_map = {}
        if empresas_query.data:
            for vinculo in empresas_query.data:
                user_id = vinculo['user_id']
                empresa_nome = vinculo['cad_clientes_sistema']['nome_cliente']
                if user_id not in empresas_map:
                    empresas_map[user_id] = []
                empresas_map[user_id].append(empresa_nome)
        
        # Processar dados dos usuários
        usuarios = {}
        total_users = len(users_map)
        active_users = 0
        total_numbers = 0
        
        # Organizar dados por usuário
        if whatsapp_query.data:
            for whatsapp in whatsapp_query.data:
                user_id = whatsapp['user_id']
                
                if user_id not in usuarios:
                    user_info = users_map.get(user_id, {})
                    usuarios[user_id] = {
                        'user_id': user_id,
                        'email': user_info.get('email', 'N/A'),
                        'nome': user_info.get('nome', 'Sem nome'),
                        'role': user_info.get('role', 'N/A'),
                        'numeros': [],
                        'empresas': empresas_map.get(user_id, []),
                        'ativo': False
                    }
                
                # Adicionar número
                usuarios[user_id]['numeros'].append({
                    'id': whatsapp['id'],
                    'numero': whatsapp['numero_whatsapp'],
                    'nome': whatsapp['nome_contato'],
                    'tipo': whatsapp['tipo_numero'],
                    'principal': whatsapp['principal'],
                    'ativo': whatsapp['ativo']
                })
                
                if whatsapp['ativo']:
                    usuarios[user_id]['ativo'] = True
                    total_numbers += 1
        
        # Contar usuários ativos
        active_users = sum(1 for u in usuarios.values() if u['ativo'])
        
        # Estatísticas
        stats = {
            'total_users': total_users,
            'active_users': active_users,
            'total_numbers': total_numbers,
            'total_companies': len(set([nome for empresas in empresas_map.values() for nome in empresas]))
        }
        
        context = {
            'is_admin_view': True,
            'usuarios': list(usuarios.values()),
            'stats': stats
        }
        
        return render_template('agente.html', **context)
        
    except Exception as e:
        print(f"[ERROR] Erro ao carregar painel admin: {str(e)}")
        import traceback
        traceback.print_exc()
        flash('Erro ao carregar dados dos agentes.', 'error')
        return render_template('agente.html', is_admin_view=True, usuarios=[], stats={})

@bp.route('/', methods=['GET', 'POST'])
@login_required
@role_required(['cliente_unique', 'admin'])
def index():
    user_id = session['user']['id']
    user_role = session['user']['role']
    print(f"[AGENTE DEBUG] Método: {request.method}, User ID: {user_id}, Role: {user_role}")
    
    # Se for admin, mostrar painel de gerenciamento
    if user_role == 'admin':
        return render_admin_panel()
    
    # Lógica normal para usuários comuns - NOVA ESTRUTURA
    if request.method == 'POST':
        print(f"[AGENTE DEBUG] POST recebido. Form data: {dict(request.form)}")
        numero = request.form.get('numero_whatsapp', '').strip()
        nome_contato = request.form.get('nome_contato', '').strip()
        tipo_numero = request.form.get('tipo_numero', 'pessoal')
        
        print(f"[AGENTE DEBUG] Número: {numero}, Nome: {nome_contato}, Tipo: {tipo_numero}")
        
        if not numero:
            flash('Por favor, informe o número de WhatsApp.', 'error')
            return redirect(url_for('agente.index'))
        
        if not nome_contato:
            flash('Por favor, informe um nome para identificar este número.', 'error')
            return redirect(url_for('agente.index'))
        
        # Validar e formatar número
        is_valid, formatted_numero = validate_phone_number(numero)
        if not is_valid:
            flash(f'Número inválido: {formatted_numero}', 'error')
            return redirect(url_for('agente.index'))
        
        print(f"[AGENTE DEBUG] Número formatado: {numero} → {formatted_numero}")
        
        try:
            # Verificar se o número já existe
            existing = supabase.table('user_whatsapp').select('id, user_id').eq('numero_whatsapp', formatted_numero).eq('ativo', True).execute()
            
            if existing.data:
                existing_user = existing.data[0]['user_id']
                if existing_user != user_id:
                    flash('Este número já está cadastrado por outro usuário.', 'error')
                    return redirect(url_for('agente.index'))
                else:
                    flash('Este número já está cadastrado para você.', 'error')
                    return redirect(url_for('agente.index'))
            
            # Verificar se é o primeiro número (será principal)
            user_numbers = supabase.table('user_whatsapp').select('id').eq('user_id', user_id).eq('ativo', True).execute()
            is_first_number = not user_numbers.data
            
            # Inserir novo número
            data = {
                'user_id': user_id,
                'numero_whatsapp': formatted_numero,
                'nome_contato': nome_contato,
                'tipo_numero': tipo_numero,
                'principal': is_first_number,
                'ativo': True
            }
            
            result = supabase.table('user_whatsapp').insert(data).execute()
            print(f"[AGENTE DEBUG] Número inserido: {result.data}")
            
            flash('Número WhatsApp adicionado com sucesso!', 'success')
            return redirect(url_for('agente.index'))
            
        except Exception as e:
            print(f"[AGENTE DEBUG] Erro ao adicionar número: {str(e)}")
            import traceback
            traceback.print_exc()
            flash('Erro ao adicionar número. Tente novamente.', 'error')
            return redirect(url_for('agente.index'))
    
    # GET - Buscar dados do usuário
    try:
        # Buscar números WhatsApp do usuário
        numeros = get_user_whatsapp_numbers(user_id)
        
        # Buscar empresas do usuário
        empresas = get_user_companies(user_id)
        
        context = {
            'user_data': {
                'numeros': numeros,
                'empresas': empresas,
                'tem_numeros': len(numeros) > 0
            }
        }
        
        print(f"[AGENTE DEBUG] Context preparado: {len(numeros)} números, {len(empresas)} empresas")
        
    except Exception as e:
        print(f"[AGENTE DEBUG] Erro ao buscar dados: {str(e)}")
        context = {
            'user_data': {
                'numeros': [],
                'empresas': [],
                'tem_numeros': False
            }
        }
    
    return render_template('agente.html', **context)

# --- AJAX: Adicionar número - NOVA ESTRUTURA ---
@bp.route('/ajax/add-numero', methods=['POST'])
@login_required
@role_required(['cliente_unique', 'admin'])
def ajax_add_numero():
    """Adicionar novo número via AJAX - NOVA ESTRUTURA"""
    try:
        data = request.get_json()
        numero = data.get('numero', '').strip()
        nome_contato = data.get('nome_contato', '').strip()
        tipo_numero = data.get('tipo_numero', 'pessoal')
        user_id = session['user']['id']
        
        if not numero:
            return jsonify({'success': False, 'message': 'Número é obrigatório'})
        
        if not nome_contato:
            return jsonify({'success': False, 'message': 'Nome de contato é obrigatório'})
        
        # Validar e formatar número
        is_valid, formatted_numero = validate_phone_number(numero)
        if not is_valid:
            return jsonify({'success': False, 'message': f'Número inválido: {formatted_numero}'})
        
        # Verificar se o número já existe
        existing = supabase.table('user_whatsapp').select('id, user_id').eq('numero_whatsapp', formatted_numero).eq('ativo', True).execute()
        
        if existing.data:
            existing_user = existing.data[0]['user_id']
            if existing_user != user_id:
                return jsonify({'success': False, 'message': 'Este número já está cadastrado por outro usuário'})
            else:
                return jsonify({'success': False, 'message': 'Este número já está cadastrado para você'})
        
        # Verificar se é o primeiro número (será principal)
        user_numbers = supabase.table('user_whatsapp').select('id').eq('user_id', user_id).eq('ativo', True).execute()
        is_first_number = not user_numbers.data
        
        # Inserir novo número
        data_insert = {
            'user_id': user_id,
            'numero_whatsapp': formatted_numero,
            'nome_contato': nome_contato,
            'tipo_numero': tipo_numero,
            'principal': is_first_number,
            'ativo': True
        }
        
        result = supabase.table('user_whatsapp').insert(data_insert).execute()
        
        # Enviar notificação para o N8N
        try:
            notificar_cadastro_n8n(formatted_numero)
        except Exception as e:
            print(f"[WARNING] Erro ao notificar N8N: {str(e)}")
        
        return jsonify({'success': True, 'message': 'Número adicionado com sucesso!'})
            
    except Exception as e:
        print(f"[ERROR] Erro ao adicionar número: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'message': 'Erro interno do servidor'})

# --- AJAX: Remover número - NOVA ESTRUTURA ---
@bp.route('/ajax/remove-numero', methods=['POST'])
@login_required
@role_required(['cliente_unique', 'admin'])
def ajax_remove_numero():
    """Remover número via AJAX - NOVA ESTRUTURA"""
    try:
        data = request.get_json()
        numero_id = data.get('numero_id')
        user_id = session['user']['id']
        
        if not numero_id:
            return jsonify({'success': False, 'message': 'ID do número é obrigatório'})
        
        # Verificar se o número pertence ao usuário
        numero_record = supabase.table('user_whatsapp').select('id, numero_whatsapp, principal').eq('id', numero_id).eq('user_id', user_id).eq('ativo', True).execute()
        
        if not numero_record.data:
            return jsonify({'success': False, 'message': 'Número não encontrado ou não pertence a você'})
        
        numero_info = numero_record.data[0]
        numero_whatsapp = numero_info['numero_whatsapp']
        is_principal = numero_info['principal']
        
        # Desativar o número
        supabase.table('user_whatsapp').update({
            'ativo': False
        }).eq('id', numero_id).execute()
        
        # Se era o número principal, definir outro como principal
        if is_principal:
            outros_numeros = supabase.table('user_whatsapp').select('id').eq('user_id', user_id).eq('ativo', True).neq('id', numero_id).limit(1).execute()
            
            if outros_numeros.data:
                # Definir outro número como principal
                supabase.table('user_whatsapp').update({
                    'principal': True
                }).eq('id', outros_numeros.data[0]['id']).execute()
        
        return jsonify({'success': True, 'message': f'Número {numero_whatsapp} removido com sucesso!'})
            
    except Exception as e:
        print(f"[ERROR] Erro ao remover número: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'message': 'Erro interno do servidor'})

# --- AJAX: Cancelar adesão - NOVA ESTRUTURA ---
@bp.route('/ajax/cancelar-adesao', methods=['POST'])
@login_required
@role_required(['cliente_unique', 'admin'])
def ajax_cancelar_adesao():
    """Cancelar adesão via AJAX - NOVA ESTRUTURA"""
    try:
        user_id = session['user']['id']
        
        # Desativar todos os números do usuário
        supabase.table('user_whatsapp').update({
            'ativo': False
        }).eq('user_id', user_id).execute()
        
        return jsonify({'success': True, 'message': 'Adesão cancelada com sucesso! Todos os números foram removidos.'})
        
    except Exception as e:
        print(f"[ERROR] Erro ao cancelar adesão: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'message': 'Erro interno do servidor'})

# --- AJAX: Definir número principal - NOVA ESTRUTURA ---
@bp.route('/ajax/set-principal', methods=['POST'])
@login_required
@role_required(['cliente_unique', 'admin'])
def ajax_set_principal():
    """Definir número como principal via AJAX - NOVA ESTRUTURA"""
    try:
        data = request.get_json()
        numero_id = data.get('numero_id')
        user_id = session['user']['id']
        
        if not numero_id:
            return jsonify({'success': False, 'message': 'ID do número é obrigatório'})
        
        # Verificar se o número pertence ao usuário
        numero_record = supabase.table('user_whatsapp').select('id').eq('id', numero_id).eq('user_id', user_id).eq('ativo', True).execute()
        
        if not numero_record.data:
            return jsonify({'success': False, 'message': 'Número não encontrado ou não pertence a você'})
        
        # Remover principal de todos os números do usuário
        supabase.table('user_whatsapp').update({
            'principal': False
        }).eq('user_id', user_id).execute()
        
        # Definir este número como principal
        supabase.table('user_whatsapp').update({
            'principal': True
        }).eq('id', numero_id).execute()
        
        return jsonify({'success': True, 'message': 'Número principal definido com sucesso!'})
            
    except Exception as e:
        print(f"[ERROR] Erro ao definir principal: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'message': 'Erro interno do servidor'})

# --- AJAX: Editar número - NOVA ESTRUTURA ---
@bp.route('/ajax/edit-numero', methods=['POST'])
@login_required
@role_required(['cliente_unique', 'admin'])
def ajax_edit_numero():
    """Editar informações do número via AJAX - NOVA ESTRUTURA"""
    try:
        data = request.get_json()
        numero_id = data.get('numero_id')
        nome_contato = data.get('nome_contato', '').strip()
        tipo_numero = data.get('tipo_numero', 'pessoal')
        user_id = session['user']['id']
        
        if not numero_id:
            return jsonify({'success': False, 'message': 'ID do número é obrigatório'})
        
        if not nome_contato:
            return jsonify({'success': False, 'message': 'Nome de contato é obrigatório'})
        
        # Verificar se o número pertence ao usuário
        numero_record = supabase.table('user_whatsapp').select('id').eq('id', numero_id).eq('user_id', user_id).eq('ativo', True).execute()
        
        if not numero_record.data:
            return jsonify({'success': False, 'message': 'Número não encontrado ou não pertence a você'})
        
        # Atualizar informações
        supabase.table('user_whatsapp').update({
            'nome_contato': nome_contato,
            'tipo_numero': tipo_numero
        }).eq('id', numero_id).execute()
        
        return jsonify({'success': True, 'message': 'Número atualizado com sucesso!'})
            
    except Exception as e:
        print(f"[ERROR] Erro ao editar número: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'message': 'Erro interno do servidor'})

# --- ÁREA ADMINISTRATIVA - REDIRECIONAMENTO ---
@bp.route('/admin')
@login_required
@role_required(['admin'])
def admin():
    """Redirecionar para a página principal (que já gerencia admins)"""
    return redirect(url_for('agente.index'))

@bp.route('/admin/data', methods=['GET'])
def admin_data():
    """API para buscar dados do painel administrativo - NOVA ESTRUTURA"""
    try:
        # Verificar se é uma requisição com bypass de API
        api_key = request.headers.get('X-API-Key')
        bypass_mode = api_key == 'uniq_api_2025_dev_bypass_key'
        
        print(f"[DEBUG] API Key recebida: {api_key}")
        print(f"[DEBUG] Bypass mode: {bypass_mode}")
        
        if not bypass_mode:
            # Verificar autenticação normal
            if 'user_id' not in session:
                print("[DEBUG] Usuário não autenticado e sem bypass")
                return jsonify({'success': False, 'message': 'Usuário não autenticado'}), 401
            
            # Verificar se é admin
            user_id = session.get('user_id')
            user_data = supabase_admin.table('users').select('*').eq('id', user_id).execute()
            
            if not user_data.data or user_data.data[0].get('role') != 'admin':
                print("[DEBUG] Usuário não é admin")
                return jsonify({'success': False, 'message': 'Acesso negado'}), 403
        
        print("[DEBUG] Prosseguindo com busca de dados...")
        
        # Buscar números WhatsApp
        whatsapp_response = supabase_admin.table('user_whatsapp').select('''
            id,
            user_id,
            numero_whatsapp,
            nome_contato,
            tipo_numero,
            ativo,
            principal,
            created_at
        ''').execute()
        
        # Buscar dados dos usuários
        users_response = supabase_admin.table('users').select('id, email, name, role').execute()
        
        # Buscar empresas vinculadas
        empresas_response = supabase_admin.table('user_empresas').select('''
            user_id,
            cad_clientes_sistema!inner(
                nome_cliente
            )
        ''').eq('ativo', True).execute()
        
        # Processar dados
        users_map = {}
        if users_response.data:
            for user in users_response.data:
                users_map[user['id']] = {
                    'email': user.get('email', 'N/A'),
                    'nome': user.get('name', 'Sem nome'),
                    'role': user.get('role', 'N/A')
                }
        
        # Mapear empresas por usuário
        empresas_map = {}
        if empresas_response.data:
            for vinculo in empresas_response.data:
                user_id = vinculo['user_id']
                empresa_nome = vinculo['cad_clientes_sistema']['nome_cliente']
                if user_id not in empresas_map:
                    empresas_map[user_id] = []
                empresas_map[user_id].append(empresa_nome)
        
        # Organizar usuários com números
        usuarios = {}
        numbers = []
        companies = []
        
        if whatsapp_response.data:
            for whatsapp in whatsapp_response.data:
                user_id = whatsapp['user_id']
                
                if user_id not in usuarios:
                    user_info = users_map.get(user_id, {})
                    usuarios[user_id] = {
                        'user_id': user_id,
                        'email': user_info.get('email', 'N/A'),
                        'nome': user_info.get('nome', 'Sem nome'),
                        'role': user_info.get('role', 'N/A'),
                        'numeros': [],
                        'empresas': empresas_map.get(user_id, []),
                        'usuario_ativo': False
                    }
                
                # Adicionar número
                numero_data = {
                    'id': whatsapp['id'],
                    'numero': whatsapp['numero_whatsapp'],
                    'nome': whatsapp['nome_contato'],
                    'tipo': whatsapp['tipo_numero'],
                    'principal': whatsapp['principal'],
                    'ativo': whatsapp['ativo']
                }
                usuarios[user_id]['numeros'].append(numero_data)
                
                if whatsapp['ativo']:
                    usuarios[user_id]['usuario_ativo'] = True
                
                # Para compatibilidade com front-end
                numbers.append({
                    'user_id': user_id,
                    'phone': whatsapp['numero_whatsapp']
                })
        
        # Criar lista de empresas para compatibilidade
        for user_id, empresa_list in empresas_map.items():
            for empresa in empresa_list:
                companies.append({
                    'user_id': user_id,
                    'nome': empresa
                })
        
        users_list = list(usuarios.values())
        
        # Calcular estatísticas
        stats = {
            'total_users': len(users_map),
            'active_users': len([u for u in users_list if u.get('usuario_ativo', False)]),
            'total_numbers': len(numbers),
            'total_companies': len(set([c['nome'] for c in companies]))
        }
        
        print(f"[DEBUG] Retornando dados: {len(users_list)} usuários, {len(numbers)} números")
        
        return jsonify({
            'success': True,
            'users': users_list,
            'numbers': numbers,
            'companies': companies,
            'stats': stats
        })
        
    except Exception as e:
        print(f"[ERROR] Erro ao buscar dados administrativos: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False, 
            'message': 'Erro interno do servidor',
            'error': str(e)
        }), 500

@bp.route('/admin/toggle-user', methods=['POST'])
@login_required
@role_required(['admin'])
def admin_toggle_user():
    """Admin: Ativar/desativar usuário - NOVA ESTRUTURA"""
    try:
        data = request.get_json()
        user_id = data.get('user_id')
        ativo = data.get('ativo', False)
        
        if not user_id:
            return jsonify({'success': False, 'message': 'ID do usuário é obrigatório'})
        
        # Ativar/desativar todos os números do usuário
        supabase_admin.table('user_whatsapp').update({
            'ativo': ativo
        }).eq('user_id', user_id).execute()
        
        status = 'ativado' if ativo else 'desativado'
        return jsonify({'success': True, 'message': f'Usuário {status} com sucesso!'})
        
    except Exception as e:
        print(f"[ERROR] Erro ao alterar status do usuário: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'message': 'Erro interno do servidor'})

@bp.route('/admin/add-numero', methods=['POST'])
@login_required
@role_required(['admin'])
def admin_add_numero():
    """Admin: Adicionar número para usuário - NOVA ESTRUTURA"""
    try:
        data = request.get_json()
        user_id = data.get('user_id')
        numero = data.get('numero', '').strip()
        nome_contato = data.get('nome_contato', '').strip()
        tipo_numero = data.get('tipo_numero', 'pessoal')
        
        if not user_id or not numero:
            return jsonify({'success': False, 'message': 'ID do usuário e número são obrigatórios'})
        
        if not nome_contato:
            nome_contato = f"Número {numero[-4:]}"  # Nome padrão baseado nos últimos 4 dígitos
        
        # Validar e formatar número
        is_valid, formatted_numero = validate_phone_number(numero)
        if not is_valid:
            return jsonify({'success': False, 'message': f'Número inválido: {formatted_numero}'})
        
        # Verificar se o número já existe
        existing = supabase_admin.table('user_whatsapp').select('id, user_id').eq('numero_whatsapp', formatted_numero).eq('ativo', True).execute()
        
        if existing.data:
            return jsonify({'success': False, 'message': 'Este número já está cadastrado'})
        
        # Verificar se é o primeiro número (será principal)
        user_numbers = supabase_admin.table('user_whatsapp').select('id').eq('user_id', user_id).eq('ativo', True).execute()
        is_first_number = not user_numbers.data
        
        # Inserir novo número
        data_insert = {
            'user_id': user_id,
            'numero_whatsapp': formatted_numero,
            'nome_contato': nome_contato,
            'tipo_numero': tipo_numero,
            'principal': is_first_number,
            'ativo': True
        }
        
        result = supabase_admin.table('user_whatsapp').insert(data_insert).execute()
        
        return jsonify({'success': True, 'message': 'Número adicionado com sucesso!'})
            
    except Exception as e:
        print(f"[ERROR] Erro ao adicionar número (admin): {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'message': 'Erro interno do servidor'})

@bp.route('/admin/remove-numero', methods=['POST'])
@login_required
@role_required(['admin'])
def admin_remove_numero():
    """Admin: Remover número de usuário - NOVA ESTRUTURA"""
    try:
        data = request.get_json()
        numero_id = data.get('numero_id')
        
        if not numero_id:
            return jsonify({'success': False, 'message': 'ID do número é obrigatório'})
        
        # Verificar se o número existe
        numero_record = supabase_admin.table('user_whatsapp').select('id, numero_whatsapp, user_id, principal').eq('id', numero_id).eq('ativo', True).execute()
        
        if not numero_record.data:
            return jsonify({'success': False, 'message': 'Número não encontrado'})
        
        numero_info = numero_record.data[0]
        numero_whatsapp = numero_info['numero_whatsapp']
        user_id = numero_info['user_id']
        is_principal = numero_info['principal']
        
        # Desativar o número
        supabase_admin.table('user_whatsapp').update({
            'ativo': False
        }).eq('id', numero_id).execute()
        
        # Se era o número principal, definir outro como principal
        if is_principal:
            outros_numeros = supabase_admin.table('user_whatsapp').select('id').eq('user_id', user_id).eq('ativo', True).neq('id', numero_id).limit(1).execute()
            
            if outros_numeros.data:
                # Definir outro número como principal
                supabase_admin.table('user_whatsapp').update({
                    'principal': True
                }).eq('id', outros_numeros.data[0]['id']).execute()
        
        return jsonify({'success': True, 'message': f'Número {numero_whatsapp} removido com sucesso!'})
            
    except Exception as e:
        print(f"[ERROR] Erro ao remover número (admin): {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'message': 'Erro interno do servidor'})

# --- NOVOS ENDPOINTS PARA ADMINISTRADORES ---

@bp.route('/api/admin/users-summary', methods=['GET'])
@login_required
@role_required(['admin'])
def api_admin_users_summary():
    """API: Resumo completo de usuários para administradores"""
    try:
        # Parâmetros de busca e filtro
        search = request.args.get('search', '').strip()
        status_filter = request.args.get('status', 'all')  # all, active, inactive
        company_filter = request.args.get('company', '').strip()
        page = int(request.args.get('page', 1))
        per_page = int(request.args.get('per_page', 20))
        
        # Buscar todos os agentes
        agentes_query = supabase_admin.table('clientes_agentes').select('*')
        
        # Aplicar filtro de status
        if status_filter == 'active':
            agentes_query = agentes_query.eq('usuario_ativo', True)
        elif status_filter == 'inactive':
            agentes_query = agentes_query.eq('usuario_ativo', False)
        
        agentes_result = agentes_query.execute()
        
        # Buscar informações dos usuários
        users_result = supabase_admin.table('users').select('id, email, name').execute()
        
        # Criar mapeamento de usuários
        users_map = {}
        if users_result.data:
            for user in users_result.data:
                users_map[user['id']] = {
                    'email': user.get('email', ''),
                    'nome': user.get('name', '')  # Mapear name para nome
                }
        
        # Processar e filtrar dados
        agentes = []
        stats = {
            'total_users': 0,
            'active_users': 0,
            'total_numbers': 0,
            'total_companies': 0,
            'users_by_company': {}
        }
        
        if agentes_result.data:
            for agente in agentes_result.data:
                user_info = users_map.get(agente['user_id'], {})
                nome = user_info.get('nome', 'N/A')
                email = user_info.get('email', 'N/A')
                
                # Aplicar filtro de busca
                if search:
                    search_text = f"{nome} {email}".lower()
                    if search.lower() not in search_text:
                        continue
                
                # Processar números
                numeros = agente.get('numero', [])
                if isinstance(numeros, str):
                    numeros = [numeros] if numeros else []
                elif not isinstance(numeros, list):
                    numeros = []
                
                # Processar empresas
                empresas = agente.get('empresa', [])
                if not isinstance(empresas, list):
                    empresas = []
                
                # Aplicar filtro de empresa
                if company_filter:
                    empresa_found = False
                    for empresa in empresas:
                        cnpj = empresa if isinstance(empresa, str) else empresa.get('cnpj', '')
                        if company_filter in cnpj:
                            empresa_found = True
                            break
                    if not empresa_found:
                        continue
                
                agente_data = {
                    'user_id': agente['user_id'],
                    'nome': nome,
                    'email': email,
                    'numeros': numeros,
                    'empresas': empresas,
                    'usuario_ativo': agente.get('usuario_ativo', False),
                    'aceite_termos': agente.get('aceite_termos', False),
                    'created_at': agente.get('created_at', ''),
                    'data_aceite': agente.get('data_aceite', ''),
                    'last_activity': agente.get('updated_at', '')
                }
                
                agentes.append(agente_data)
                
                # Atualizar estatísticas
                stats['total_users'] += 1
                if agente_data['usuario_ativo']:
                    stats['active_users'] += 1
                stats['total_numbers'] += len(numeros)
                
                # Contabilizar empresas
                for empresa in empresas:
                    cnpj = empresa if isinstance(empresa, str) else empresa.get('cnpj', 'N/A')
                    stats['users_by_company'][cnpj] = stats['users_by_company'].get(cnpj, 0) + 1
        
        stats['total_companies'] = len(stats['users_by_company'])
        
        # Implementar paginação
        total_items = len(agentes)
        start_idx = (page - 1) * per_page
        end_idx = start_idx + per_page
        agentes_paginated = agentes[start_idx:end_idx]
        
        return jsonify({
            'success': True,
            'users': agentes_paginated,
            'stats': stats,
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total_items': total_items,
                'total_pages': (total_items + per_page - 1) // per_page
            }
        })
        
    except Exception as e:
        print(f"[ERROR] Erro ao buscar resumo de usuários: {str(e)}")
        traceback.print_exc()
        return jsonify({'success': False, 'message': 'Erro interno do servidor'})

@bp.route('/admin/bulk-actions', methods=['POST'])
@login_required
@role_required(['admin'])
def admin_bulk_actions():
    """Admin: Ações em massa - NOVA ESTRUTURA"""
    try:
        data = request.get_json()
        action = data.get('action')
        user_ids = data.get('user_ids', [])
        
        if not action or not user_ids:
            return jsonify({'success': False, 'message': 'Ação e IDs de usuários são obrigatórios'})
        
        if action == 'activate':
            # Ativar todos os números dos usuários
            for user_id in user_ids:
                supabase_admin.table('user_whatsapp').update({
                    'ativo': True
                }).eq('user_id', user_id).execute()
            
            return jsonify({'success': True, 'message': f'{len(user_ids)} usuários ativados com sucesso!'})
            
        elif action == 'deactivate':
            # Desativar todos os números dos usuários
            for user_id in user_ids:
                supabase_admin.table('user_whatsapp').update({
                    'ativo': False
                }).eq('user_id', user_id).execute()
            
            return jsonify({'success': True, 'message': f'{len(user_ids)} usuários desativados com sucesso!'})
            
        elif action == 'export':
            # Exportar dados (retornar dados para download)
            export_data = []
            for user_id in user_ids:
                # Buscar números do usuário
                numeros = get_user_whatsapp_numbers(user_id)
                # Buscar empresas do usuário
                empresas = get_user_companies(user_id)
                # Buscar info do usuário
                user_info = supabase_admin.table('users').select('email, name, role').eq('id', user_id).execute()
                
                user_data = {
                    'user_id': user_id,
                    'email': user_info.data[0].get('email', 'N/A') if user_info.data else 'N/A',
                    'nome': user_info.data[0].get('name', 'N/A') if user_info.data else 'N/A',
                    'role': user_info.data[0].get('role', 'N/A') if user_info.data else 'N/A',
                    'numeros': numeros,
                    'empresas': empresas
                }
                export_data.append(user_data)
            
            return jsonify({'success': True, 'data': export_data, 'message': 'Dados exportados com sucesso!'})
            
        else:
            return jsonify({'success': False, 'message': 'Ação não reconhecida'})
            
    except Exception as e:
        print(f"[ERROR] Erro em ações em massa: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'message': 'Erro interno do servidor'})



@bp.route('/debug-direct')
@login_required 
def debug_direct():
    """Teste direto da função get_user_companies"""
    try:
        user_id = session.get('user', {}).get('id')
        print(f"[DEBUG DIRECT] === INICIANDO TESTE DIRETO ===")
        print(f"[DEBUG DIRECT] User ID: {user_id}")
        
        # Chamar diretamente a função get_user_companies
        print(f"[DEBUG DIRECT] Chamando get_user_companies({user_id})...")
        empresas = get_user_companies(user_id)
        print(f"[DEBUG DIRECT] Resultado: {empresas}")
        print(f"[DEBUG DIRECT] === FIM TESTE DIRETO ===")
        
        return jsonify({
            "user_id": user_id,
            "empresas": empresas,
            "total": len(empresas)
        })
        
    except Exception as e:
        print(f"[DEBUG DIRECT ERROR] {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)})


@bp.route('/debug-join')
@login_required 
def debug_join():
    """Debug detalhado do JOIN"""
    try:
        user_id = session.get('user', {}).get('id')
        print(f"[DEBUG JOIN] User ID: {user_id}")
        
        # 1. Verificar user_empresas sem JOIN
        print("[DEBUG JOIN] 1. Verificando user_empresas...")
        user_empresas = supabase.table('user_empresas').select('*').eq('user_id', user_id).execute()
        print(f"[DEBUG JOIN] user_empresas encontrados: {len(user_empresas.data)}")
        
        result = {
            "user_id": user_id,
            "step1_user_empresas": user_empresas.data,
            "step2_join_results": [],
            "step3_manual_lookup": []
        }
        
        if not user_empresas.data:
            return jsonify(result)
        
        # 2. Verificar JOIN com diferentes sintaxes
        print("[DEBUG JOIN] 2. Testando JOIN com diferentes sintaxes...")
        
        # Sintaxe atual
        try:
            join1 = supabase.table('user_empresas').select(
                '*, cad_clientes_sistema!inner(id, nome_cliente, cnpjs)'
            ).eq('user_id', user_id).eq('ativo', True).execute()
            result["step2_join_results"].append({
                "syntax": "!inner",
                "success": True,
                "data": join1.data
            })
        except Exception as e:
            result["step2_join_results"].append({
                "syntax": "!inner", 
                "success": False,
                "error": str(e)
            })
        
        # Sintaxe alternativa 1
        try:
            join2 = supabase.table('user_empresas').select(
                '*, cad_clientes_sistema(id, nome_cliente, cnpjs)'
            ).eq('user_id', user_id).eq('ativo', True).execute()
            result["step2_join_results"].append({
                "syntax": "sem !inner",
                "success": True,
                "data": join2.data
            })
        except Exception as e:
            result["step2_join_results"].append({
                "syntax": "sem !inner",
                "success": False,
                "error": str(e)
            })
        
        # 3. Lookup manual dos cliente_sistema_ids
        print("[DEBUG JOIN] 3. Fazendo lookup manual...")
        for vinculo in user_empresas.data:
            cliente_sistema_id = vinculo.get('cliente_sistema_id')
            if cliente_sistema_id:
                try:
                    cliente = supabase.table('cad_clientes_sistema').select('*').eq('id', cliente_sistema_id).execute()
                    result["step3_manual_lookup"].append({
                        "cliente_sistema_id": cliente_sistema_id,
                        "found": len(cliente.data) > 0,
                        "data": cliente.data[0] if cliente.data else None
                    })
                except Exception as e:
                    result["step3_manual_lookup"].append({
                        "cliente_sistema_id": cliente_sistema_id,
                        "found": False,
                        "error": str(e)
                    })
        
        return jsonify(result)
        
    except Exception as e:
        print(f"[DEBUG JOIN ERROR] {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)})


@bp.route('/debug-empresas')
@login_required
def debug_empresas():
    """Endpoint para debugar empresas"""
    try:
        user_id = session.get('user', {}).get('id')
        print(f"[DEBUG] User ID da sessão: {user_id}")
        
        if not user_id:
            return jsonify({"error": "User ID não encontrado na sessão", "session": dict(session)})
        
        # Buscar empresas
        empresas = get_user_companies(user_id)
        print(f"[DEBUG] Empresas retornadas: {empresas}")
        
        return jsonify({
            "user_id": user_id,
            "empresas": empresas,
            "total_empresas": len(empresas)
        })
        
    except Exception as e:
        print(f"[DEBUG ERROR] {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)})


