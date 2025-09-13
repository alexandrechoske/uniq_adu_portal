# Conciliação de Lançamentos - Routes
from flask import Blueprint, render_template, request, session, jsonify, flash, redirect, url_for, send_file
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
import re
from typing import Dict, List, Tuple, Optional
import io
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill

# Configurar blueprint
# Configurar blueprint
conciliacao_lancamentos_bp = Blueprint('fin_conciliacao_lancamentos', __name__, 
                                      template_folder='templates',
                                      static_folder='static', 
                                      static_url_path='/static/fin_conciliacao_lancamentos',
                                      url_prefix='/financeiro/conciliacao-lancamentos')

# Configurar logging
logger = logging.getLogger(__name__)

# Configurações de upload
UPLOAD_FOLDER = '/tmp/conciliacao_uploads'
ALLOWED_EXTENSIONS = {'xlsx', 'xls', 'csv'}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB

# Criar pasta de upload se não existir
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Bypass API key para testes
API_BYPASS_KEY = os.getenv('API_BYPASS_KEY', 'uniq_api_2025_dev_bypass_key')

def verificar_api_bypass():
    """Verifica se a requisição tem bypass de API"""
    return request.headers.get('X-API-Key') == API_BYPASS_KEY

class ProcessadorBancos:
    """Classe para processar arquivos de diferentes bancos"""
    
    def __init__(self):
        self.bancos_suportados = ['banco_brasil', 'santander', 'itau']
        
    def identificar_banco(self, arquivo_path: str, nome_arquivo: str) -> str:
        """Identifica automaticamente o banco baseado no conteúdo do arquivo"""
        logger.info(f"[BANCO] Iniciando identificação do banco para arquivo: {nome_arquivo}")
        
        try:
            if arquivo_path.endswith('.csv'):
                logger.info(f"[BANCO] Arquivo CSV detectado, analisando conteúdo...")
                with open(arquivo_path, 'r', encoding='utf-8', errors='ignore') as f:
                    primeiras_linhas = [f.readline().strip() for _ in range(5)]
                
                logger.info(f"[BANCO] Primeiras linhas do CSV: {primeiras_linhas[:2]}")
                
                if any('Data;observacao;Data balancete' in linha for linha in primeiras_linhas):
                    logger.info(f"[BANCO] Banco do Brasil identificado por header CSV")
                    return 'banco_brasil'
                
                if any('AGENCIA;' in linha and 'CONTA;' in linha for linha in primeiras_linhas):
                    logger.info(f"[BANCO] Santander identificado por header CSV")
                    return 'santander'
                    
            elif arquivo_path.endswith(('.xls', '.xlsx')):
                logger.info(f"[BANCO] Arquivo Excel detectado, analisando conteúdo...")
                try:
                    df_temp = pd.read_excel(arquivo_path, nrows=10)
                    
                    logger.info(f"[BANCO] Colunas do Excel: {list(df_temp.columns)}")
                    
                    # Verificar colunas para identificar banco
                    colunas_str = ' '.join([str(col) for col in df_temp.columns]).upper()
                    
                    # Adicionar conteúdo das primeiras linhas para análise
                    content_rows = []
                    for index, row in df_temp.head(5).iterrows():
                        row_str = ' '.join([str(val) for val in row.values if pd.notna(val)]).upper()
                        content_rows.append(row_str)
                    
                    all_content = (colunas_str + ' ' + ' '.join(content_rows)).upper()
                    
                    logger.info(f"[BANCO] Conteúdo para análise: {all_content[:200]}...")
                    
                    # Itaú - identificação por coluna ou conteúdo
                    if 'UNIQUE CONSULTORIA' in all_content:
                        logger.info(f"[BANCO] Itaú identificado por conteúdo do Excel")
                        return 'itau'
                    
                    # Banco do Brasil - identificação por padrões específicos
                    bb_indicators = ['DATA BALANCETE', 'COD. HISTORICO', 'DETALHAMENTO HIST', 'AGENCIA ORIGEM']
                    bb_score = sum(1 for indicator in bb_indicators if indicator in all_content)
                    
                    logger.info(f"[BANCO] Score BB: {bb_score}/4")
                    for indicator in bb_indicators:
                        found = indicator in all_content
                        logger.info(f"[BANCO]   - {indicator}: {'✅' if found else '❌'}")
                    
                    # Se encontrar pelo menos 2 indicadores BB
                    if bb_score >= 2:
                        logger.info(f"[BANCO] Banco do Brasil identificado por indicadores Excel")
                        return 'banco_brasil'
                    
                    # Santander - identificação por padrões de coluna e conteúdo
                    # Deve ter AGENCIA e CONTA mas não ser BB (já verificado acima)
                    santander_indicators = ['DATA MOVIMENTO', 'LANCAMENTO', 'DOC']
                    santander_score = sum(1 for indicator in santander_indicators if indicator in all_content)
                    
                    if ('AGENCIA' in all_content and 'CONTA' in all_content and santander_score > 0):
                        logger.info(f"[BANCO] Santander identificado por estrutura de colunas Excel")
                        return 'santander'
                            
                except Exception as e:
                    logger.error(f"[BANCO] Erro ao analisar Excel: {e}")
                    # Se não conseguir ler como Excel, pode ser que seja CSV com extensão errada
            
            # Fallback para identificação por nome do arquivo
            logger.info(f"[BANCO] Tentando identificação por nome do arquivo...")
            nome_lower = nome_arquivo.lower()
            if 'bb' in nome_lower or 'brasil' in nome_lower:
                logger.info(f"[BANCO] Banco do Brasil identificado por nome do arquivo")
                return 'banco_brasil'
            elif 'santander' in nome_lower:
                logger.info(f"[BANCO] Santander identificado por nome do arquivo")
                return 'santander'
            elif 'itau' in nome_lower or 'itaú' in nome_lower:
                logger.info(f"[BANCO] Itaú identificado por nome do arquivo")
                return 'itau'
                
            logger.warning(f"[BANCO] Não foi possível identificar o banco do arquivo: {nome_arquivo}")
            return 'desconhecido'
            
        except Exception as e:
            logger.error(f"[BANCO] Erro ao identificar banco: {e}")
            return 'desconhecido'
    
    def extrair_referencia(self, texto: str) -> str:
        """Extrai referência UN do texto"""
        if not texto:
            return ''
        
        padroes = [
            r'UN\s*\d{2}/\d{4,5}',
            r'UN\s*\d{2}\.\d{4,5}',
            r'UN\s*\d{6,7}',
            r'UN\s*\d{2}\s*\d{4,5}',
        ]
        
        for padrao in padroes:
            match = re.search(padrao, texto, re.IGNORECASE)
            if match:
                ref = match.group().replace(' ', '')
                if '/' not in ref and '.' not in ref:
                    if len(ref) >= 7:
                        ref = f"{ref[:4]}/{ref[4:]}"
                return ref.upper()
        
        return ''
    
    def processar_banco_brasil(self, arquivo_path: str) -> List[Dict]:
        """Processa arquivo do Banco do Brasil"""
        logger.info(f"[BB] Iniciando processamento de arquivo do Banco do Brasil: {arquivo_path}")
        
        try:
            # Detectar tipo de arquivo e ler apropriadamente
            if arquivo_path.endswith(('.xlsx', '.xls')):
                logger.info(f"[BB] Lendo arquivo Excel...")
                df = pd.read_excel(arquivo_path)
                
                # Procurar linha com header correto (baseado na análise dos arquivos reais)
                header_row = None
                for i, row in df.iterrows():
                    if 'Data' in str(row.iloc[0]) and any('Historico' in str(val) for val in row.values):
                        header_row = i
                        break
                
                if header_row is not None:
                    logger.info(f"[BB] Header encontrado na linha {header_row}")
                    # Redefinir DataFrame com header correto
                    new_df = df.iloc[header_row+1:].copy()
                    # Usar os valores da linha header como nomes de colunas
                    new_df.columns = df.iloc[header_row].values
                    df = new_df
                    logger.info(f"[BB] Usando estrutura Excel com {len(df)} linhas de dados")
                    logger.info(f"[BB] Colunas: {list(df.columns)}")
                else:
                    logger.warning(f"[BB] Header não encontrado, usando estrutura padrão")
            else:
                logger.info(f"[BB] Lendo arquivo CSV...")
                df = pd.read_csv(arquivo_path, sep=';', encoding='utf-8', dtype=str)
                
            logger.info(f"[BB] Arquivo carregado com {len(df)} linhas e colunas: {list(df.columns)}")
            
            lancamentos = []
            linhas_processadas = 0
            linhas_ignoradas = 0
            
            for index, row in df.iterrows():
                try:
                    # Detectar colunas dinamicamente
                    data_col = None
                    valor_col = None
                    historico_col = None
                    detalhamento_col = None
                    documento_col = None
                    cod_historico_col = None
                    inf_col = None
                    
                    # Mapear colunas baseado nos nomes
                    for col in df.columns:
                        col_upper = str(col).upper()
                        if 'DATA' in col_upper and data_col is None:
                            data_col = col
                        elif 'VALOR' in col_upper:
                            valor_col = col
                        elif 'HISTORICO' in col_upper and 'COD' not in col_upper:
                            historico_col = col
                        elif 'DETALHAMENTO' in col_upper:
                            detalhamento_col = col
                        elif 'DOCUMENTO' in col_upper:
                            documento_col = col
                        elif 'COD' in col_upper and 'HISTORICO' in col_upper:
                            cod_historico_col = col
                        elif 'INF' in col_upper:
                            inf_col = col
                    
                    # Verificar se temos as colunas essenciais
                    if not data_col or not valor_col:
                        if index == 0:  # Log apenas na primeira linha
                            logger.warning(f"[BB] Colunas essenciais não encontradas: Data={data_col}, Valor={valor_col}")
                        linhas_ignoradas += 1
                        continue
                    
                    # Processar data
                    data_str = str(row[data_col]).strip()
                    if data_str in ['nan', '', 'None'] or not data_str:
                        linhas_ignoradas += 1
                        continue
                    
                    # Pular linhas que não são de lançamentos (como totais, limites, etc.)
                    if any(palavra in data_str.upper() for palavra in ['SALDO', 'LIMITE', 'JUROS', 'IOF']):
                        linhas_ignoradas += 1
                        continue
                        
                    try:
                        data = datetime.strptime(data_str, '%d/%m/%Y').date()
                    except:
                        logger.debug(f"[BB] Linha {index+1}: Data inválida '{data_str}', ignorando")
                        linhas_ignoradas += 1
                        continue
                    
                    # Processar valor
                    valor_str = str(row[valor_col]).strip()
                    if valor_str in ['nan', '', 'None'] or not valor_str:
                        linhas_ignoradas += 1
                        continue
                        
                    try:
                        valor_str = valor_str.replace(' ', '').replace('.', '').replace(',', '.')
                        valor = float(valor_str)
                    except:
                        logger.debug(f"[BB] Linha {index+1}: Valor inválido '{valor_str}', ignorando")
                        linhas_ignoradas += 1
                        continue
                    
                    # Verificar débito/crédito
                    if inf_col:
                        inf = str(row[inf_col]).strip().upper()
                        if inf == 'D':
                            valor = -valor
                    
                    # Processar histórico
                    historico = str(row[historico_col]).strip() if historico_col else ''
                    detalhamento = str(row[detalhamento_col]).strip() if detalhamento_col else ''
                    
                    # Extrair referência UN
                    ref_unique = self.extrair_referencia(historico + ' ' + detalhamento)
                    
                    lancamento = {
                        'data': data.isoformat(),
                        'valor': valor,
                        'historico': f"{historico} {detalhamento}".strip(),
                        'ref_unique': ref_unique,
                        'banco': 'Banco do Brasil',
                        'documento': str(row[documento_col]).strip() if documento_col else '',
                        'cod_historico': str(row[cod_historico_col]).strip() if cod_historico_col else ''
                    }
                    
                    lancamentos.append(lancamento)
                    linhas_processadas += 1
                    
                    if ref_unique:
                        logger.debug(f"[BB] Linha {index+1}: UN encontrado - {ref_unique}")
                    
                except Exception as e:
                    logger.warning(f"[BB] Erro ao processar linha {index+1}: {e}")
                    linhas_ignoradas += 1
                    continue
            
            logger.info(f"[BB] Processamento concluído: {linhas_processadas} processadas, {linhas_ignoradas} ignoradas")
            logger.info(f"[BB] Total de lançamentos extraídos: {len(lancamentos)}")
            
            if lancamentos:
                logger.info(f"[BB] Primeiro lançamento: {lancamentos[0]}")
                logger.info(f"[BB] Último lançamento: {lancamentos[-1]}")
            
            return lancamentos
            
        except Exception as e:
            logger.error(f"[BB] Erro ao processar Banco do Brasil: {e}")
            return []
    
    def processar_santander(self, arquivo_path: str) -> List[Dict]:
        """Processa arquivo do Santander"""
        logger.info(f"[SANTANDER] Iniciando processamento de arquivo: {arquivo_path}")
        
        try:
            # Detectar tipo de arquivo e processar apropriadamente
            if arquivo_path.endswith(('.xlsx', '.xls')):
                logger.info(f"[SANTANDER] Processando arquivo Excel...")
                df = pd.read_excel(arquivo_path, dtype=str)
                logger.info(f"[SANTANDER] Arquivo Excel carregado com {len(df)} linhas e colunas: {list(df.columns)}")
                
                # Estrutura real do Santander: header na linha 1
                header_row = 1
                if len(df) > header_row:
                    # Usar dados da linha 1 como header
                    new_df = df.iloc[header_row+1:].copy()
                    headers = ['Data', 'Historico', 'Documento', 'Valor', 'Saldo']
                    new_df.columns = headers[:len(new_df.columns)]
                    df = new_df
                    logger.info(f"[SANTANDER] Usando estrutura Excel com {len(df)} linhas de dados")
                else:
                    logger.warning(f"[SANTANDER] Arquivo muito pequeno para processar")
                    return []
                
            else:
                logger.info(f"[SANTANDER] Processando arquivo CSV...")
                with open(arquivo_path, 'r', encoding='utf-8', errors='ignore') as f:
                    linhas = f.readlines()
                
                logger.info(f"[SANTANDER] Arquivo lido com {len(linhas)} linhas")
                
                inicio_dados = 0
                for i, linha in enumerate(linhas):
                    if 'Data;Histórico;Documento;Valor' in linha:
                        inicio_dados = i
                        logger.info(f"[SANTANDER] Header encontrado na linha {i+1}")
                        break
                
                dados_limpos = []
                for linha in linhas[inicio_dados:]:
                    linha = linha.strip()
                    if linha and not linha.startswith('AGENCIA') and 'Data;Histórico' not in linha:
                        dados_limpos.append(linha)
                
                logger.info(f"[SANTANDER] {len(dados_limpos)} linhas de dados encontradas")
                
                if dados_limpos:
                    dados_split = [linha.split(';') for linha in dados_limpos]
                    df = pd.DataFrame(dados_split, columns=['Data', 'Historico', 'Documento', 'Valor', 'Saldo'])
                    logger.info(f"[SANTANDER] DataFrame criado com {len(df)} registros")
                else:
                    logger.warning(f"[SANTANDER] Nenhum dado encontrado no arquivo")
                    return []
            
            lancamentos = []
            linhas_processadas = 0
            linhas_ignoradas = 0
            
            for index, row in df.iterrows():
                try:
                    data_str = str(row.get('Data', '')).strip()
                    if not data_str or '/' not in data_str:
                        logger.debug(f"[SANTANDER] Linha {index+1}: Data inválida, ignorando")
                        linhas_ignoradas += 1
                        continue
                    
                    data = datetime.strptime(data_str, '%d/%m/%Y').date()
                    
                    valor_str = str(row.get('Valor', '')).strip()
                    if not valor_str:
                        logger.debug(f"[SANTANDER] Linha {index+1}: Valor vazio, ignorando")
                        linhas_ignoradas += 1
                        continue
                    
                    valor_str = valor_str.replace('R$', '').replace(' ', '')
                    
                    if valor_str.startswith('-'):
                        valor_str = valor_str[1:]
                        multiplicador = -1
                    else:
                        multiplicador = 1
                    
                    valor_str = valor_str.replace('.', '').replace(',', '.')
                    valor = float(valor_str) * multiplicador
                    
                    historico = str(row.get('Historico', '')).strip()
                    documento = str(row.get('Documento', '')).strip()
                    
                    ref_unique = self.extrair_referencia(historico)
                    
                    lancamento = {
                        'data': data.isoformat(),
                        'valor': valor,
                        'historico': historico,
                        'ref_unique': ref_unique,
                        'banco': 'Santander',
                        'documento': documento
                    }
                    
                    lancamentos.append(lancamento)
                    linhas_processadas += 1
                    
                    if ref_unique:
                        logger.debug(f"[SANTANDER] Linha {index+1}: UN encontrado - {ref_unique}")
                    
                except Exception as e:
                    logger.warning(f"[SANTANDER] Erro ao processar linha {index+1}: {e}")
                    linhas_ignoradas += 1
                    continue
            
            logger.info(f"[SANTANDER] Processamento concluído: {linhas_processadas} processadas, {linhas_ignoradas} ignoradas")
            logger.info(f"[SANTANDER] Total de lançamentos extraídos: {len(lancamentos)}")
            
            if lancamentos:
                logger.info(f"[SANTANDER] Primeiro lançamento: {lancamentos[0]}")
                logger.info(f"[SANTANDER] Último lançamento: {lancamentos[-1]}")
            
            return lancamentos
            
        except Exception as e:
            logger.error(f"[SANTANDER] Erro ao processar Santander: {e}")
            return []
    
    def processar_itau(self, arquivo_path: str) -> List[Dict]:
        """Processa arquivo do Itaú"""
        logger.info(f"[ITAU] Iniciando processamento de arquivo: {arquivo_path}")
        
        try:
            df = pd.read_excel(arquivo_path, dtype=str)
            logger.info(f"[ITAU] Arquivo Excel carregado com {len(df)} linhas e {len(df.columns)} colunas")
            
            inicio_dados = 0
            for i, row in df.iterrows():
                for col in df.columns:
                    if 'Data' in str(row[col]) and 'Lançamento' in str(row[col]):
                        inicio_dados = i + 1
                        break
                if inicio_dados > 0:
                    break
            
            dados_limpos = []
            for i in range(inicio_dados, len(df)):
                row = df.iloc[i]
                
                data_col = None
                lancamento_col = None
                valor_col = None
                saldo_col = None
                
                for col_idx, val in enumerate(row):
                    val_str = str(val).strip()
                    
                    if re.match(r'\d{2}/\d{2}', val_str):
                        data_col = col_idx
                    
                    elif len(val_str) > 10 and not re.match(r'^[\d.,\-]+$', val_str):
                        lancamento_col = col_idx
                    
                    elif re.match(r'^[\-]?[\d.,]+$', val_str) and ',' in val_str:
                        if valor_col is None:
                            valor_col = col_idx
                        else:
                            saldo_col = col_idx
                
                if data_col is not None and valor_col is not None:
                    dados_limpos.append({
                        'data': row.iloc[data_col] if data_col < len(row) else '',
                        'lancamento': row.iloc[lancamento_col] if lancamento_col is not None and lancamento_col < len(row) else '',
                        'valor': row.iloc[valor_col] if valor_col < len(row) else '',
                        'saldo': row.iloc[saldo_col] if saldo_col is not None and saldo_col < len(row) else ''
                    })
            
            lancamentos = []
            ano_atual = datetime.now().year
            
            for item in dados_limpos:
                try:
                    data_str = str(item['data']).strip()
                    if not data_str or data_str == 'nan':
                        continue
                    
                    if len(data_str) == 5:
                        data_str = f"{data_str}/{ano_atual}"
                    
                    data = datetime.strptime(data_str, '%d/%m/%Y').date()
                    
                    valor_str = str(item['valor']).strip()
                    if not valor_str or valor_str == 'nan':
                        continue
                    
                    if valor_str.startswith('-'):
                        valor_str = valor_str[1:]
                        multiplicador = -1
                    else:
                        multiplicador = 1
                    
                    valor_str = valor_str.replace('.', '').replace(',', '.')
                    valor = float(valor_str) * multiplicador
                    
                    lancamento_desc = str(item['lancamento']).strip()
                    
                    ref_unique = self.extrair_referencia(lancamento_desc)
                    
                    lancamento = {
                        'data': data.isoformat(),
                        'valor': valor,
                        'historico': lancamento_desc,
                        'ref_unique': ref_unique,
                        'banco': 'Itaú'
                    }
                    
                    lancamentos.append(lancamento)
                    
                except Exception as e:
                    logger.warning(f"Erro ao processar linha Itaú: {e}")
                    continue
            
            logger.info(f"Itaú: {len(lancamentos)} lançamentos processados")
            return lancamentos
            
        except Exception as e:
            logger.error(f"Erro ao processar Itaú: {e}")
            return []
    
    def processar_arquivo(self, arquivo_path: str, banco: str = None) -> Dict:
        """Processa arquivo de qualquer banco"""
        
        if not os.path.exists(arquivo_path):
            return {'success': False, 'message': 'Arquivo não encontrado'}
        
        nome_arquivo = os.path.basename(arquivo_path)
        
        if not banco:
            banco = self.identificar_banco(arquivo_path, nome_arquivo)
        
        if banco == 'desconhecido':
            return {'success': False, 'message': 'Não foi possível identificar o banco do arquivo'}
        
        logger.info(f"Processando arquivo {nome_arquivo} como {banco}")
        
        try:
            if banco == 'banco_brasil':
                lancamentos = self.processar_banco_brasil(arquivo_path)
            elif banco == 'santander':
                lancamentos = self.processar_santander(arquivo_path)
            elif banco == 'itau':
                lancamentos = self.processar_itau(arquivo_path)
            else:
                return {'success': False, 'message': f'Banco {banco} não suportado'}
            
            return {
                'success': True,
                'banco_identificado': banco,
                'formato_arquivo': arquivo_path.split('.')[-1].upper(),
                'registros_processados': len(lancamentos),
                'lancamentos': lancamentos
            }
            
        except Exception as e:
            return {'success': False, 'message': f'Erro ao processar arquivo: {str(e)}'}

