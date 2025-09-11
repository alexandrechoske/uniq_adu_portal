# Conciliação de Lançamentos - Routes
from flask import Blueprint, render_template, request, session, jsonify, flash, redirect, url_for
from werkzeug.utils import secure_filename
import os
import pandas as pd
import logging
from datetime import datetime, timedelta
from extensions import supabase, supabase_admin
from decorators.perfil_decorators import perfil_required
from services.access_logger import access_logger
import tempfile
import uuid

# Configurar blueprint
conciliacao_lancamentos_bp = Blueprint('fin_conciliacao_lancamentos', __name__, 
                         url_prefix='/financeiro/conciliacao-lancamentos',
                         template_folder='templates/conciliacao_lancamentos',
                         static_folder='static')

# Configurar logging
logger = logging.getLogger(__name__)

# Configurações de upload
UPLOAD_FOLDER = '/tmp/conciliacao_uploads'
ALLOWED_EXTENSIONS = {'xlsx', 'xls'}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB

# Criar pasta de upload se não existir
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

@conciliacao_lancamentos_bp.route('/')
@perfil_required(['admin', 'interno_unique'])
def index():
    """Página principal da conciliação de lançamentos."""
    try:
        logger.info(f"[CONCILIACAO] Acessando página principal - usuário: {session.get('user_email', 'N/A')}")
        
        # Log de acesso
        access_logger.log_page_access('Conciliação de Lançamentos', 'financeiro')
        
        return render_template('conciliacao_lancamentos.html',
                             module_name='Conciliação de Lançamentos',
                             page_title='Conciliação de Lançamentos')
        
    except Exception as e:
        logger.error(f"[CONCILIACAO] Erro ao carregar página: {str(e)}")
        flash(f'Erro ao carregar página: {str(e)}', 'error')
        return redirect(url_for('dashboard.dashboard_main'))

@conciliacao_lancamentos_bp.route('/api/upload-extratos', methods=['POST'])
@perfil_required(['admin', 'interno_unique'])
def upload_extratos():
    """Upload e processamento de arquivos de extrato bancário."""
    try:
        logger.info("[CONCILIACAO] Iniciando upload de extratos")
        
        if 'files' not in request.files:
            return jsonify({'success': False, 'error': 'Nenhum arquivo enviado'})
        
        files = request.files.getlist('files')
        if not files or all(f.filename == '' for f in files):
            return jsonify({'success': False, 'error': 'Nenhum arquivo selecionado'})
        
        resultados = []
        movimentos_banco = []
        
        for file in files:
            if file and allowed_file(file.filename):
                resultado = processar_arquivo_extrato(file)
                if resultado['success']:
                    resultados.append(resultado)
                    movimentos_banco.extend(resultado['data'])
                else:
                    logger.error(f"[CONCILIACAO] Erro ao processar {file.filename}: {resultado['error']}")
                    return jsonify({'success': False, 'error': f'Erro em {file.filename}: {resultado["error"]}'})
            else:
                return jsonify({'success': False, 'error': f'Arquivo {file.filename} não permitido'})
        
        # Salvar na sessão para uso posterior
        session['movimentos_banco'] = movimentos_banco
        session['extratos_processados'] = resultados
        
        logger.info(f"[CONCILIACAO] Upload concluído: {len(movimentos_banco)} movimentos processados")
        
        return jsonify({
            'success': True,
            'data': {
                'total_arquivos': len(resultados),
                'total_movimentos': len(movimentos_banco),
                'arquivos': resultados
            }
        })
        
    except Exception as e:
        logger.error(f"[CONCILIACAO] Erro no upload: {str(e)}")
        return jsonify({'success': False, 'error': f'Erro interno: {str(e)}'})

