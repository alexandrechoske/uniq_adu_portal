# ConciliaÃ§Ã£o BancÃ¡ria V2 - Routes Integradas com Motor de ConciliaÃ§Ã£o
from flask import Blueprint, render_template, request, session, jsonify, flash, redirect, url_for, send_file
from werkzeug.utils import secure_filename
import os
import pandas as pd
import logging
from datetime import datetime, timedelta
from extensions import supabase, supabase_admin
from decorators.perfil_decorators import perfil_required
from modules.auth.routes import login_required
from services.access_logger import access_logger
import tempfile
import uuid
import re
from typing import Dict, List, Tuple, Optional
import io
import json
from decimal import Decimal

# Import do nosso motor de conciliaÃ§Ã£o
from .bank_parser import BankFileParser
from .conciliacao_service import ConciliacaoService
from .conciliacao_integrator import ConciliacaoIntegrator

# Configurar blueprint
conciliacao_v2_bp = Blueprint('fin_conciliacao_v2', __name__, 
                             template_folder='templates',
                             static_folder='static', 
                             static_url_path='/static/fin_conciliacao_v2',
                             url_prefix='/financeiro/conciliacao-v2')

# Configurar logging
logger = logging.getLogger(__name__)

# ConfiguraÃ§Ãµes
UPLOAD_FOLDER = '/tmp/conciliacao_v2_uploads'
ALLOWED_EXTENSIONS = {'xlsx', 'xls', 'csv', 'txt'}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB

# Criar pasta de upload se nÃ£o existir
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Bypass API key para testes
API_BYPASS_KEY = os.getenv('API_BYPASS_KEY', 'uniq_api_2025_dev_bypass_key')

# Armazenamento temporário para sessões de bypass (em produção usar Redis/cache)
bypass_sessions = {}

def get_bypass_session_id():
    """Obtém ou cria um ID de sessão para bypass"""
    session_id = request.headers.get('X-Session-ID')
    if not session_id:
        import uuid
        session_id = str(uuid.uuid4())
    return session_id

def get_bypass_session_data(session_id):
    """Obtém dados da sessão de bypass"""
    return bypass_sessions.get(session_id, {})

def set_bypass_session_data(session_id, key, value):
    """Define dados na sessão de bypass"""
    if session_id not in bypass_sessions:
        bypass_sessions[session_id] = {}
    bypass_sessions[session_id][key] = value

def verificar_api_bypass():
    """Verifica se a requisição tem bypass de API"""
    return request.headers.get('X-API-Key') == API_BYPASS_KEY

class ConciliacaoManager:
    """Classe para gerenciar todo o processo de conciliaÃ§Ã£o"""
    
    def __init__(self):
        self.parser = BankFileParser()
        self.conciliacao_service = ConciliacaoService()
        self.integrador = ConciliacaoIntegrator()
    
    def detect_bank_type(self, file_content, filename):
        """Detecta automaticamente o tipo de banco baseado no conteÃºdo"""
        filename_lower = filename.lower()
        
        # Detecta por nome do arquivo
        if 'brasil' in filename_lower or 'bb' in filename_lower:
            return 'BANCO_DO_BRASIL'
        elif 'santander' in filename_lower:
            return 'BANCO_SANTANDER'  
        elif 'itau' in filename_lower or 'itaÃº' in filename_lower:
            return 'BANCO_ITAU'
        
        # Detecta por extensÃ£o
        if filename_lower.endswith('.txt'):
            return 'BANCO_ITAU'  # ItaÃº usa TXT
        elif filename_lower.endswith(('.xlsx', '.xls')):
            # Tenta detectar pelo conteÃºdo do Excel
            try:
                if isinstance(file_content, pd.DataFrame):
                    columns = [col.lower() for col in file_content.columns]
                    
                    # PadrÃµes do Banco do Brasil
                    if any('extrato' in col for col in columns):
                        return 'BANCO_DO_BRASIL'
                    
                    # PadrÃµes do Santander
                    if 'agencia' in columns or 'conta' in columns:
                        return 'BANCO_SANTANDER'
                        
            except Exception:
                pass
        
        return 'BANCO_DO_BRASIL'  # Default

# InstÃ¢ncia global do manager
conciliacao_manager = ConciliacaoManager()

