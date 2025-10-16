"""
API endpoints para gerenciar dados de armazenagem Kingspan
Tabela: importacoes_processos_armazenagem_kingspan
Acesso: Somente analistas internos com acesso ao cliente Kingspan
"""
from flask import Blueprint, jsonify, request, session
from extensions import supabase_admin
from routes.auth import login_required
from routes.api import get_user_companies
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

# Blueprint específico para API de armazenagem
api_armazenagem_bp = Blueprint('api_armazenagem', __name__, url_prefix='/api/armazenagem')

# Log de criação do blueprint
logger.info(f"[API_ARMAZENAGEM] 🏗️ Blueprint criado com url_prefix='/api/armazenagem'")
print(f"[API_ARMAZENAGEM] 🏗️ Blueprint 'api_armazenagem' criado!")

# CNPJ do cliente Kingspan - configure conforme necessário
KINGSPAN_CNPJ = None  # Será detectado dinamicamente pelos CNPJs do usuário

def is_kingspan_user(user_data):
    """
    Verificar se o usuário tem acesso ao cliente Kingspan
    Returns: (bool, list, bool) - (tem_acesso, lista_de_cnpjs_kingspan, pode_editar)
    
    REGRAS:
    - cliente_unique (Kingspan): pode VER (read-only)
    - interno_unique (analistas Kingspan): pode EDITAR
    - interno_unique (admin_operacao, master_admin): pode EDITAR (todos os Kingspan)
    """
    try:
        role = user_data.get('role')
        perfil_principal = user_data.get('perfil_principal', '')
        user_email = user_data.get('email', 'unknown')
        
        logger.info(f"[ARMAZENAGEM] ===== Verificando acesso para {user_email} =====")
        logger.info(f"[ARMAZENAGEM] Role: {role}")
        logger.info(f"[ARMAZENAGEM] Perfil Principal: {perfil_principal}")
        
        # VERIFICAÇÃO ESPECIAL: Admins master/operação têm acesso SEMPRE
        if perfil_principal in ['admin_operacao', 'master_admin']:
            logger.info(f"[ARMAZENAGEM] ✅ ADMIN DETECTADO ({perfil_principal}) - Concedendo acesso total")
            
            # Buscar TODOS os CNPJs Kingspan do sistema
            kingspan_cnpjs = []
            try:
                result = supabase_admin.table('importacoes_processos_aberta')\
                    .select('cnpj_importador, importador')\
                    .execute()
                
                if result.data:
                    seen_cnpjs = set()
                    for row in result.data:
                        importador = row.get('importador', '').upper()
                        cnpj = row.get('cnpj_importador')
                        if cnpj and cnpj not in seen_cnpjs:
                            if 'KINGSPAN' in importador or 'KING SPAN' in importador:
                                kingspan_cnpjs.append(cnpj)
                                seen_cnpjs.add(cnpj)
                                logger.info(f"[ARMAZENAGEM] CNPJ Kingspan encontrado: {cnpj} - {importador}")
                
                logger.info(f"[ARMAZENAGEM] Admin vê {len(kingspan_cnpjs)} CNPJs Kingspan do sistema")
                
                if kingspan_cnpjs:
                    return True, kingspan_cnpjs, True  # Tem acesso, lista de CNPJs, pode editar
                else:
                    logger.warning(f"[ARMAZENAGEM] ⚠️ Nenhum processo Kingspan encontrado no sistema")
                    return False, [], False  # Sem processos Kingspan, sem acesso
                    
            except Exception as e:
                logger.error(f"[ARMAZENAGEM] Erro ao buscar CNPJs Kingspan: {str(e)}")
                return False, [], False
        
        # Para não-admins, precisa ter CNPJs associados
        user_cnpjs = get_user_companies(user_data)
        if not user_cnpjs:
            logger.warning(f"[ARMAZENAGEM] Usuário {user_email} não tem CNPJs associados e não é admin")
            return False, [], False
        
        logger.info(f"[ARMAZENAGEM] Usuário tem {len(user_cnpjs)} CNPJs associados")
        
        # Buscar CNPJs que contém "KINGSPAN" no nome da empresa
        kingspan_cnpjs = []
        for cnpj in user_cnpjs:
            # Consultar nome da empresa pelo CNPJ
            result = supabase_admin.table('importacoes_processos_aberta')\
                .select('importador')\
                .eq('cnpj_importador', cnpj)\
                .limit(1)\
                .execute()
            
            if result.data:
                importador = result.data[0].get('importador', '').upper()
                if 'KINGSPAN' in importador or 'KING SPAN' in importador:
                    kingspan_cnpjs.append(cnpj)
                    logger.info(f"[ARMAZENAGEM] CNPJ Kingspan encontrado: {cnpj} - {importador}")
        
        if not kingspan_cnpjs:
            logger.warning(f"[ARMAZENAGEM] Usuário {user_email} não tem CNPJs Kingspan associados")
            return False, [], False
        
        # Determinar permissões baseado na role
        can_edit = False
        
        if role == 'interno_unique':
            # Internos sempre podem editar
            can_edit = True
            logger.info(f"[ARMAZENAGEM] Interno {user_email}: pode EDITAR {len(kingspan_cnpjs)} CNPJs Kingspan")
        elif role == 'cliente_unique':
            # Clientes só podem visualizar
            can_edit = False
            logger.info(f"[ARMAZENAGEM] Cliente {user_email}: pode VER (read-only) {len(kingspan_cnpjs)} CNPJs Kingspan")
        else:
            logger.warning(f"[ARMAZENAGEM] Role desconhecido: {role}")
            return False, [], False
        
        return True, kingspan_cnpjs, can_edit
            
    except Exception as e:
        logger.error(f"[ARMAZENAGEM] Erro ao verificar acesso Kingspan: {str(e)}")
        import traceback
        traceback.print_exc()
        return False, [], False