@conciliacao_lancamentos_bp.route('/')
def index():
    """Página principal da conciliação de lançamentos."""
    try:
        # Verificar bypass da API primeiro
        if verificar_api_bypass():
            logger.info(f"[CONCILIACAO] Acesso via bypass da API")
            return render_template('conciliacao_lancamentos/conciliacao_lancamentos.html',
                                 module_name='Conciliação de Lançamentos',
                                 page_title='Conciliação de Lançamentos')
        
        # Verificação de autenticação tradicional
        user = session.get('user', {})
        if not user:
            logger.warning(f"[CONCILIACAO] Usuário não autenticado")
            if request.is_json:
                return jsonify({'error': 'Usuário não autenticado', 'redirect': '/auth/login'}), 401
            return redirect(url_for('auth.login'))
        
        user_role = user.get('role', '')
        if user_role not in ['admin', 'interno_unique']:
            logger.warning(f"[CONCILIACAO] Acesso negado para perfil: {user_role}")
            if request.is_json:
                return jsonify({'error': 'Acesso negado'}), 403
            return redirect(url_for('dashboard.dashboard_main'))
        
        logger.info(f"[CONCILIACAO] Acessando página principal - usuário: {user.get('email', 'N/A')}")
        
        return render_template('conciliacao_lancamentos/conciliacao_lancamentos.html',
                             module_name='Conciliação de Lançamentos',
                             page_title='Conciliação de Lançamentos')
        
    except Exception as e:
        logger.error(f"[CONCILIACAO] Erro ao carregar página: {str(e)}")
        if request.is_json:
            return jsonify({'error': f'Erro interno: {str(e)}'}), 500
        return redirect(url_for('dashboard.dashboard_main'))