@conciliacao_v2_bp.route('/')
@login_required
@perfil_required('admin', 'interno_unique')
def index():
    """PÃ¡gina principal da conciliaÃ§Ã£o V2"""
    access_logger.log_access(
        'page_access',
        user_id=session.get('user_id'),
        action='page_view',
        resource='conciliacao_v2',
        details={'page': 'index'}
    )
    
    return render_template('conciliacao_lancamentos/conciliacao_v2.html')

@conciliacao_v2_bp.route('/api/upload-arquivo', methods=['POST'])
@login_required
@perfil_required('admin', 'interno_unique')
def upload_arquivo():
    """Upload e processamento de arquivo bancÃ¡rio"""
    try:
        # Verificar se é bypass para usar armazenamento alternativo
        is_bypass = verificar_api_bypass()
        session_id = get_bypass_session_id() if is_bypass else None
        if 'arquivo' not in request.files:
            return jsonify({'success': False, 'message': 'Nenhum arquivo enviado'}), 400
        
        arquivo = request.files['arquivo']
        if arquivo.filename == '':
            return jsonify({'success': False, 'message': 'Nenhum arquivo selecionado'}), 400
        
        # Validar extensÃ£o
        filename = secure_filename(arquivo.filename)
        if not any(filename.lower().endswith(ext) for ext in ['.xlsx', '.xls', '.txt', '.csv']):
            return jsonify({'success': False, 'message': 'Tipo de arquivo nÃ£o suportado'}), 400
        
        # Salvar arquivo temporÃ¡rio
        temp_path = os.path.join(UPLOAD_FOLDER, f"{uuid.uuid4()}_{filename}")
        arquivo.save(temp_path)
        
        try:
            # Detectar tipo do banco
            banco_tipo = request.form.get('banco_origem', 'auto')
            if banco_tipo == 'auto':
                # Ler arquivo para detectar tipo
                if filename.lower().endswith('.txt'):
                    banco_tipo = 'BANCO_ITAU'
                else:
                    df = pd.read_excel(temp_path, engine='openpyxl')
                    banco_tipo = conciliacao_manager.detect_bank_type(df, filename)
            
            # Processar arquivo com nosso motor
            resultado_parser = conciliacao_manager.parser.parse_file(temp_path, banco_tipo)
            
            # Verificar se houve erro no parsing
            if "erro" in resultado_parser:
                return jsonify({'success': False, 'message': resultado_parser["erro"]}), 400
            
            # Extrair movimentos do resultado
            movimentos_banco = resultado_parser.get("movimentos", [])
            
            # Converter para formato JSON
            movimentos_json = []
            for mov in movimentos_banco:
                # mov é um dicionário, não um objeto
                movimentos_json.append({
                    'id': f"banco_{len(movimentos_json)}",
                    'data': mov.get('data', ''),
                    'data_iso': mov.get('data', ''),
                    'valor': float(mov.get('valor', 0)),
                    'valor_formatado': f"R$ {mov.get('valor', 0):,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.'),
                    'descricao': mov.get('descricao', ''),
                    'banco': resultado_parser.get('banco', banco_tipo),
                    'conta': resultado_parser.get('conta', ''),
                    'tipo': mov.get('tipo', ''),
                    'codigo_referencia': mov.get('codigo_referencia', ''),
                    'linha_origem': mov.get('linha_origem', 0)
                })
            
            # Armazenar na sessÃ£o (ou bypass_sessions)
            if is_bypass and session_id:
                arquivos_processados = get_bypass_session_data(session_id).get('arquivos_processados', {})
                arquivos_processados[banco_tipo] = {
                    'filename': filename,
                    'movimentos': movimentos_json,
                    'total': len(movimentos_json),
                    'upload_time': datetime.now().isoformat()
                }
                set_bypass_session_data(session_id, 'arquivos_processados', arquivos_processados)
            else:
                if 'arquivos_processados' not in session:
                    session['arquivos_processados'] = {}
                
                session['arquivos_processados'][banco_tipo] = {
                    'filename': filename,
                    'movimentos': movimentos_json,
                    'total': len(movimentos_json),
                    'upload_time': datetime.now().isoformat()
                }
                session.modified = True
            
            access_logger.log_access(
                'api_call',
                user_id=session.get('user_id'),
                action='file_upload',
                resource='conciliacao_v2',
                details={
                    'filename': filename,
                    'banco_tipo': banco_tipo,
                    'total_movimentos': len(movimentos_json)
                }
            )
            
            return jsonify({
                'success': True,
                'message': f'Arquivo processado com sucesso! {len(movimentos_json)} movimentos encontrados.',
                'banco_tipo': banco_tipo,
                'total_movimentos': len(movimentos_json),
                'movimentos': movimentos_json[:5]  # Primeiros 5 para preview
            })
            
        finally:
            # Limpar arquivo temporÃ¡rio
            if os.path.exists(temp_path):
                os.remove(temp_path)
                
    except Exception as e:
        logger.error(f"Erro no upload de arquivo: {str(e)}")
        return jsonify({'success': False, 'message': f'Erro ao processar arquivo: {str(e)}'}), 500