def validate_ref_unique_belongs_to_kingspan(ref_unique, kingspan_cnpjs):
    """
    Validar se o ref_unique pertence a um processo Kingspan
    """
    try:
        result = supabase_admin.table('importacoes_processos_aberta')\
            .select('cnpj_importador, importador')\
            .eq('ref_unique', ref_unique)\
            .limit(1)\
            .execute()
        
        if not result.data:
            logger.warning(f"[ARMAZENAGEM] ref_unique {ref_unique} não encontrado")
            return False, "Processo não encontrado"
        
        processo = result.data[0]
        cnpj = processo.get('cnpj_importador')
        
        if cnpj not in kingspan_cnpjs:
            logger.warning(f"[ARMAZENAGEM] ref_unique {ref_unique} não pertence aos CNPJs Kingspan do usuário")
            return False, "Acesso negado: processo não pertence ao cliente Kingspan associado"
        
        return True, None
        
    except Exception as e:
        logger.error(f"[ARMAZENAGEM] Erro ao validar ref_unique: {str(e)}")
        return False, f"Erro na validação: {str(e)}"

@api_armazenagem_bp.route('/<path:ref_unique>', methods=['GET'])
@login_required
def get_armazenagem(ref_unique):
    """
    GET /api/armazenagem/<path:ref_unique>
    Buscar dados de armazenagem para um processo específico
    ACESSO: Clientes e Internos Kingspan (read-only para clientes)
    """
    try:
        user_data = session.get('user')
        if not user_data:
            return jsonify({'error': 'Usuário não autenticado'}), 401
        
        # Verificar acesso Kingspan
        tem_acesso, kingspan_cnpjs, can_edit = is_kingspan_user(user_data)
        if not tem_acesso:
            return jsonify({'error': 'Acesso negado: usuário não tem permissão para visualizar dados de armazenagem Kingspan'}), 403
        
        # Validar se ref_unique pertence a Kingspan
        is_valid, error_msg = validate_ref_unique_belongs_to_kingspan(ref_unique, kingspan_cnpjs)
        if not is_valid:
            return jsonify({'error': error_msg}), 403
        
        # Buscar dados de armazenagem
        result = supabase_admin.table('importacoes_processos_armazenagem_kingspan')\
            .select('*')\
            .eq('ref_unique', ref_unique)\
            .limit(1)\
            .execute()
        
        if result.data:
            armazenagem = result.data[0]
            # Converter datas para formato DD/MM/YYYY para o frontend
            for date_field in ['data_desova', 'limite_primeiro_periodo', 'limite_segundo_periodo']:
                if armazenagem.get(date_field):
                    try:
                        date_obj = datetime.fromisoformat(armazenagem[date_field].replace('Z', '+00:00'))
                        armazenagem[date_field] = date_obj.strftime('%d/%m/%Y')
                    except:
                        pass
            
            logger.info(f"[ARMAZENAGEM] Dados encontrados para {ref_unique}")
            return jsonify({
                'success': True, 
                'data': armazenagem,
                'can_edit': can_edit  # Informar se usuário pode editar
            })
        else:
            logger.info(f"[ARMAZENAGEM] Nenhum dado encontrado para {ref_unique}")
            return jsonify({
                'success': True, 
                'data': None,
                'can_edit': can_edit  # Informar se usuário pode editar
            })
            
    except Exception as e:
        logger.error(f"[ARMAZENAGEM] Erro ao buscar dados: {str(e)}")
        return jsonify({'error': f'Erro ao buscar dados: {str(e)}'}), 500