@conciliacao_lancamentos_bp.route('/processar', methods=['POST'])
def upload_extratos():
    """Upload e processamento de arquivos de extrato bancário."""
    try:
        logger.info("[PROCESSAR] Iniciando processamento de upload")
        logger.info(f"[PROCESSAR] Headers: {dict(request.headers)}")
        logger.info(f"[PROCESSAR] Form data: {dict(request.form)}")
        logger.info(f"[PROCESSAR] Files: {list(request.files.keys())}")
        
        # Verificar bypass da API ou autenticação
        if not (verificar_api_bypass() or (session.get('user', {}).get('role') in ['admin', 'interno_unique'])):
            logger.warning("[PROCESSAR] Acesso negado - sem bypass ou autenticação")
            return jsonify({'error': 'Acesso negado'}), 403
        
        logger.info("[PROCESSAR] Autenticação/bypass verificado com sucesso")
        
        # Verificar se o arquivo foi enviado corretamente
        if 'arquivo_extrato' not in request.files:
            logger.error("[PROCESSAR] Campo 'arquivo_extrato' não encontrado nos files")
            return jsonify({'success': False, 'error': 'Nenhum arquivo enviado com o nome correto (arquivo_extrato)'}), 400
        
        arquivo = request.files['arquivo_extrato']
        if not arquivo or arquivo.filename == '':
            logger.error("[PROCESSAR] Arquivo vazio ou sem nome")
            return jsonify({'success': False, 'error': 'Nenhum arquivo selecionado'}), 400
        
        logger.info(f"[PROCESSAR] Arquivo recebido: {arquivo.filename}")
        
        # Verificar se é um tipo de arquivo permitido
        if not allowed_file(arquivo.filename):
            logger.error(f"[PROCESSAR] Tipo de arquivo não permitido: {arquivo.filename}")
            return jsonify({'success': False, 'error': f'Tipo de arquivo não permitido. Use: {", ".join(ALLOWED_EXTENSIONS)}'}), 400
        
        # Processar o arquivo
        resultado = processar_arquivo_extrato(arquivo)
        
        if resultado['success']:
            # Buscar também os dados do sistema
            dados_sistema = []
            try:
                logger.info("[PROCESSAR] Buscando dados do sistema...")
                
                # Obter parâmetros de período
                periodo = request.form.get('periodo', '30_dias')
                
                if periodo == 'personalizado':
                    data_inicio = request.form.get('data_inicio')
                    data_fim = request.form.get('data_fim')
                else:
                    # Calcular período baseado na seleção
                    from datetime import datetime, timedelta
                    hoje = datetime.now()
                    
                    if periodo == '7_dias':
                        data_inicio = (hoje - timedelta(days=7)).strftime('%Y-%m-%d')
                    elif periodo == '15_dias':
                        data_inicio = (hoje - timedelta(days=15)).strftime('%Y-%m-%d')
                    elif periodo == '60_dias':
                        data_inicio = (hoje - timedelta(days=60)).strftime('%Y-%m-%d')
                    elif periodo == '90_dias':
                        data_inicio = (hoje - timedelta(days=90)).strftime('%Y-%m-%d')
                    else:  # 30_dias (padrão)
                        data_inicio = (hoje - timedelta(days=30)).strftime('%Y-%m-%d')
                    
                    data_fim = hoje.strftime('%Y-%m-%d')
                
                logger.info(f"[PROCESSAR] Buscando dados do sistema para período: {data_inicio} a {data_fim}")
                
                # Buscar movimentos do sistema via view
                query = supabase_admin.table('vw_fin_movimentos_caixa').select('*')
                query = query.gte('data_lancamento', data_inicio)
                query = query.lte('data_lancamento', data_fim)
                
                response_sistema = query.execute()
                
                if response_sistema.data:
                    dados_sistema = response_sistema.data
                    logger.info(f"[PROCESSAR] {len(dados_sistema)} movimentos do sistema encontrados")
                else:
                    logger.warning("[PROCESSAR] Nenhum movimento do sistema encontrado")
                    
            except Exception as e:
                logger.error(f"[PROCESSAR] Erro ao buscar dados do sistema: {e}")
                # Continuar mesmo se não conseguir buscar dados do sistema
            
            # Salvar apenas metadados na sessão para evitar cookie muito grande
            session['banco_identificado'] = resultado['banco']
            session['arquivo_processado'] = resultado['arquivo']
            session['registros_banco'] = len(resultado['data'])
            session['registros_sistema'] = len(dados_sistema)
            session['periodo_conciliacao'] = f"{data_inicio} a {data_fim}"
            
            # Salvar dados temporariamente em arquivo para não sobrecarregar session
            import tempfile
            import pickle
            
            temp_dir = tempfile.gettempdir()
            session_id = session.get('session_id', str(uuid.uuid4()))
            session['session_id'] = session_id
            
            # Salvar dados em arquivos temporários
            banco_file = os.path.join(temp_dir, f"banco_{session_id}.pkl")
            sistema_file = os.path.join(temp_dir, f"sistema_{session_id}.pkl")
            
            with open(banco_file, 'wb') as f:
                pickle.dump(resultado['data'], f)
            with open(sistema_file, 'wb') as f:
                pickle.dump(dados_sistema, f)
            
            logger.info(f"[PROCESSAR] Dados salvos em arquivos temporários - Session ID: {session_id}")
            
            logger.info(f"[PROCESSAR] Sucesso: {len(resultado['data'])} movimentos do banco, {len(dados_sistema)} do sistema")
            
            # Retornar no formato esperado pelo frontend
            return jsonify({
                'success': True,
                'dados_banco': resultado['data'],
                'dados_sistema': dados_sistema,
                'status': {
                    'banco_identificado': resultado['banco'],
                    'formato_arquivo': resultado['arquivo'].split('.')[-1].upper() if 'arquivo' in resultado else 'CSV',
                    'registros_banco': len(resultado['data']),
                    'registros_sistema': len(dados_sistema),
                    'periodo': f"{data_inicio} a {data_fim}"
                }
            })
        else:
            logger.error(f"[PROCESSAR] Falha no processamento: {resultado['error']}")
            return jsonify({'success': False, 'message': resultado['error']}), 400
            
    except Exception as e:
        logger.error(f"[PROCESSAR] Erro inesperado: {str(e)}", exc_info=True)
        return jsonify({'success': False, 'error': f'Erro interno: {str(e)}'}), 500