@conciliacao_v2_bp.route('/api/carregar-dados-sistema', methods=['POST'])
@login_required  
@perfil_required('admin', 'interno_unique')
def carregar_dados_sistema():
    """Carrega dados da tabela fin_conciliacao_movimentos"""
    try:
        # Verificar se é bypass para usar armazenamento alternativo
        is_bypass = verificar_api_bypass()
        session_id = get_bypass_session_id() if is_bypass else None
        
        data = request.get_json()
        banco = data.get('banco', 'todos')
        periodo = data.get('periodo', 'ultimos_30_dias')
        data_inicio = data.get('data_inicio')
        data_fim = data.get('data_fim')
        
        # Calcular perÃ­odo
        if periodo == 'mes_atual':
            now = datetime.now()
            data_inicio = now.replace(day=1)
            data_fim = now
        elif periodo == 'mes_anterior':
            now = datetime.now()
            primeiro_dia_mes_atual = now.replace(day=1)
            data_fim = primeiro_dia_mes_atual - timedelta(days=1)
            data_inicio = data_fim.replace(day=1)
        elif periodo == 'ultimos_7_dias':
            data_fim = datetime.now()
            data_inicio = data_fim - timedelta(days=7)
        elif periodo == 'ultimos_30_dias':
            data_fim = datetime.now()
            data_inicio = data_fim - timedelta(days=30)
        elif periodo == 'personalizado':
            if not data_inicio or not data_fim:
                return jsonify({'success': False, 'message': 'Datas sÃ£o obrigatÃ³rias para perÃ­odo personalizado'}), 400
            data_inicio = datetime.fromisoformat(data_inicio)
            data_fim = datetime.fromisoformat(data_fim)
        
        # Buscar dados no Supabase
        client = supabase_admin if supabase_admin else supabase
        if not client:
            return jsonify({'success': False, 'message': 'ConexÃ£o com banco de dados nÃ£o disponÃ­vel'}), 500
        
        query = client.table('fin_conciliacao_movimentos').select('*')
        
        # Filtrar por banco se especÃ­fico
        if banco != 'todos':
            query = query.eq('nome_banco', banco)
        
        # Filtrar por perÃ­odo
        query = query.gte('data_lancamento', data_inicio.strftime('%Y-%m-%d'))
        query = query.lte('data_lancamento', data_fim.strftime('%Y-%m-%d'))
        
        # Executar query
        result = query.execute()
        
        # Processar dados
        movimentos_sistema = []
        for row in result.data:
            # Tratar diferentes formatos de data
            data_lancamento = row['data_lancamento']
            try:
                if isinstance(data_lancamento, str):
                    # Tentar diferentes formatos
                    if '/' in data_lancamento:  # DD/MM/YYYY
                        data_obj = datetime.strptime(data_lancamento, '%d/%m/%Y')
                    elif '-' in data_lancamento and len(data_lancamento) == 10:  # YYYY-MM-DD
                        data_obj = datetime.strptime(data_lancamento, '%Y-%m-%d')
                    else:  # ISO format
                        data_obj = datetime.fromisoformat(data_lancamento.split('T')[0])
                else:
                    data_obj = datetime.now()  # fallback
                    
                data_formatada = data_obj.strftime('%d/%m/%Y')
                data_iso = data_obj.strftime('%Y-%m-%d')
            except:
                # Se falhar, usar data atual
                data_obj = datetime.now()
                data_formatada = data_obj.strftime('%d/%m/%Y')
                data_iso = data_obj.strftime('%Y-%m-%d')
            
            movimentos_sistema.append({
                'id': row['id'],
                'data': data_iso,  # Formato ISO para processamento
                'data_formatada': data_formatada,  # Formato brasileiro para exibição
                'valor': float(row['valor']),
                'valor_formatado': f"R$ {float(row['valor']):,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.'),
                'descricao': row['descricao'],
                'banco': row['nome_banco'],
                'conta': row.get('numero_conta', ''),
                'tipo': row['tipo_lancamento'],
                'codigo_referencia': row.get('ref_unique', ''),
                'conciliado': row.get('status', 'PENDENTE') != 'PENDENTE'
            })
        
        # Armazenar na sessÃ£o (ou bypass_sessions)
        if is_bypass and session_id:
            set_bypass_session_data(session_id, 'dados_sistema', movimentos_sistema)
        else:
            session['dados_sistema'] = movimentos_sistema
            session.modified = True
        
        access_logger.log_access(
            'api_call',
            user_id=session.get('user_id'),
            action='data_load',
            resource='conciliacao_v2',
            details={
                'banco': banco,
                'periodo': periodo,
                'total_movimentos': len(movimentos_sistema)
            }
        )
        
        return jsonify({
            'success': True,
            'message': f'{len(movimentos_sistema)} movimentos carregados do sistema',
            'total_movimentos': len(movimentos_sistema),
            'movimentos': movimentos_sistema
        })
        
    except Exception as e:
        logger.error(f"Erro ao carregar dados do sistema: {str(e)}")
        return jsonify({'success': False, 'message': f'Erro ao carregar dados: {str(e)}'}), 500

