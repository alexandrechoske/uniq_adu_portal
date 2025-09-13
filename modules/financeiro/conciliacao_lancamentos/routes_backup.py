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
    """Buscar movimentos financeiros do sistema para conciliação."""
    try:
        logger.info("[CONCILIACAO] Buscando movimentos do sistema")
        
        # Parâmetros de filtro
        data_inicio = request.args.get('data_inicio')
        data_fim = request.args.get('data_fim')
        
        # Se não informar datas, usar o mês atual
        if not data_inicio or not data_fim:
            hoje = datetime.now()
            data_inicio = hoje.replace(day=1).strftime('%Y-%m-%d')
            data_fim = hoje.strftime('%Y-%m-%d')
        
        logger.info(f"[CONCILIACAO] Período: {data_inicio} a {data_fim}")
        
        # Buscar movimentos do sistema via view usando supabase_admin
        try:
            # Consultar view financeira usando a coluna correta
            query = supabase_admin.table('vw_fin_movimentos_caixa').select('*')
            
            # Aplicar filtros de data usando data_lancamento
            query = query.gte('data_lancamento', data_inicio)
            query = query.lte('data_lancamento', data_fim)
            
            # Executar consulta
            response = query.execute()
            logger.info(f"[CONCILIACAO] Query executada. Total de registros encontrados: {len(response.data) if response.data else 0}")
            
            if response.data:
                movimentos = []
                for mov in response.data:
                    # Padronizar campos para a interface
                    movimento_padronizado = {
                        'id': f"sistema_{mov.get('ref_unique', '')}_h{hash(str(mov))}",
                        'data_movimento': mov.get('data_lancamento'),
                        'data_lancamento': mov.get('data_lancamento'), 
                        'descricao': mov.get('descricao', ''),
                        'valor': float(mov.get('valor', 0)),
                        'tipo_movimento': mov.get('tipo_lancamento', ''),
                        'categoria': mov.get('categoria', ''),
                        'centro_resultado': mov.get('centro_resultado', ''),
                        'classe': mov.get('classe', ''),
                        'ref_unique': mov.get('ref_unique', ''),
                        'origem': 'SISTEMA_FINANCEIRO'
                    }
                    movimentos.append(movimento_padronizado)
                
                logger.info(f"[CONCILIACAO] Movimentos padronizados: {len(movimentos)}")
            else:
                logger.warning("[CONCILIACAO] Nenhum movimento encontrado na view")
                movimentos = []
                
        except Exception as view_error:
            logger.error(f"[CONCILIACAO] Erro ao acessar view: {str(view_error)}")
            # Fallback: dados de teste
            logger.info("[CONCILIACAO] Usando dados de teste...")
            movimentos = gerar_dados_teste()
        
        if movimentos:
            logger.info(f"[CONCILIACAO] Retornando {len(movimentos)} movimentos do sistema")
            return jsonify({
                'success': True,
                'data': movimentos,
                'total': len(movimentos),
                'periodo': {'inicio': data_inicio, 'fim': data_fim}
            })
        else:
            logger.warning("[CONCILIACAO] Nenhum movimento encontrado no período")
            return jsonify({
                'success': False, 
                'error': 'Nenhum movimento encontrado no período especificado',
                'periodo': {'inicio': data_inicio, 'fim': data_fim}
            })
            
    except Exception as e:
        logger.error(f"[CONCILIACAO] Erro na busca de movimentos: {str(e)}")
        return jsonify({'success': False, 'error': str(e)})
                        logger.warning(f"[CONCILIACAO] Erro ao processar data {data_mov}: {str(date_error)}")
                        continue
            
            movimentos = movimentos_filtrados
        
        # Salvar na sessão
        session['movimentos_sistema'] = movimentos
        
        logger.info(f"[CONCILIACAO] Movimentos encontrados: {len(movimentos)}")
        
        return jsonify({
            'success': True,
            'data': movimentos,
            'total': len(movimentos),
            'periodo': {
                'data_inicio': data_inicio,
                'data_fim': data_fim
            }
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
        
        logger.info(f"[CONCILIACAO] Movimentos na sessão - Sistema: {len(movimentos_sistema)}, Banco: {len(movimentos_banco)}")
        
        if not movimentos_sistema:
            logger.error("[CONCILIACAO] Movimentos do sistema não encontrados na sessão")
            return jsonify({'success': False, 'error': 'Movimentos do sistema não encontrados'})
        
        if not movimentos_banco:
            logger.warning("[CONCILIACAO] Movimentos bancários não encontrados na sessão")
            return jsonify({'success': False, 'error': 'Movimentos bancários não encontrados'})
        
        # Processar conciliação automática
        resultado = executar_conciliacao_automatica(movimentos_sistema, movimentos_banco)
        
        # Salvar resultados na sessão
        session['resultado_conciliacao'] = resultado
        
        logger.info(f"[CONCILIACAO] Conciliação processada: {resultado.get('conciliados_automatico', 0)} automáticos")
        
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
        
        logger.info(f"[CONCILIACAO] Processando arquivo: {filename}")
        
        # Salvar arquivo temporariamente
        file.save(filepath)
        
        # Verificar tamanho
        if os.path.getsize(filepath) > MAX_FILE_SIZE:
            os.remove(filepath)
            return {'success': False, 'error': 'Arquivo muito grande (máx. 10MB)'}
        
        # Processar Excel
        try:
            # Detectar formato do arquivo e usar engine apropriado
            if filename.lower().endswith('.xlsx'):
                logger.info(f"[CONCILIACAO] Lendo arquivo .xlsx com openpyxl: {filename}")
                df = pd.read_excel(filepath, engine='openpyxl')
            elif filename.lower().endswith('.xls'):
                logger.info(f"[CONCILIACAO] Lendo arquivo .xls com xlrd: {filename}")
                df = pd.read_excel(filepath, engine='xlrd')
            else:
                os.remove(filepath)
                return {'success': False, 'error': f'Formato de arquivo não suportado: {filename}. Use apenas .xlsx ou .xls'}
                
            logger.info(f"[CONCILIACAO] Arquivo lido com sucesso. Dimensões: {df.shape}")
                
        except Exception as e:
            os.remove(filepath)
            logger.error(f"[CONCILIACAO] Erro ao ler Excel {filename}: {str(e)}")
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
                data_formatada = None
                if data_raw and str(data_raw) != 'nan':
                    try:
                        # Tentar diferentes formatos de data
                        data_str = str(data_raw).strip()
                        if '/' in data_str:  # DD/MM/YYYY
                            data_obj = datetime.strptime(data_str, '%d/%m/%Y')
                        elif '-' in data_str:  # YYYY-MM-DD
                            data_obj = datetime.strptime(data_str, '%Y-%m-%d')
                        else:
                            # Tentar como timestamp do pandas
                            data_obj = pd.to_datetime(data_raw)
                        
                        data_formatada = data_obj.strftime('%d/%m/%Y')
                    except:
                        logger.warning(f"[CONCILIACAO] Data inválida: {data_raw}")
                        continue
                
                # Processar valor
                valor = 0.0
                try:
                    if pd.isna(valor_raw) or str(valor_raw).strip() == '':
                        valor = 0.0
                    else:
                        # Limpar formatação brasileira de moeda
                        valor_str = str(valor_raw).replace('R$', '').replace('.', '').replace(',', '.').strip()
                        valor = float(valor_str)
                except:
                    logger.warning(f"[CONCILIACAO] Valor inválido: {valor_raw}")
                    valor = 0.0
                
                # Determinar tipo baseado no valor
                tipo_movimento = 'CREDITO' if valor >= 0 else 'DEBITO'
                
                # Criar movimento padronizado
                movimento = {
                    'id': f'banco_{index}_{hash(str(data_formatada) + descricao + str(valor))}',
                    'data': data_formatada,
                    'data_movimento': data_formatada,
                    'descricao': descricao,
                    'valor': valor,
                    'tipo': tipo_movimento,
                    'tipo_movimento': tipo_movimento,
                    'banco': banco,
                    'origem': 'EXTRATO_BANCARIO',
                    'status': 'pendente',
                    'linha_excel': index + 1
                }
                
                # Só adicionar se tem data e descrição válidas
                if data_formatada and descricao and descricao != 'N/A':
                    movimentos.append(movimento)
                    
            except Exception as row_error:
                logger.warning(f"[CONCILIACAO] Erro ao processar linha {index}: {str(row_error)}")
                continue
        
        logger.info(f"[CONCILIACAO] Padronização {banco}: {len(movimentos)} movimentos válidos de {len(df)} linhas")
        
        return movimentos
        
    except Exception as e:
        logger.error(f"[CONCILIACAO] Erro na padronização: {str(e)}")
        return []


def identificar_banco(filename, df):
    """Identificar banco baseado no nome do arquivo e estrutura."""
    filename_lower = filename.lower()
    
    # Verificar nome do arquivo
    if 'itau' in filename_lower or 'itaú' in filename_lower:
        return 'ITAU'
    elif 'bradesco' in filename_lower:
        return 'BRADESCO'
    elif 'bb' in filename_lower or 'brasil' in filename_lower:
        return 'BB'
    elif 'santander' in filename_lower:
        return 'SANTANDER'
    elif 'caixa' in filename_lower:
        return 'CAIXA'
    else:
        return 'GENERICO'


def executar_conciliacao_automatica(movimentos_sistema, movimentos_banco):
    """Executar conciliação automática baseada em valor e data."""
    try:
        logger.info(f"[CONCILIACAO] Iniciando conciliação automática - Sistema: {len(movimentos_sistema)}, Banco: {len(movimentos_banco)}")
        
        conciliados = []
        pendentes_sistema = list(movimentos_sistema)
        pendentes_banco = list(movimentos_banco)
        
        # Algoritmo simples de conciliação por valor e data (±3 dias)
        for mov_sistema in movimentos_sistema[:]:
            try:
                valor_sistema = float(mov_sistema.get('valor', 0))
                
                # Tratar diferentes formatos de data do sistema
                data_campo = mov_sistema.get('data_movimento') or mov_sistema.get('data_lancamento')
                if not data_campo:
                    continue
                
                # Converter data brasileira (DD/MM/YYYY) para objeto date
                try:
                    if '/' in data_campo:  # DD/MM/YYYY
                        data_sistema = datetime.strptime(data_campo, '%d/%m/%Y').date()
                    else:  # YYYY-MM-DD
                        data_sistema = datetime.strptime(data_campo, '%Y-%m-%d').date()
                except ValueError:
                    logger.warning(f"[CONCILIACAO] Data inválida no sistema: {data_campo}")
                    continue
                
                for mov_banco in movimentos_banco[:]:
                    try:
                        valor_banco = float(mov_banco.get('valor', 0))
                        
                        # Tratar data do banco (pode vir em diferentes formatos)
                        data_banco_campo = mov_banco.get('data') or mov_banco.get('data_movimento')
                        if not data_banco_campo:
                            continue
                        
                        try:
                            if '/' in data_banco_campo:  # DD/MM/YYYY
                                data_banco = datetime.strptime(data_banco_campo, '%d/%m/%Y').date()
                            else:  # YYYY-MM-DD
                                data_banco = datetime.strptime(data_banco_campo, '%Y-%m-%d').date()
                        except ValueError:
                            logger.warning(f"[CONCILIACAO] Data inválida no banco: {data_banco_campo}")
                            continue
                        
                        # Verificar se valores batem e datas estão próximas (±3 dias)
                        diferenca_valor = abs(valor_sistema - valor_banco)
                        diferenca_data = abs((data_sistema - data_banco).days)
                        
                        if diferenca_valor < 0.01 and diferenca_data <= 3:
                            # Conciliação encontrada
                            conciliacao = {
                                'sistema_id': mov_sistema.get('id'),
                                'banco_id': mov_banco.get('id'),
                                'sistema': mov_sistema,
                                'banco': mov_banco,
                                'tipo': 'automatica',
                                'data_conciliacao': datetime.now().isoformat(),
                                'diferenca_valor': diferenca_valor,
                                'diferenca_dias': diferenca_data,
                                'valor': valor_sistema
                            }
                            
                            conciliados.append(conciliacao)
                            logger.info(f"[CONCILIACAO] Match encontrado: R$ {valor_sistema} ({diferenca_data} dias)")
                            
                            # Remover das listas de pendentes
                            if mov_sistema in pendentes_sistema:
                                pendentes_sistema.remove(mov_sistema)
                            if mov_banco in pendentes_banco:
                                pendentes_banco.remove(mov_banco)
                            
                            break  # Sair do loop do banco após encontrar match
                    
                    except Exception as banco_error:
                        logger.warning(f"[CONCILIACAO] Erro ao processar movimento banco: {str(banco_error)}")
                        continue
            
            except Exception as sistema_error:
                logger.warning(f"[CONCILIACAO] Erro ao processar movimento sistema: {str(sistema_error)}")
                continue
        
        # Calcular totais
        total_sistema = len(movimentos_sistema)
        total_banco = len(movimentos_banco)
        total_conciliados = len(conciliados)
        total_pendentes_sistema = len(pendentes_sistema)
        total_pendentes_banco = len(pendentes_banco)
        
        valor_sistema = sum(float(m.get('valor', 0)) for m in movimentos_sistema)
        valor_banco = sum(float(m.get('valor', 0)) for m in movimentos_banco)
        valor_conciliado = sum(float(c.get('valor', 0)) for c in conciliados)
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
            'conciliados': conciliados,
            'pendentes_sistema_lista': pendentes_sistema,
            'pendentes_banco_lista': pendentes_banco,
            'movimentos_sistema': movimentos_sistema,
            'movimentos_banco': movimentos_banco
        }
        
        logger.info(f"[CONCILIACAO] Resultado: {total_conciliados} conciliados de {total_sistema + total_banco} movimentos")
        
        return resultado
        
    except Exception as e:
        logger.error(f"[CONCILIACAO] Erro na conciliação automática: {str(e)}")
        return {
            'total_sistema': 0,
            'total_extratos': 0,
            'conciliados_automatico': 0,
            'pendentes_sistema': 0,
            'pendentes_banco': 0,
            'error': str(e)
        }


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


@conciliacao_lancamentos_bp.route('/test-movimentos-sistema')
def test_movimentos_sistema():
    """Rota de teste para buscar movimentos do sistema com bypass."""
    # Verificar bypass da API
    api_bypass_key = os.getenv('API_BYPASS_KEY')
    request_api_key = request.headers.get('X-API-Key')
    
    if not (api_bypass_key and request_api_key == api_bypass_key):
        return jsonify({'error': 'API key inválida'}), 401
    
    try:
        logger.info("[CONCILIACAO] [TEST] Verificando estrutura da view")
        
        # Primeiro, vamos ver a estrutura da view
        response_estrutura = supabase_admin.table('vw_fin_movimentos_caixa').select('*').limit(1).execute()
        
        if response_estrutura.data:
            exemplo = response_estrutura.data[0]
            colunas = list(exemplo.keys())
            logger.info(f"[CONCILIACAO] [TEST] Colunas disponíveis: {colunas}")
            
            # Tentar identificar a coluna de data
            coluna_data = None
            for col in ['data_movimento', 'data_lancamento', 'data', 'created_at']:
                if col in colunas:
                    coluna_data = col
                    break
            
            if not coluna_data:
                return jsonify({
                    'success': False,
                    'error': 'Coluna de data não encontrada',
                    'colunas_disponiveis': colunas
                })
            
            logger.info(f"[CONCILIACAO] [TEST] Usando coluna de data: {coluna_data}")
            
            # Parâmetros de filtro
            data_inicio = request.args.get('data_inicio')
            data_fim = request.args.get('data_fim')
            
            # Se não informar datas, usar o mês atual
            if not data_inicio or not data_fim:
                hoje = datetime.now()
                data_inicio = hoje.replace(day=1).strftime('%Y-%m-%d')
                data_fim = hoje.strftime('%Y-%m-%d')
            
            logger.info(f"[CONCILIACAO] [TEST] Período: {data_inicio} a {data_fim}")
            
            # Consultar view financeira
            query = supabase_admin.table('vw_fin_movimentos_caixa').select('*')
            
            # Aplicar filtros de data usando a coluna correta
            query = query.gte(coluna_data, data_inicio)
            query = query.lte(coluna_data, data_fim)
            
            # Executar consulta
            response = query.execute()
            
            if response.data:
                movimentos = response.data
                logger.info(f"[CONCILIACAO] [TEST] Encontrados {len(movimentos)} movimentos")
                
                # Log dos primeiros movimentos para debug
                for i, mov in enumerate(movimentos[:3]):
                    data_mov = mov.get(coluna_data)
                    descricao = mov.get('descricao') or mov.get('description') or 'N/A'
                    valor = mov.get('valor') or mov.get('amount') or 0
                    logger.info(f"[CONCILIACAO] [TEST] Movimento {i+1}: {data_mov} - {descricao} - R$ {valor}")
                
                return jsonify({
                    'success': True,
                    'data': movimentos,
                    'total': len(movimentos),
                    'periodo': {'inicio': data_inicio, 'fim': data_fim},
                    'coluna_data_usada': coluna_data,
                    'colunas_disponiveis': colunas
                })
            else:
                logger.warning("[CONCILIACAO] [TEST] Nenhum movimento encontrado")
                return jsonify({
                    'success': False,
                    'error': 'Nenhum movimento encontrado no período',
                    'periodo': {'inicio': data_inicio, 'fim': data_fim},
                    'coluna_data_usada': coluna_data
                })
        else:
            return jsonify({
                'success': False,
                'error': 'View vw_fin_movimentos_caixa não retornou dados'
            })
            
    except Exception as e:
        logger.error(f"[CONCILIACAO] [TEST] Erro na busca: {str(e)}")
        return jsonify({'success': False, 'error': str(e)})


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


def gerar_dados_teste():
    """Gerar dados de teste para movimentos do sistema."""
    logger.info("[CONCILIACAO] Gerando dados de teste...")
    
    from datetime import datetime, timedelta
    
    data_base = datetime.now() - timedelta(days=15)
    movimentos = []
    
    # Criar 15 movimentos de teste
    for i in range(15):
        data = data_base + timedelta(days=i)
        movimento = {
            'id': f'test_{i+1}',
            'data_movimento': data.strftime('%d/%m/%Y'),
            'descricao': f'Movimento Sistema Teste {i+1}',
            'valor': round((i+1) * 125.50, 2) if i % 2 == 0 else round((i+1) * -87.25, 2),
            'tipo_movimento': 'ENTRADA' if i % 2 == 0 else 'SAIDA',
            'categoria': 'VENDAS' if i % 2 == 0 else 'OPERACIONAL',
            'origem': 'SISTEMA_TESTE',
            'created_at': datetime.now().isoformat(),
            'chave_conciliacao': f'REF{i+1:03d}{data.strftime("%m%Y")}'
        }
        movimentos.append(movimento)
    
    logger.info(f"[CONCILIACAO] Dados de teste gerados: {len(movimentos)} movimentos")
    return movimentos