@api_armazenagem_bp.route('/<path:ref_unique>', methods=['POST', 'PUT'])
@login_required
def save_armazenagem(ref_unique):
    """
    POST/PUT /api/armazenagem/<path:ref_unique>
    Criar ou atualizar dados de armazenagem para um processo
    ACESSO: Somente internos e admins podem EDITAR
    """
    logger.info(f"[API_ARMAZENAGEM] 📝 Requisição {request.method} recebida para {ref_unique}")
    print(f"[API_ARMAZENAGEM] 📝 {request.method} /api/armazenagem/{ref_unique}")
    
    try:
        user_data = session.get('user')
        if not user_data:
            logger.warning(f"[API_ARMAZENAGEM] Usuário não autenticado")
            return jsonify({'error': 'Usuário não autenticado'}), 401
        
        # Verificar acesso Kingspan
        tem_acesso, kingspan_cnpjs, can_edit = is_kingspan_user(user_data)
        if not tem_acesso:
            return jsonify({'error': 'Acesso negado: usuário não tem acesso aos dados Kingspan'}), 403
        
        # Clientes não podem editar
        if not can_edit:
            return jsonify({'error': 'Acesso negado: somente analistas internos e administradores podem editar'}), 403
        
        # Validar se ref_unique pertence a Kingspan
        is_valid, error_msg = validate_ref_unique_belongs_to_kingspan(ref_unique, kingspan_cnpjs)
        if not is_valid:
            return jsonify({'error': error_msg}), 403
        
        # Validar e processar dados do request
        data = request.json
        if not data:
            return jsonify({'error': 'Dados inválidos'}), 400
        
        # Processar e validar campos
        armazenagem_data = {
            'ref_unique': ref_unique
        }
        
        # Processar datas (converter DD/MM/YYYY para YYYY-MM-DD)
        date_fields = ['data_desova', 'limite_primeiro_periodo', 'limite_segundo_periodo']
        for field in date_fields:
            if data.get(field):
                try:
                    # Aceitar tanto DD/MM/YYYY quanto YYYY-MM-DD
                    date_str = data[field]
                    if '/' in date_str:
                        # DD/MM/YYYY
                        date_obj = datetime.strptime(date_str, '%d/%m/%Y')
                    else:
                        # YYYY-MM-DD
                        date_obj = datetime.strptime(date_str, '%Y-%m-%d')
                    armazenagem_data[field] = date_obj.strftime('%Y-%m-%d')
                except ValueError:
                    return jsonify({'error': f'Data inválida para {field}: {data[field]}'}), 400
            else:
                armazenagem_data[field] = None
        
        # Processar campo numérico inteiro
        if data.get('dias_extras_armazenagem') is not None:
            try:
                armazenagem_data['dias_extras_armazenagem'] = int(data['dias_extras_armazenagem'])
            except ValueError:
                return jsonify({'error': f'Valor inválido para dias_extras_armazenagem: {data["dias_extras_armazenagem"]}'}), 400
        else:
            armazenagem_data['dias_extras_armazenagem'] = None
        
        # Processar campo numérico decimal
        if data.get('valor_despesas_extras') is not None:
            try:
                armazenagem_data['valor_despesas_extras'] = float(data['valor_despesas_extras'])
            except ValueError:
                return jsonify({'error': f'Valor inválido para valor_despesas_extras: {data["valor_despesas_extras"]}'}), 400
        else:
            armazenagem_data['valor_despesas_extras'] = None
        
        # Verificar se registro já existe
        existing = supabase_admin.table('importacoes_processos_armazenagem_kingspan')\
            .select('id')\
            .eq('ref_unique', ref_unique)\
            .limit(1)\
            .execute()
        
        if existing.data:
            # UPDATE
            result = supabase_admin.table('importacoes_processos_armazenagem_kingspan')\
                .update(armazenagem_data)\
                .eq('ref_unique', ref_unique)\
                .execute()
            
            logger.info(f"[ARMAZENAGEM] Dados atualizados para {ref_unique} por {user_data.get('email')}")
            return jsonify({
                'success': True, 
                'message': 'Dados de armazenagem atualizados com sucesso',
                'data': result.data[0] if result.data else None
            })
        else:
            # INSERT
            result = supabase_admin.table('importacoes_processos_armazenagem_kingspan')\
                .insert(armazenagem_data)\
                .execute()
            
            logger.info(f"[ARMAZENAGEM] Dados criados para {ref_unique} por {user_data.get('email')}")
            return jsonify({
                'success': True, 
                'message': 'Dados de armazenagem criados com sucesso',
                'data': result.data[0] if result.data else None
            })
            
    except Exception as e:
        logger.error(f"[ARMAZENAGEM] Erro ao salvar dados: {str(e)}")
        return jsonify({'error': f'Erro ao salvar dados: {str(e)}'}), 500