@conciliacao_v2_bp.route('/api/conciliacao-automatica', methods=['POST'])
@login_required
@perfil_required('admin', 'interno_unique')
def conciliacao_automatica():
    """Executa conciliaÃ§Ã£o automÃ¡tica usando nosso motor"""
    try:
        # Verificar se Ã© bypass mode
        is_bypass = request.headers.get('X-API-Key') == os.getenv('API_BYPASS_KEY')
        session_id = request.headers.get('X-Session-ID') if is_bypass else None
        
        # Obter dados da sessÃ£o (ou bypass_sessions)
        if is_bypass and session_id:
            dados_sistema = get_bypass_session_data(session_id).get('dados_sistema', [])
            arquivos_processados = get_bypass_session_data(session_id).get('arquivos_processados', {})
            print(f"[DEBUG BYPASS] Session ID: {session_id}")
            print(f"[DEBUG BYPASS] Dados Sistema: {len(dados_sistema)}")
            print(f"[DEBUG BYPASS] Arquivos Processados: {len(arquivos_processados)}")
        else:
            dados_sistema = session.get('dados_sistema', [])
            arquivos_processados = session.get('arquivos_processados', {})
            print(f"[DEBUG NORMAL] Session Keys: {list(session.keys())}")
            print(f"[DEBUG NORMAL] Dados Sistema: {len(dados_sistema)}")
            print(f"[DEBUG NORMAL] Arquivos Processados: {len(arquivos_processados)}")
            if arquivos_processados:
                for nome, info in arquivos_processados.items():
                    print(f"[DEBUG NORMAL] Arquivo {nome}: {len(info.get('movimentos', []))} movimentos")
        
        if not dados_sistema:
            print(f"[DEBUG ERROR] Nenhum dado do sistema encontrado!")
            return jsonify({'success': False, 'message': 'Carregue primeiro os dados do sistema'}), 400
        
        if not arquivos_processados:
            print(f"[DEBUG ERROR] Nenhum arquivo bancário encontrado!")
            return jsonify({'success': False, 'message': 'FaÃ§a upload de pelo menos um arquivo bancÃ¡rio'}), 400
        
        # Converter dados do sistema para formato do motor
        movimentos_sistema = []
        for mov in dados_sistema:
            from .conciliacao_service import MovimentoSistema
            movimento_sistema = MovimentoSistema(
                id=str(mov['id']),
                data_lancamento=mov['data'],
                valor=float(mov['valor']),
                descricao=mov['descricao'],
                nome_banco=mov['banco'],
                numero_conta=mov['conta'],
                tipo_lancamento=mov['tipo'],
                ref_unique=mov.get('codigo_referencia', '')
            )
            movimentos_sistema.append(movimento_sistema)
        
        # Converter dados dos bancos para formato do motor
        movimentos_banco = []
        for banco_tipo, arquivo_data in arquivos_processados.items():
            for mov in arquivo_data['movimentos']:
                from .conciliacao_service import MovimentoBanco
                movimento_banco = MovimentoBanco(
                    data=mov['data_iso'],
                    data_original=mov.get('data_original', mov['data_iso']),
                    valor=float(mov['valor']),
                    valor_original=str(mov['valor']),
                    descricao=mov['descricao'],
                    banco=mov['banco'],
                    conta=mov['conta'],
                    tipo=mov['tipo'],
                    codigo_referencia=mov.get('codigo_referencia', ''),
                    linha_origem=mov.get('linha_origem', 0)
                )
                movimentos_banco.append(movimento_banco)
        
        # Executar conciliaÃ§Ã£o
        resultados = conciliacao_manager.conciliacao_service.conciliar_movimentos(
            movimentos_sistema, 
            movimentos_banco
        )
        
        # Processar resultados
        conciliados = []
        parciais = []
        nao_conciliados = []
        
        for resultado in resultados:
            resultado_data = {
                'id_sistema': resultado.movimento_sistema.id,
                'data': resultado.movimento_sistema.data_lancamento,
                'valor': float(resultado.movimento_sistema.valor),
                'descricao_sistema': resultado.movimento_sistema.descricao,
                'banco_sistema': resultado.movimento_sistema.nome_banco,
                'status': resultado.status,
                'score': float(resultado.score_match) if resultado.score_match else 0,
                'criterios': resultado.criterios_atendidos if resultado.criterios_atendidos else []
            }
            
            if resultado.movimento_banco:
                resultado_data.update({
                    'descricao_banco': resultado.movimento_banco.descricao,
                    'banco_banco': resultado.movimento_banco.banco,
                    'valor_banco': float(resultado.movimento_banco.valor)
                })
            
            if resultado.status == 'CONCILIADO':
                conciliados.append(resultado_data)
            elif resultado.status == 'PARCIAL':
                parciais.append(resultado_data)
            else:
                nao_conciliados.append(resultado_data)
        
        # Armazenar resultados na sessÃ£o (ou bypass_sessions)
        if is_bypass and session_id:
            set_bypass_session_data(session_id, 'resultados_conciliacao', {
                'conciliados': conciliados,
                'parciais': parciais,
                'nao_conciliados': nao_conciliados,
                'timestamp': datetime.now().isoformat()
            })
        else:
            session['resultados_conciliacao'] = {
                'conciliados': conciliados,
                'parciais': parciais,
                'nao_conciliados': nao_conciliados,
                'timestamp': datetime.now().isoformat()
            }
            session.modified = True
        
        taxa_sucesso = (len(conciliados) / len(movimentos_sistema)) * 100 if movimentos_sistema else 0
        
        access_logger.log_access(
            'api_call',
            user_id=session.get('user_id'),
            action='auto_reconciliation',
            resource='conciliacao_v2',
            details={
                'total_sistema': len(movimentos_sistema),
                'total_banco': len(movimentos_banco),
                'conciliados': len(conciliados),
                'parciais': len(parciais),
                'nao_conciliados': len(nao_conciliados),
                'taxa_sucesso': round(taxa_sucesso, 2)
            }
        )
        
        return jsonify({
            'success': True,
            'message': f'ConciliaÃ§Ã£o automÃ¡tica concluÃ­da! {len(conciliados)} conciliaÃ§Ãµes encontradas.',
            'estatisticas': {
                'total_sistema': len(movimentos_sistema),
                'total_banco': len(movimentos_banco),
                'conciliados': len(conciliados),
                'parciais': len(parciais),
                'nao_conciliados': len(nao_conciliados),
                'taxa_sucesso': round(taxa_sucesso, 2)
            },
            'resultados': {
                'conciliados': conciliados[:10],  # Primeiros 10 para preview
                'parciais': parciais[:10],
                'nao_conciliados': nao_conciliados[:10]
            }
        })
        
    except Exception as e:
        logger.error(f"Erro na conciliaÃ§Ã£o automÃ¡tica: {str(e)}")
        return jsonify({'success': False, 'message': f'Erro na conciliaÃ§Ã£o: {str(e)}'}), 500