@conciliacao_lancamentos_bp.route('/api/movimentos-sistema')
@perfil_required(['admin', 'interno_unique'])
def movimentos_sistema():
    """Buscar movimentos financeiros do sistema para o mês atual."""
    try:
        logger.info("[CONCILIACAO] Buscando movimentos do sistema")
        
        # Buscar movimentos do mês atual via view
        response = supabase.table('vw_fin_movimentos_caixa').select('*').execute()
        
        if response.data:
            # Salvar na sessão
            session['movimentos_sistema'] = response.data
            
            logger.info(f"[CONCILIACAO] Encontrados {len(response.data)} movimentos do sistema")
            
            return jsonify({
                'success': True,
                'data': response.data
            })
        else:
            logger.warning("[CONCILIACAO] Nenhum movimento encontrado no sistema")
            return jsonify({
                'success': True,
                'data': []
            })
            
    except Exception as e:
        logger.error(f"[CONCILIACAO] Erro ao buscar movimentos: {str(e)}")
        return jsonify({'success': False, 'error': f'Erro ao buscar movimentos: {str(e)}'})

@conciliacao_lancamentos_bp.route('/api/processar-conciliacao', methods=['POST'])
@perfil_required(['admin', 'interno_unique'])
def processar_conciliacao():
    """Processar conciliação automática entre sistema e extratos."""
    try:
        logger.info("[CONCILIACAO] Iniciando processamento de conciliação")
        
        movimentos_sistema = session.get('movimentos_sistema', [])
        movimentos_banco = session.get('movimentos_banco', [])
        
        if not movimentos_sistema:
            return jsonify({'success': False, 'error': 'Movimentos do sistema não encontrados'})
        
        if not movimentos_banco:
            return jsonify({'success': False, 'error': 'Movimentos bancários não encontrados'})
        
        # Processar conciliação automática
        resultado = executar_conciliacao_automatica(movimentos_sistema, movimentos_banco)
        
        # Salvar resultados na sessão
        session['resultado_conciliacao'] = resultado
        
        logger.info(f"[CONCILIACAO] Conciliação processada: {resultado['conciliados_automatico']} automáticos")
        
        return jsonify({
            'success': True,
            'data': resultado
        })
        
    except Exception as e:
        logger.error(f"[CONCILIACAO] Erro no processamento: {str(e)}")
        return jsonify({'success': False, 'error': f'Erro no processamento: {str(e)}'})

@conciliacao_lancamentos_bp.route('/api/conciliar-manual', methods=['POST'])
@perfil_required(['admin', 'interno_unique'])
def conciliar_manual():
    """Conciliar movimentos selecionados manualmente."""
    try:
        data = request.get_json()
        sistema_ids = data.get('sistema_ids', [])
        banco_ids = data.get('banco_ids', [])
        
        logger.info(f"[CONCILIACAO] Conciliação manual: {len(sistema_ids)} sistema, {len(banco_ids)} banco")
        
        if not sistema_ids or not banco_ids:
            return jsonify({'success': False, 'error': 'Selecione movimentos em ambas as tabelas'})
        
        # Executar conciliação manual
        resultado = executar_conciliacao_manual(sistema_ids, banco_ids)
        
        if resultado['success']:
            logger.info(f"[CONCILIACAO] Conciliação manual realizada com sucesso")
            return jsonify({
                'success': True,
                'message': f'Conciliação realizada: {len(sistema_ids)} x {len(banco_ids)} movimentos'
            })
        else:
            return jsonify({'success': False, 'error': resultado['error']})
        
    except Exception as e:
        logger.error(f"[CONCILIACAO] Erro na conciliação manual: {str(e)}")
        return jsonify({'success': False, 'error': f'Erro na conciliação: {str(e)}'})

# Funções auxiliares