@api_armazenagem_bp.route('/<path:ref_unique>', methods=['DELETE'])
@login_required
def delete_armazenagem(ref_unique):
    """
    DELETE /api/armazenagem/<path:ref_unique>
    Deletar dados de armazenagem para um processo
    ACESSO: Somente internos e admins podem DELETAR
    """
    try:
        user_data = session.get('user')
        if not user_data:
            return jsonify({'error': 'Usuário não autenticado'}), 401
        
        # Verificar acesso Kingspan
        tem_acesso, kingspan_cnpjs, can_edit = is_kingspan_user(user_data)
        if not tem_acesso:
            return jsonify({'error': 'Acesso negado: usuário não tem acesso aos dados Kingspan'}), 403
        
        # Clientes não podem deletar
        if not can_edit:
            return jsonify({'error': 'Acesso negado: somente analistas internos e administradores podem deletar'}), 403
        
        # Validar se ref_unique pertence a Kingspan
        is_valid, error_msg = validate_ref_unique_belongs_to_kingspan(ref_unique, kingspan_cnpjs)
        if not is_valid:
            return jsonify({'error': error_msg}), 403
        
        # Deletar registro
        result = supabase_admin.table('importacoes_processos_armazenagem_kingspan')\
            .delete()\
            .eq('ref_unique', ref_unique)\
            .execute()
        
        logger.info(f"[ARMAZENAGEM] Dados deletados para {ref_unique} por {user_data.get('email')}")
        return jsonify({'success': True, 'message': 'Dados de armazenagem deletados com sucesso'})
        
    except Exception as e:
        logger.error(f"[ARMAZENAGEM] Erro ao deletar dados: {str(e)}")
        return jsonify({'error': f'Erro ao deletar dados: {str(e)}'}), 500

# Endpoint para verificar se usuário tem acesso Kingspan
@api_armazenagem_bp.route('/check-access', methods=['GET'])
@login_required
def check_kingspan_access():
    """
    GET /api/armazenagem/check-access
    Verificar se usuário atual tem acesso aos recursos de armazenagem Kingspan
    Retorna: has_access (pode ver), can_edit (pode editar), can_view (pode visualizar)
    """
    try:
        user_data = session.get('user')
        if not user_data:
            return jsonify({'error': 'Usuário não autenticado'}), 401
        
        tem_acesso, kingspan_cnpjs, can_edit = is_kingspan_user(user_data)
        
        return jsonify({
            'success': True,
            'has_access': tem_acesso,  # Pode ver a coluna/funcionalidade
            'can_edit': can_edit,      # Pode editar dados
            'can_view': tem_acesso,    # Pode visualizar dados (sempre igual a has_access)
            'kingspan_cnpjs': kingspan_cnpjs,
            'user_role': user_data.get('role'),
            'perfil_principal': user_data.get('perfil_principal', '')
        })
        
    except Exception as e:
        logger.error(f"[ARMAZENAGEM] Erro ao verificar acesso: {str(e)}")
        return jsonify({'error': f'Erro ao verificar acesso: {str(e)}'}), 500