@conciliacao_lancamentos_bp.route('/api/movimentos-sistema')
def movimentos_sistema():
    """Buscar movimentos financeiros do sistema para conciliação."""
    try:
        # Verificar bypass da API ou autenticação
        if not (verificar_api_bypass() or (session.get('user', {}).get('role') in ['admin', 'interno_unique'])):
            return jsonify({'error': 'Acesso negado'}), 403
        
        logger.info("[CONCILIACAO] Buscando movimentos do sistema")
        
        # Verificar se existem dados temporários da sessão atual
        session_id = session.get('session_id')
        if session_id:
            dados_temporarios = carregar_dados_temporarios(session_id, 'sistema')
            if dados_temporarios:
                logger.info(f"[CONCILIACAO] Retornando {len(dados_temporarios)} movimentos da sessão temporária")
                return jsonify({
                    'success': True,
                    'data': dados_temporarios,
                    'total': len(dados_temporarios),
                    'periodo': session.get('periodo_conciliacao', 'N/A')
                })
        
        # Se não há dados temporários, buscar no banco
        logger.info("[CONCILIACAO] Buscando movimentos do banco de dados")
        
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

@conciliacao_lancamentos_bp.route('/api/limpar-sessao', methods=['POST'])
def limpar_sessao():
    """Limpar dados temporários da sessão."""
    try:
        # Verificar bypass da API ou autenticação
        if not (verificar_api_bypass() or (session.get('user', {}).get('role') in ['admin', 'interno_unique'])):
            return jsonify({'error': 'Acesso negado'}), 403
            
        session_id = session.get('session_id')
        if session_id:
            limpar_dados_temporarios(session_id)
            
        # Limpar dados da sessão
        keys_to_remove = ['session_id', 'banco_identificado', 'arquivo_processado', 
                         'registros_banco', 'registros_sistema', 'periodo_conciliacao']
        for key in keys_to_remove:
            session.pop(key, None)
            
        logger.info("[CONCILIACAO] Sessão limpa com sucesso")
        return jsonify({'success': True, 'message': 'Sessão limpa com sucesso'})
        
    except Exception as e:
        logger.error(f"[CONCILIACAO] Erro ao limpar sessão: {str(e)}")
        return jsonify({'success': False, 'error': str(e)})