@conciliacao_v2_bp.route('/api/conciliacao-manual', methods=['POST'])
@login_required
@perfil_required('admin', 'interno_unique')
def conciliacao_manual():
    """Concilia manualmente registros selecionados"""
    try:
        data = request.get_json()
        ids_sistema = data.get('ids_sistema', [])
        ids_banco = data.get('ids_banco', [])
        
        if not ids_sistema or not ids_banco:
            return jsonify({'success': False, 'message': 'Selecione registros do sistema e do banco'}), 400
        
        # Obter dados da sessÃ£o
        dados_sistema = session.get('dados_sistema', [])
        arquivos_processados = session.get('arquivos_processados', {})
        
        # Encontrar registros selecionados
        movimentos_sistema_sel = []
        for mov in dados_sistema:
            if str(mov['id']) in ids_sistema:
                movimentos_sistema_sel.append(mov)
        
        movimentos_banco_sel = []
        for banco_tipo, arquivo_data in arquivos_processados.items():
            for mov in arquivo_data['movimentos']:
                if mov['id'] in ids_banco:
                    movimentos_banco_sel.append(mov)
        
        # Calcular somatÃ³rios
        valor_sistema = sum(mov['valor'] for mov in movimentos_sistema_sel)
        valor_banco = sum(mov['valor'] for mov in movimentos_banco_sel)
        diferenca = valor_sistema - valor_banco
        
        # Criar conciliaÃ§Ã£o manual
        conciliacao_manual = {
            'id': f"manual_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            'tipo': 'MANUAL',
            'movimentos_sistema': movimentos_sistema_sel,
            'movimentos_banco': movimentos_banco_sel,
            'valor_sistema': valor_sistema,
            'valor_banco': valor_banco,
            'diferenca': diferenca,
            'timestamp': datetime.now().isoformat()
        }
        
        # Armazenar na sessÃ£o
        if 'conciliacoes_manuais' not in session:
            session['conciliacoes_manuais'] = []
        
        session['conciliacoes_manuais'].append(conciliacao_manual)
        session.modified = True
        
        access_logger.log_access(
            'api_call',
            user_id=session.get('user_id'),
            action='manual_reconciliation',
            resource='conciliacao_v2',
            details={
                'ids_sistema': ids_sistema,
                'ids_banco': ids_banco,
                'valor_sistema': valor_sistema,
                'valor_banco': valor_banco,
                'diferenca': diferenca
            }
        )
        
        return jsonify({
            'success': True,
            'message': f'ConciliaÃ§Ã£o manual realizada! {len(movimentos_sistema_sel)} registros do sistema com {len(movimentos_banco_sel)} do banco.',
            'conciliacao': {
                'id': conciliacao_manual['id'],
                'tipo': 'MANUAL',
                'quantidade_sistema': len(movimentos_sistema_sel),
                'quantidade_banco': len(movimentos_banco_sel),
                'valor_sistema': valor_sistema,
                'valor_banco': valor_banco,
                'diferenca': diferenca,
                'valor_sistema_formatado': f"R$ {valor_sistema:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.'),
                'valor_banco_formatado': f"R$ {valor_banco:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.'),
                'diferenca_formatada': f"R$ {diferenca:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
            }
        })
        
    except Exception as e:
        logger.error(f"Erro na conciliaÃ§Ã£o manual: {str(e)}")
        return jsonify({'success': False, 'message': f'Erro na conciliaÃ§Ã£o manual: {str(e)}'}), 500