def allowed_file(filename):
    """Verificar se o arquivo é permitido."""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def processar_arquivo_extrato(file):
    """Processar arquivo de extrato bancário."""
    try:
        filename = secure_filename(file.filename)
        filepath = os.path.join(UPLOAD_FOLDER, f"{uuid.uuid4()}_{filename}")
        
        # Salvar arquivo temporariamente
        file.save(filepath)
        
        # Verificar tamanho
        if os.path.getsize(filepath) > MAX_FILE_SIZE:
            os.remove(filepath)
            return {'success': False, 'error': 'Arquivo muito grande (máx. 10MB)'}
        
        # Processar Excel
        try:
            df = pd.read_excel(filepath, engine='openpyxl')
        except Exception as e:
            os.remove(filepath)
            return {'success': False, 'error': f'Erro ao ler Excel: {str(e)}'}
        
        # Identificar banco e formato
        banco = identificar_banco(filename, df)
        
        # Padronizar colunas baseado no banco
        movimentos = padronizar_extrato(df, banco)
        
        # Limpar arquivo temporário
        os.remove(filepath)
        
        logger.info(f"[CONCILIACAO] Arquivo processado: {filename}, {len(movimentos)} movimentos")
        
        return {
            'success': True,
            'data': movimentos,
            'arquivo': filename,
            'banco': banco,
            'total_movimentos': len(movimentos)
        }
        
    except Exception as e:
        # Limpar arquivo em caso de erro
        if 'filepath' in locals() and os.path.exists(filepath):
            os.remove(filepath)
        
        logger.error(f"[CONCILIACAO] Erro ao processar arquivo: {str(e)}")
        return {'success': False, 'error': str(e)}

def identificar_banco(filename, df):
    """Identificar banco baseado no nome do arquivo e estrutura."""
    filename_lower = filename.lower()
    
    # Verificar nome do arquivo
    if 'itau' in filename_lower or 'itaú' in filename_lower:
        return 'Itaú'
    elif 'santander' in filename_lower:
        return 'Santander'
    elif 'bb' in filename_lower or 'brasil' in filename_lower:
        return 'Banco do Brasil'
    elif 'bradesco' in filename_lower:
        return 'Bradesco'
    elif 'caixa' in filename_lower:
        return 'Caixa Econômica'
    
    # Verificar estrutura das colunas
    colunas = [str(col).lower() for col in df.columns]
    
    if any('agência' in col or 'agencia' in col for col in colunas):
        return 'Banco do Brasil'
    elif any('conta corrente' in col for col in colunas):
        return 'Itaú'
    
    return 'Outros'

def padronizar_extrato(df, banco):
    """Padronizar extrato bancário para formato comum."""
    movimentos = []
    
    try:
        # Mapeamento de colunas por banco (simplificado para exemplo)
        mapeamentos = {
            'Itaú': {
                'data': ['data', 'dt_mov', 'data_mov'],
                'descricao': ['descricao', 'historico', 'desc'],
                'valor': ['valor', 'vlr_mov', 'debito_credito']
            },
            'Santander': {
                'data': ['data', 'data_mov'],
                'descricao': ['descricao', 'historico'],
                'valor': ['valor', 'vlr_mov']
            },
            'Banco do Brasil': {
                'data': ['data', 'data_mov'],
                'descricao': ['historico', 'descricao'],
                'valor': ['valor', 'vlr_mov']
            }
        }
        
        mapa = mapeamentos.get(banco, mapeamentos['Itaú'])
        
        # Encontrar colunas correspondentes
        colunas_df = [str(col).lower() for col in df.columns]
        
        col_data = None
        col_descricao = None
        col_valor = None
        
        for campo, opcoes in mapa.items():
            for opcao in opcoes:
                if any(opcao in col for col in colunas_df):
                    col_encontrada = [col for col in df.columns if opcao in str(col).lower()][0]
                    if campo == 'data':
                        col_data = col_encontrada
                    elif campo == 'descricao':
                        col_descricao = col_encontrada
                    elif campo == 'valor':
                        col_valor = col_encontrada
                    break
        
        # Se não encontrou as colunas essenciais, usar as primeiras disponíveis
        if not col_data and len(df.columns) > 0:
            col_data = df.columns[0]
        if not col_descricao and len(df.columns) > 1:
            col_descricao = df.columns[1]
        if not col_valor and len(df.columns) > 2:
            col_valor = df.columns[2]
        
        # Processar cada linha
        for index, row in df.iterrows():
            try:
                # Extrair e limpar dados
                data_raw = row[col_data] if col_data else None
                descricao = str(row[col_descricao]).strip() if col_descricao else 'N/A'
                valor_raw = row[col_valor] if col_valor else 0
                
                # Processar data
                if pd.isna(data_raw):
                    continue
                
                if isinstance(data_raw, str):
                    # Tentar diferentes formatos de data
                    for fmt in ['%d/%m/%Y', '%Y-%m-%d', '%d-%m-%Y']:
                        try:
                            data = datetime.strptime(data_raw, fmt).date()
                            break
                        except:
                            continue
                    else:
                        continue
                else:
                    data = data_raw.date() if hasattr(data_raw, 'date') else data_raw
                
                # Processar valor
                if pd.isna(valor_raw):
                    valor = 0
                else:
                    if isinstance(valor_raw, str):
                        # Limpar string de valor
                        valor_str = valor_raw.replace('R$', '').replace('.', '').replace(',', '.').strip()
                        try:
                            valor = float(valor_str)
                        except:
                            valor = 0
                    else:
                        valor = float(valor_raw)
                
                # Determinar tipo
                tipo = 'CREDITO' if valor >= 0 else 'DEBITO'
                
                movimento = {
                    'id': f"{banco}_{index}_{uuid.uuid4().hex[:8]}",
                    'data': data.strftime('%Y-%m-%d'),
                    'tipo': tipo,
                    'descricao': descricao,
                    'valor': valor,
                    'banco': banco,
                    'status': 'pendente',
                    'arquivo_origem': f"{banco}_extrato",
                    'linha_original': index + 1
                }
                
                movimentos.append(movimento)
                
            except Exception as e:
                logger.warning(f"[CONCILIACAO] Erro ao processar linha {index}: {str(e)}")
                continue
        
        logger.info(f"[CONCILIACAO] Padronização concluída: {len(movimentos)} movimentos de {len(df)} linhas")
        
    except Exception as e:
        logger.error(f"[CONCILIACAO] Erro na padronização: {str(e)}")
        raise
    
    return movimentos