@conciliacao_lancamentos_bp.route('/api/processar-conciliacao', methods=['POST'])
def processar_conciliacao():
    """Processar conciliação automática entre sistema e extratos."""
    try:
        # Verificar bypass da API ou autenticação
        if not (verificar_api_bypass() or (session.get('user', {}).get('role') in ['admin', 'interno_unique'])):
            logger.warning("[CONCILIACAO] Acesso negado - sem bypass ou autenticação")
            return jsonify({'error': 'Acesso negado'}), 403
        logger.info("[CONCILIACAO] Iniciando processamento de conciliação")
        
        # Carregar dados dos arquivos temporários em vez da sessão
        session_id = session.get('session_id')
        if not session_id:
            logger.error("[CONCILIACAO] Session ID não encontrado")
            return jsonify({'success': False, 'error': 'Sessão inválida'})
        
        movimentos_sistema = carregar_dados_temporarios(session_id, 'sistema')
        movimentos_banco = carregar_dados_temporarios(session_id, 'banco')
        
        logger.info(f"[CONCILIACAO] Dados carregados - Sistema: {len(movimentos_sistema)}, Banco: {len(movimentos_banco)}")
        
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
def conciliar_manual():
    """Conciliar movimentos selecionados manualmente."""
    try:
        # Verificar bypass da API ou autenticação
        if not (verificar_api_bypass() or (session.get('user', {}).get('role') in ['admin', 'interno_unique'])):
            logger.warning("[CONCILIACAO] Acesso negado - sem bypass ou autenticação")
            return jsonify({'error': 'Acesso negado'}), 403
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