@conciliacao_v2_bp.route('/api/limpar-dados', methods=['POST'])
@login_required
@perfil_required('admin', 'interno_unique')
def limpar_dados():
    """Limpa todos os dados da sessÃ£o"""
    try:
        keys_to_clear = [
            'dados_sistema',
            'arquivos_processados', 
            'resultados_conciliacao',
            'conciliacoes_manuais'
        ]
        
        for key in keys_to_clear:
            if key in session:
                del session[key]
        
        session.modified = True
        
        access_logger.log_access(
            'api_call',
            user_id=session.get('user_id'),
            action='clear_data',
            resource='conciliacao_v2'
        )
        
        return jsonify({'success': True, 'message': 'Dados limpos com sucesso!'})
        
    except Exception as e:
        logger.error(f"Erro ao limpar dados: {str(e)}")
        return jsonify({'success': False, 'message': f'Erro ao limpar dados: {str(e)}'}), 500

@conciliacao_v2_bp.route('/api/status', methods=['GET'])
@login_required
@perfil_required('admin', 'interno_unique')
def get_status():
    """Retorna status atual da conciliaÃ§Ã£o"""
    try:
        dados_sistema = session.get('dados_sistema', [])
        arquivos_processados = session.get('arquivos_processados', {})
        resultados_conciliacao = session.get('resultados_conciliacao', {})
        conciliacoes_manuais = session.get('conciliacoes_manuais', [])
        
        total_arquivos = len(arquivos_processados)
        total_movimentos_banco = sum(arquivo['total'] for arquivo in arquivos_processados.values())
        
        # EstatÃ­sticas
        conciliados_auto = len(resultados_conciliacao.get('conciliados', []))
        parciais_auto = len(resultados_conciliacao.get('parciais', []))
        nao_conciliados_auto = len(resultados_conciliacao.get('nao_conciliados', []))
        conciliados_manual = len(conciliacoes_manuais)
        
        total_conciliado = conciliados_auto + conciliados_manual
        taxa_conciliacao = (total_conciliado / len(dados_sistema)) * 100 if dados_sistema else 0
        
        return jsonify({
            'success': True,
            'status': {
                'dados_sistema_carregados': len(dados_sistema) > 0,
                'total_movimentos_sistema': len(dados_sistema),
                'arquivos_carregados': total_arquivos > 0,
                'total_arquivos': total_arquivos,
                'total_movimentos_banco': total_movimentos_banco,
                'conciliacao_executada': len(resultados_conciliacao) > 0,
                'estatisticas': {
                    'conciliados_automatico': conciliados_auto,
                    'parciais': parciais_auto,
                    'nao_conciliados': nao_conciliados_auto,
                    'conciliados_manual': conciliados_manual,
                    'total_conciliado': total_conciliado,
                    'taxa_conciliacao': round(taxa_conciliacao, 2)
                }
            }
        })
        
    except Exception as e:
        logger.error(f"Erro ao obter status: {str(e)}")
        return jsonify({'success': False, 'message': f'Erro ao obter status: {str(e)}'}), 500