def executar_conciliacao_automatica(movimentos_sistema, movimentos_banco):
    """Executar conciliação automática baseada em valor e data."""
    try:
        conciliados = []
        pendentes_sistema = list(movimentos_sistema)
        pendentes_banco = list(movimentos_banco)
        
        # Algoritmo simples de conciliação por valor e data (±2 dias)
        for mov_sistema in movimentos_sistema[:]:
            valor_sistema = float(mov_sistema.get('valor', 0))
            data_sistema = datetime.strptime(mov_sistema.get('data_lancamento', ''), '%Y-%m-%d').date()
            
            for mov_banco in movimentos_banco[:]:
                valor_banco = float(mov_banco.get('valor', 0))
                data_banco = datetime.strptime(mov_banco.get('data', ''), '%Y-%m-%d').date()
                
                # Verificar se valores batem e datas estão próximas (±2 dias)
                diferenca_valor = abs(valor_sistema - valor_banco)
                diferenca_data = abs((data_sistema - data_banco).days)
                
                if diferenca_valor < 0.01 and diferenca_data <= 2:
                    # Conciliação encontrada
                    conciliacao = {
                        'sistema': mov_sistema,
                        'banco': mov_banco,
                        'tipo': 'automatica',
                        'data_conciliacao': datetime.now().isoformat(),
                        'diferenca_valor': diferenca_valor,
                        'diferenca_dias': diferenca_data
                    }
                    
                    conciliados.append(conciliacao)
                    
                    # Remover das listas de pendentes
                    if mov_sistema in pendentes_sistema:
                        pendentes_sistema.remove(mov_sistema)
                    if mov_banco in pendentes_banco:
                        pendentes_banco.remove(mov_banco)
                    
                    break
        
        # Calcular totais
        total_sistema = len(movimentos_sistema)
        total_banco = len(movimentos_banco)
        total_conciliados = len(conciliados)
        total_pendentes_sistema = len(pendentes_sistema)
        total_pendentes_banco = len(pendentes_banco)
        
        valor_sistema = sum(float(m.get('valor', 0)) for m in movimentos_sistema)
        valor_banco = sum(float(m.get('valor', 0)) for m in movimentos_banco)
        valor_conciliado = sum(float(c['sistema'].get('valor', 0)) for c in conciliados)
        valor_pendente_sistema = sum(float(m.get('valor', 0)) for m in pendentes_sistema)
        valor_pendente_banco = sum(float(m.get('valor', 0)) for m in pendentes_banco)
        
        resultado = {
            'total_sistema': total_sistema,
            'total_extratos': total_banco,
            'conciliados_automatico': total_conciliados,
            'pendentes_sistema': total_pendentes_sistema,
            'pendentes_banco': total_pendentes_banco,
            'valor_sistema': valor_sistema,
            'valor_extratos': valor_banco,
            'valor_conciliado': valor_conciliado,
            'valor_pendente_sistema': valor_pendente_sistema,
            'valor_pendente_banco': valor_pendente_banco,
            'conciliacoes': conciliados,
            'pendentes_sistema_lista': pendentes_sistema,
            'pendentes_banco_lista': pendentes_banco
        }
        
        logger.info(f"[CONCILIACAO] Conciliação automática: {total_conciliados} de {total_sistema + total_banco}")
        
        return resultado
        
    except Exception as e:
        logger.error(f"[CONCILIACAO] Erro na conciliação automática: {str(e)}")
        raise