def carregar_dados_temporarios(session_id, tipo):
    """Carrega dados dos arquivos temporários"""
    try:
        import tempfile
        import pickle
        
        temp_dir = tempfile.gettempdir()
        arquivo = os.path.join(temp_dir, f"{tipo}_{session_id}.pkl")
        
        if os.path.exists(arquivo):
            with open(arquivo, 'rb') as f:
                return pickle.load(f)
        return []
    except Exception as e:
        logger.error(f"Erro ao carregar dados temporários {tipo}: {e}")
        return []

def limpar_dados_temporarios(session_id):
    """Remove arquivos temporários da sessão"""
    try:
        import tempfile
        
        temp_dir = tempfile.gettempdir()
        banco_file = os.path.join(temp_dir, f"banco_{session_id}.pkl")
        sistema_file = os.path.join(temp_dir, f"sistema_{session_id}.pkl")
        
        for arquivo in [banco_file, sistema_file]:
            if os.path.exists(arquivo):
                os.remove(arquivo)
                logger.info(f"Arquivo temporário removido: {arquivo}")
    except Exception as e:
        logger.error(f"Erro ao limpar dados temporários: {e}")

def allowed_file(filename):
    """Verificar se o arquivo é permitido."""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def processar_arquivo_extrato(file):
    """Processar arquivo de extrato bancário."""
    filename = None
    filepath = None
    
    try:
        filename = secure_filename(file.filename)
        filepath = os.path.join(UPLOAD_FOLDER, f"{uuid.uuid4()}_{filename}")
        
        logger.info(f"[UPLOAD] Iniciando processamento do arquivo: {filename}")
        logger.info(f"[UPLOAD] Arquivo temporário salvo em: {filepath}")
        
        # Salvar arquivo temporariamente
        file.save(filepath)
        
        # Verificar tamanho
        file_size = os.path.getsize(filepath)
        logger.info(f"[UPLOAD] Tamanho do arquivo: {file_size} bytes")
        
        if file_size > MAX_FILE_SIZE:
            logger.error(f"[UPLOAD] Arquivo muito grande: {file_size} > {MAX_FILE_SIZE}")
            os.remove(filepath)
            return {'success': False, 'error': 'Arquivo muito grande (máx. 10MB)'}
        
        # Usar ProcessadorBancos para processar o arquivo
        processador = ProcessadorBancos()
        resultado = processador.processar_arquivo(filepath)
        
        # Limpar arquivo temporário
        if os.path.exists(filepath):
            os.remove(filepath)
            logger.info(f"[UPLOAD] Arquivo temporário removido: {filepath}")
        
        if resultado['success']:
            logger.info(f"[UPLOAD] Processamento concluído com sucesso para {filename}")
            logger.info(f"[UPLOAD] Banco identificado: {resultado['banco_identificado']}")
            logger.info(f"[UPLOAD] Registros processados: {resultado['registros_processados']}")
            
            return {
                'success': True,
                'data': resultado['lancamentos'],
                'arquivo': filename,
                'banco': resultado['banco_identificado'],
                'registros_processados': resultado['registros_processados']
            }
        else:
            logger.error(f"[UPLOAD] Falha no processamento: {resultado['message']}")
            return {'success': False, 'error': resultado['message']}
        
    except Exception as e:
        logger.error(f"[UPLOAD] Erro inesperado ao processar {filename}: {str(e)}")
        
        # Garantir limpeza do arquivo temporário
        if filepath and os.path.exists(filepath):
            try:
                os.remove(filepath)
                logger.info(f"[UPLOAD] Arquivo temporário removido após erro: {filepath}")
            except:
                logger.warning(f"[UPLOAD] Não foi possível remover arquivo temporário: {filepath}")
                
        return {'success': False, 'error': f'Erro interno: {str(e)}'}

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
        # Carregar dados dos arquivos temporários
        session_id = session.get('session_id')
        if not session_id:
            return {'success': False, 'error': 'Sessão inválida'}
            
        movimentos_sistema = carregar_dados_temporarios(session_id, 'sistema')
        movimentos_banco = carregar_dados_temporarios(session_id, 'banco')
        
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