# Rotas de teste/debug
@conciliacao_v2_bp.route('/debug/test-motor', methods=['GET'])
def test_motor():
    """Rota de teste para validar o motor de conciliaÃ§Ã£o"""
    if not verificar_api_bypass():
        return jsonify({'error': 'Acesso negado'}), 403
    
    try:
        # Teste bÃ¡sico do motor
        test_files = {
            'BANCO_DO_BRASIL': 'modules/financeiro/conciliacao_lancamentos/Banco do Brasil.xlsx',
            'BANCO_ITAU': 'modules/financeiro/conciliacao_lancamentos/Banco Itau.txt', 
            'BANCO_SANTANDER': 'modules/financeiro/conciliacao_lancamentos/Banco Santander.xlsx'
        }
        
        resultados = {}
        for banco_tipo, filepath in test_files.items():
            full_path = os.path.join(os.getcwd(), filepath)
            if os.path.exists(full_path):
                try:
                    movimentos = conciliacao_manager.parser.parse_file(full_path, banco_tipo)
                    resultados[banco_tipo] = {
                        'success': True,
                        'total_movimentos': len(movimentos),
                        'sample': [
                            {
                                'data': mov.data.strftime('%d/%m/%Y'),
                                'valor': float(mov.valor),
                                'descricao': mov.descricao[:50],
                                'banco': mov.banco
                            } for mov in movimentos[:3]
                        ]
                    }
                except Exception as e:
                    resultados[banco_tipo] = {
                        'success': False,
                        'error': str(e)
                    }
            else:
                resultados[banco_tipo] = {
                    'success': False,
                    'error': 'Arquivo nÃ£o encontrado'
                }
        
        return jsonify({
            'success': True,
            'message': 'Motor de conciliaÃ§Ã£o testado',
            'resultados': resultados
        })
        
    except Exception as e:
        logger.error(f"Erro no teste do motor: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500