def executar_conciliacao_manual(sistema_ids, banco_ids):
    """Executar conciliação manual dos IDs selecionados."""
    try:
        # Buscar movimentos nas sessões
        movimentos_sistema = session.get('movimentos_sistema', [])
        movimentos_banco = session.get('movimentos_banco', [])
        
        # Encontrar movimentos selecionados
        sistema_selecionados = [m for m in movimentos_sistema if m.get('id') in sistema_ids]
        banco_selecionados = [m for m in movimentos_banco if m.get('id') in banco_ids]
        
        if not sistema_selecionados or not banco_selecionados:
            return {'success': False, 'error': 'Movimentos selecionados não encontrados'}
        
        # Criar conciliação manual
        conciliacao = {
            'tipo': 'manual',
            'data_conciliacao': datetime.now().isoformat(),
            'usuario': session.get('user_email', 'N/A'),
            'sistema_movimentos': sistema_selecionados,
            'banco_movimentos': banco_selecionados,
            'observacoes': 'Conciliação manual realizada pelo usuário'
        }
        
        # Aqui você salvaria no banco de dados a conciliação
        # Por enquanto apenas log
        logger.info(f"[CONCILIACAO] Conciliação manual criada: {len(sistema_selecionados)} x {len(banco_selecionados)}")
        
        return {'success': True, 'conciliacao': conciliacao}
        
    except Exception as e:
        logger.error(f"[CONCILIACAO] Erro na conciliação manual: {str(e)}")
        return {'success': False, 'error': str(e)}

# Registro das rotas de teste e debug
@conciliacao_lancamentos_bp.route('/test')
@perfil_required(['admin'])
def test_route():
    """Rota de teste para desenvolvimento."""
    return jsonify({
        'success': True,
        'message': 'Conciliação de Lançamentos - Rota de teste funcionando',
        'timestamp': datetime.now().isoformat()
    })

@conciliacao_lancamentos_bp.route('/debug')
@perfil_required(['admin'])
def debug_route():
    """Debug da sessão e estado."""
    return jsonify({
        'session_keys': list(session.keys()),
        'movimentos_sistema_count': len(session.get('movimentos_sistema', [])),
        'movimentos_banco_count': len(session.get('movimentos_banco', [])),
        'has_resultado_conciliacao': 'resultado_conciliacao' in session
    })

# === ROTA DE DEBUG TEMPORÁRIA ===
@conciliacao_lancamentos_bp.route('/debug')
def debug_page():
    """Rota de debug temporária para testar a página sem autenticação."""
    try:
        logger.info("[CONCILIACAO-DEBUG] Acessando página de debug")
        
        return render_template('conciliacao_lancamentos.html',
                             module_name='Conciliação de Lançamentos (DEBUG)',
                             page_title='Conciliação de Lançamentos - Debug')
        
    except Exception as e:
        logger.error(f"[CONCILIACAO-DEBUG] Erro ao carregar página: {str(e)}")
        return f"Erro ao carregar página: {str(e)}", 500
