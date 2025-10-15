# Conciliação de Lançamentos - Routes
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
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill
from .bank_parser import BankFileParser  # Importa parser atualizado
from .conciliacao_service import (
    ConciliacaoService,
    MovimentoBanco as MovimentoBancoDTO,
    MovimentoSistema as MovimentoSistemaDTO
)

# Configurar blueprint
conciliacao_lancamentos_bp = Blueprint('fin_conciliacao_lancamentos', __name__, 
                                      template_folder='templates',
                                      static_folder='static',
                                      url_prefix='/financeiro/conciliacao-lancamentos')

# Configurar logging
logger = logging.getLogger(__name__)

# Configurações de upload
UPLOAD_FOLDER = '/tmp/conciliacao_uploads'
ALLOWED_EXTENSIONS = {'ofx', 'xlsx', 'txt'}  # Formatos suportados na conciliação
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB

# Criar pasta de upload se não existir
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Bypass API key para testes
API_BYPASS_KEY = os.getenv('API_BYPASS_KEY', 'uniq_api_2025_dev_bypass_key')

def normalizar_nome_banco(nome_banco: str) -> str:
    """
    Normaliza os nomes dos bancos do sistema para ficar igual aos identificadores dos arquivos OFX
    
    Mapeamento:
    - bb (OFX) → banco_brasil
    - itau (OFX) → itau  
    - santander (OFX) → santander
    """
    if not nome_banco:
        return 'desconhecido'
    
    nome_limpo = nome_banco.strip().upper()
    
    # Mapeamento de nomes variados para identificadores padronizados
    mapeamento_bancos = {
        # Banco do Brasil - várias variações
        'BANCO DO BRASIL': 'banco_brasil',
        'BB': 'banco_brasil',
        'BRASIL': 'banco_brasil',
        'BANCO BRASIL': 'banco_brasil',
        
        # Itaú - várias variações
        'ITAU': 'itau',
        'ITAÚ': 'itau',
        'BANCO ITAU': 'itau',
        'BANCO ITAÚ': 'itau',
        
        # Santander - várias variações
        'SANTANDER': 'santander',
        'BANCO SANTANDER': 'santander',
        
        # Outros bancos - mantém identificador único
        'BRADESCO': 'bradesco',
        'SICOOB': 'sicoob', 
        'CAIXA': 'caixa',
        'CAIXA ECONOMICA': 'caixa',
        'XP INVESTIMENTO': 'xp_investimento',
        'XP RENDIMENTOS': 'xp_rendimentos',
        'INTER': 'inter',
        'NUBANK': 'nubank',
        'C6': 'c6'
    }
    
    # Procurar por correspondência exata primeiro
    if nome_limpo in mapeamento_bancos:
        return mapeamento_bancos[nome_limpo]
    
    # Procurar por correspondência parcial
    for banco_key, banco_id in mapeamento_bancos.items():
        if banco_key in nome_limpo or nome_limpo in banco_key:
            return banco_id
    
    # Se não encontrar, retornar normalizado (minúsculo, sem espaços)
    return nome_limpo.lower().replace(' ', '_').replace('ã', 'a').replace('á', 'a').replace('ê', 'e').replace('ç', 'c')

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
                    
            elif arquivo_path.endswith('.ofx'):
                logger.info(f"[BANCO] Arquivo OFX detectado, usando parser dedicado...")
                # Para OFX, usar o novo parser que detecta automaticamente
                parser = BankFileParser()
                banco_code = parser._detect_bank_from_ofx(arquivo_path)
                
                banco_map = {
                    'BB': 'banco_brasil',
                    'SANTANDER': 'santander', 
                    'ITAU': 'itau'
                }
                
                detected = banco_map.get(banco_code, 'desconhecido')
                logger.info(f"[BANCO] Banco detectado no OFX: {detected}")
                return detected
                
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
    
    def normalize_ref(self, texto: str) -> str:
        """
        Normaliza referência UN conforme especificação do plano:
        - Procura padrões UN[0-9]{2}[./]?[0-9]{4} ou UN [0-9]{2}[./]?[0-9]{4}
        - Remove todos os caracteres não numéricos
        - Retorna padrão limpo (ex: UN257093, UN257020, UN257069)
        - Se ref_unique já for um número, mantém como está
        - Se nenhum padrão UN for encontrado, retorna null
        """
        if not texto:
            return None
        
        texto_str = str(texto).strip()
        
        # Se já é um número puro, mantém como está (dados do sistema)
        if texto_str.isdigit():
            return texto_str
            
        # Padrões UN conforme especificação
        padroes = [
            r'UN\s*\d{2}[./]?\d{4,5}',  # UN25/7093, UN25.7020, UN257069
            r'UN\s*\d{2}\s+\d{4,5}',    # UN 25 7093
            r'UN\s*\d{6,7}',            # UN257093, UN 257093
        ]
        
        for padrao in padroes:
            match = re.search(padrao, texto_str, re.IGNORECASE)
            if match:
                found = match.group()
                # Remove todos os caracteres não numéricos, mantém apenas UN + números
                numeros = re.sub(r'[^0-9]', '', found)
                if len(numeros) >= 6:  # Pelo menos UN + 4 dígitos
                    return f"UN{numeros}"
                
        return None
    
    def extrair_referencia(self, texto: str) -> str:
        """Extrai referência UN do texto (mantido para compatibilidade)"""
        normalized = self.normalize_ref(texto)
        return normalized if normalized else ''
    
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
                    
                    # Extrair e normalizar referência UN
                    texto_completo = f"{historico} {detalhamento}".strip()
                    ref_unique = self.extrair_referencia(texto_completo)
                    ref_unique_norm = self.normalize_ref(texto_completo)
                    
                    lancamento = {
                        'data': data.isoformat(),
                        'data_lancamento': data.isoformat(),
                        'valor': valor,
                        'tipo_lancamento': 'DESPESA' if valor < 0 else 'RECEITA',
                        'descricao_original': texto_completo,
                        'historico': texto_completo,
                        'ref_unique': ref_unique,
                        'ref_unique_norm': ref_unique_norm,
                        'banco_origem': 'BANCO_BRASIL',
                        'banco': 'Banco do Brasil',
                        'documento': str(row[documento_col]).strip() if documento_col else '',
                        'cod_historico': str(row[cod_historico_col]).strip() if cod_historico_col else '',
                        'status': 'PENDENTE',
                        'id_conciliacao': None
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
                    
                    # Extrair e normalizar referência UN
                    ref_unique = self.extrair_referencia(historico)
                    ref_unique_norm = self.normalize_ref(historico)
                    
                    lancamento = {
                        'data': data.isoformat(),
                        'data_lancamento': data.isoformat(),
                        'valor': valor,
                        'tipo_lancamento': 'DESPESA' if valor < 0 else 'RECEITA',
                        'descricao_original': historico,
                        'historico': historico,
                        'ref_unique': ref_unique,
                        'ref_unique_norm': ref_unique_norm,
                        'banco_origem': 'SANTANDER',
                        'banco': 'Santander',
                        'documento': documento,
                        'status': 'PENDENTE',
                        'id_conciliacao': None
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
        """Processa arquivo do Itaú - novo formato CSV com separador ponto e vírgula"""
        logger.info(f"[ITAU] Iniciando processamento de arquivo: {arquivo_path}")
        
        try:
            # Tentar ler como CSV primeiro (novo formato)
            try:
                # Novo formato: data;descrição;valor
                if arquivo_path.lower().endswith('.txt') or arquivo_path.lower().endswith('.csv'):
                    logger.info(f"[ITAU] Processando como CSV/TXT com separador ponto e vírgula")
                    
                    with open(arquivo_path, 'r', encoding='utf-8') as file:
                        linhas = file.readlines()
                    
                    logger.info(f"[ITAU] Arquivo lido com {len(linhas)} linhas")
                    
                    lancamentos = []
                    for i, linha in enumerate(linhas):
                        try:
                            linha = linha.strip()
                            if not linha:
                                continue
                            
                            # Dividir por ponto e vírgula
                            partes = linha.split(';')
                            
                            if len(partes) != 3:
                                logger.warning(f"[ITAU] Linha {i+1} com formato inválido: {linha}")
                                continue
                            
                            data_str, descricao, valor_str = partes
                            
                            # Processar data
                            try:
                                data = datetime.strptime(data_str.strip(), '%d/%m/%Y').date()
                            except ValueError:
                                logger.warning(f"[ITAU] Data inválida na linha {i+1}: {data_str}")
                                continue
                            
                            # Processar valor
                            try:
                                valor_str = valor_str.strip().replace(',', '.')
                                valor = float(valor_str)
                            except ValueError:
                                logger.warning(f"[ITAU] Valor inválido na linha {i+1}: {valor_str}")
                                continue
                            
                            # Processar descrição
                            descricao = descricao.strip()
                            
                            # Extrair e normalizar referência UN
                            ref_unique = self.extrair_referencia(descricao)
                            ref_unique_norm = self.normalize_ref(descricao)
                            
                            # Criar lançamento conforme especificação
                            lancamento = {
                                'data': data.isoformat(),
                                'data_lancamento': data.isoformat(),
                                'valor': valor,
                                'tipo_lancamento': 'DESPESA' if valor < 0 else 'RECEITA',
                                'descricao_original': descricao,
                                'historico': descricao,
                                'ref_unique': ref_unique,
                                'ref_unique_norm': ref_unique_norm,
                                'banco_origem': 'ITAU',
                                'banco': 'Itaú',
                                'tipo': 'Débito' if valor < 0 else 'Crédito',
                                'status': 'PENDENTE',
                                'id_conciliacao': None
                            }
                            
                            lancamentos.append(lancamento)
                            logger.debug(f"[ITAU] Linha {i+1}: Data={data}, Valor={valor}, Desc={descricao[:30]}...")
                            
                        except Exception as e:
                            logger.warning(f"[ITAU] Erro ao processar linha {i+1}: {e}")
                            continue
                    
                    logger.info(f"[ITAU] {len(lancamentos)} lançamentos processados com sucesso (novo formato)")
                    return lancamentos
                
                # Fallback para formato Excel antigo
                else:
                    logger.info(f"[ITAU] Tentando processar como Excel (formato antigo)")
                    return self.processar_itau_excel_antigo(arquivo_path)
                    
            except Exception as e:
                logger.warning(f"[ITAU] Erro no formato CSV, tentando Excel: {e}")
                return self.processar_itau_excel_antigo(arquivo_path)
            
        except Exception as e:
            logger.error(f"[ITAU] Erro geral ao processar arquivo: {e}")
            return []
    
    def processar_itau_excel_antigo(self, arquivo_path: str) -> List[Dict]:
        """Processa arquivo do Itaú no formato Excel antigo (fallback)"""
        logger.info(f"[ITAU] Processando formato Excel antigo: {arquivo_path}")
        
        try:
            df = pd.read_excel(arquivo_path, dtype=str)
            logger.info(f"[ITAU] Arquivo Excel carregado com {len(df)} linhas e {len(df.columns)} colunas")
            
            # Encontrar início dos dados
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
                    logger.warning(f"[ITAU] Erro ao processar linha Excel: {e}")
                    continue
            
            logger.info(f"[ITAU] {len(lancamentos)} lançamentos processados (formato Excel)")
            return lancamentos
            
        except Exception as e:
            logger.error(f"[ITAU] Erro ao processar Excel: {e}")
            return []
    
    def processar_arquivo(self, arquivo_path: str, banco: str = None) -> Dict:
        """Processa arquivo de qualquer banco (OFX ou formatos legados)"""
        
        if not os.path.exists(arquivo_path):
            return {'success': False, 'message': 'Arquivo não encontrado'}
        
        nome_arquivo = os.path.basename(arquivo_path)
        file_ext = os.path.splitext(arquivo_path)[1].lower()
        
        logger.info(f"[PROCESSAMENTO] Arquivo: {nome_arquivo}, Extensão: {file_ext}")
        
        try:
            # Para arquivos OFX, usar o novo parser unificado
            if file_ext == '.ofx':
                logger.info(f"[OFX] Usando parser OFX unificado para {nome_arquivo}")
                parser = BankFileParser()
                resultado = parser.parse_file(arquivo_path)
                
                if "erro" in resultado:
                    return {'success': False, 'message': resultado['erro']}
                
                # Converte formato do parser para formato esperado pelas rotas
                lancamentos = []
                for mov in resultado.get('movimentos', []):
                    lancamento = {
                        'data': mov['data'],
                        'descricao': mov['descricao'],
                        'valor': mov['valor'],
                        'tipo': mov['tipo'],
                        'ref_unique': mov.get('ref_unique'),
                        'linha_origem': mov.get('linha_origem', 0)
                    }
                    lancamentos.append(lancamento)
                
                return {
                    'success': True,
                    'banco_identificado': resultado.get('codigo_banco', 'OFX').lower(),
                    'banco_nome': resultado.get('banco', 'Banco OFX'),
                    'conta': resultado.get('conta', 'N/A'),
                    'total_lancamentos': len(lancamentos),
                    'lancamentos': lancamentos,
                    'formato': 'OFX',
                    'info_adicional': {
                        'data_processamento': resultado.get('data_processamento'),
                        'conta': resultado.get('conta'),
                        'agencia': resultado.get('agencia')
                    }
                }
            
            # Para formatos legados (xlsx, txt, csv)
            if not banco:
                banco = self.identificar_banco(arquivo_path, nome_arquivo)
            
            if banco == 'desconhecido':
                return {'success': False, 'message': 'Não foi possível identificar o banco do arquivo'}
            
            logger.info(f"[LEGADO] Processando arquivo {nome_arquivo} como {banco}")
            
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
                'movimentos': lancamentos
            }
            
        except Exception as e:
            return {'success': False, 'message': f'Erro ao processar arquivo: {str(e)}'}

@conciliacao_lancamentos_bp.route('/')
@login_required
@perfil_required('financeiro', 'conciliacao_lancamentos')
def index():
    """Página principal da conciliação de lançamentos."""
    try:
        # Verificar bypass da API primeiro
        if verificar_api_bypass():
            logger.info(f"[CONCILIACAO] Acesso via bypass da API")
            return render_template('conciliacao_lancamentos/conciliacao_lancamentos.html',
                                 module_name='Conciliação de Lançamentos',
                                 page_title='Conciliação de Lançamentos')
        
        # Log de acesso
        access_logger.log_page_access('Conciliação de Lançamentos', 'financeiro')
        
        # Buscar dados iniciais se necessário
        user = session.get('user', {})
        logger.info(f"[CONCILIACAO] Usuário {user.get('email')} acessou Conciliação de Lançamentos")
        
        return render_template('conciliacao_lancamentos/conciliacao_lancamentos.html',
                             module_name='Conciliação de Lançamentos',
                             page_title='Conciliação de Lançamentos')
        
    except Exception as e:
        logger.error(f"[CONCILIACAO] Erro ao carregar página: {str(e)}")
        if request.is_json:
            return jsonify({'error': f'Erro interno: {str(e)}'}), 500
        return redirect(url_for('dashboard.dashboard_main'))

@conciliacao_lancamentos_bp.route('/processar', methods=['POST'])
def carregar_dados_conciliacao():
    """Carregar dados da tabela fin_conciliacao_movimentos e simular extrato bancário."""
    try:
        logger.info("[PROCESSAR] Carregando dados para conciliação")
        
        # Verificar bypass da API ou autenticação
        if not (verificar_api_bypass() or (session.get('user', {}).get('role') in ['admin', 'interno_unique'])):
            logger.warning("[PROCESSAR] Acesso negado - sem bypass ou autenticação")
            return jsonify({'error': 'Acesso negado'}), 403
        
        # Obter parâmetros
        banco_selecionado = request.form.get('banco', 'todos')
        periodo = request.form.get('periodo', 'mes_atual')
        
        logger.info(f"[PROCESSAR] Banco: {banco_selecionado}, Período: {periodo}")
        
        # Calcular período baseado na seleção
        from datetime import datetime, timedelta
        hoje = datetime.now()
        
        if periodo == 'personalizado':
            data_inicio = request.form.get('data_inicio')
            data_fim = request.form.get('data_fim')
        elif periodo == 'mes_atual':
            data_inicio = hoje.replace(day=1).strftime('%Y-%m-%d')
            data_fim = hoje.strftime('%Y-%m-%d')
        elif periodo == 'mes_anterior':
            primeiro_mes_anterior = (hoje.replace(day=1) - timedelta(days=1)).replace(day=1)
            ultimo_mes_anterior = hoje.replace(day=1) - timedelta(days=1)
            data_inicio = primeiro_mes_anterior.strftime('%Y-%m-%d')
            data_fim = ultimo_mes_anterior.strftime('%Y-%m-%d')
        else:  # ultimos_30_dias
            data_inicio = (hoje - timedelta(days=30)).strftime('%Y-%m-%d')
            data_fim = hoje.strftime('%Y-%m-%d')
        
        logger.info(f"[PROCESSAR] Período calculado: {data_inicio} a {data_fim}")
        
        # Buscar dados do sistema (fin_conciliacao_movimentos)
        query_sistema = supabase.table('fin_conciliacao_movimentos').select(
            'id, data_lancamento, nome_banco, numero_conta, tipo_lancamento, '
            'valor, descricao, ref_unique, status'
        ).gte('data_lancamento', data_inicio).lte('data_lancamento', data_fim)
        
        # Aplicar filtro de banco se especificado
        if banco_selecionado and banco_selecionado != 'todos':
            query_sistema = query_sistema.ilike('nome_banco', f'%{banco_selecionado}%')
        
        response_sistema = query_sistema.order('data_lancamento', desc=True).execute()
        
        dados_sistema = []
        if response_sistema.data:
            for item in response_sistema.data:
                movimento = {
                    'id': item.get('id'),
                    'data_lancamento': item.get('data_lancamento'),
                    'nome_banco': item.get('nome_banco', 'N/A'),
                    'numero_conta': item.get('numero_conta', 'N/A'),
                    'tipo_lancamento': item.get('tipo_lancamento', 'N/A'),
                    'valor': float(item.get('valor', 0)),
                    'descricao': item.get('descricao') or 'Sem descrição',
                    'ref_unique': item.get('ref_unique'),
                    'status': 'pendente'  # Para conciliação
                }
                dados_sistema.append(movimento)
        
        # Usar dados reais do banco da sessão (se disponíveis)
        dados_banco = []
        movimentos_banco_sessao = session.get('movimentos_banco', [])
        
        if movimentos_banco_sessao:
            logger.info(f"[PROCESSAR] Usando dados do banco da sessão: {len(movimentos_banco_sessao)} registros")
            # Usar dados reais do upload do banco
            for movimento in movimentos_banco_sessao:
                dados_banco.append({
                    'id': movimento.get('id', f"banco_{len(dados_banco) + 1}"),
                    'data': movimento.get('data'),
                    'nome_banco': movimento.get('banco', 'N/A'),
                    'numero_conta': movimento.get('conta', 'N/A'),
                    'valor': float(movimento.get('valor', 0)),
                    'descricao': movimento.get('descricao', ''),
                    'tipo': movimento.get('tipo', 'N/A'),
                    'ref_unique': movimento.get('ref_unique'),
                    'status': 'pendente'
                })
        else:
            logger.warning("[PROCESSAR] Nenhum dado do banco encontrado na sessão - usando simulação limitada")
            # Fallback: simular alguns dados para teste (apenas 3 registros)
            for item in dados_sistema[:3]:
                movimento_banco = {
                    'id': f"banco_{item['id']}",
                    'data': item['data_lancamento'],
                    'nome_banco': item['nome_banco'],
                    'numero_conta': item['numero_conta'],
                    'valor': item['valor'],
                    'descricao': f"Extrato: {item['descricao'][:50]}...",
                    'historico': item['descricao'],
                    'status': 'pendente'
                }
                dados_banco.append(movimento_banco)
        
        logger.info(f"[PROCESSAR] Dados carregados - Sistema: {len(dados_sistema)}, Banco: {len(dados_banco)}")
        
        # Resultado de sucesso
        resultado = {
            'success': True,
            'dados_aberta': dados_sistema,  # Nome esperado pelo frontend
            'dados_banco': dados_banco,
            'status': {
                'banco_identificado': banco_selecionado if banco_selecionado != 'todos' else 'Todos os bancos',
                'formato_arquivo': 'Dados da tabela fin_conciliacao_movimentos',
                'registros_banco': len(dados_banco),
                'registros_sistema': len(dados_sistema),
                'periodo': f"{data_inicio} a {data_fim}"
            }
        }
        
        return jsonify(resultado)
        
    except Exception as e:
        logger.error(f"[PROCESSAR] Erro inesperado: {str(e)}", exc_info=True)
        return jsonify({'success': False, 'error': f'Erro interno: {str(e)}'}), 500
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
        
        arquivos_recebidos = request.files.getlist('arquivo_bancario')
        if not arquivos_recebidos:
            arquivos_recebidos = request.files.getlist('arquivo')

        if not arquivos_recebidos:
            logger.error("[PROCESSAR] Campo de arquivo não encontrado nos files")
            return jsonify({'success': False, 'error': 'Nenhum arquivo enviado'}), 400

        if len(arquivos_recebidos) > 1:
            logger.info(f"[PROCESSAR] {len(arquivos_recebidos)} arquivos recebidos - processando apenas o primeiro")

        arquivo = arquivos_recebidos[0]
        if not arquivo or arquivo.filename == '':
            logger.error("[PROCESSAR] Arquivo vazio ou sem nome")
            return jsonify({'success': False, 'error': 'Nenhum arquivo selecionado'}), 400
        
        logger.info(f"[PROCESSAR] Arquivo recebido: {arquivo.filename}")
        
        # Verificar se é um tipo de arquivo permitido
        if not allowed_file(arquivo.filename):
            logger.error(f"[PROCESSAR] Tipo de arquivo não permitido: {arquivo.filename}")
            return jsonify({'success': False, 'error': 'Formato não suportado. Aceitamos arquivos OFX, XLSX ou TXT exportados do internet banking.'}), 400
        
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
                    # Normalizar dados do sistema usando ProcessadorBancos
                    processador = ProcessadorBancos()
                    dados_sistema_normalizados = []
                    
                    for mov in response_sistema.data:
                        # Normalizar referência do sistema
                        ref_unique_original = mov.get('ref_unique', '')
                        ref_unique_norm = processador.normalize_ref(ref_unique_original)
                        
                        # Estrutura normalizada conforme especificação
                        movimento_normalizado = {
                            'id': f"sistema_{mov.get('ref_unique', '')}_h{hash(str(mov))}",
                            'data_lancamento': mov.get('data_lancamento'),
                            'valor': float(mov.get('valor', 0)),
                            'tipo_lancamento': mov.get('tipo_lancamento', ''),
                            'descricao_original': mov.get('descricao', ''),
                            'ref_unique': ref_unique_original,
                            'ref_unique_norm': ref_unique_norm,
                            'categoria': mov.get('categoria', ''),
                            'centro_resultado': mov.get('centro_resultado', ''),
                            'classe': mov.get('classe', ''),
                            'origem': 'SISTEMA_FINANCEIRO',
                            'status': 'PENDENTE',
                            'id_conciliacao': None
                        }
                        dados_sistema_normalizados.append(movimento_normalizado)
                    
                    dados_sistema = dados_sistema_normalizados
                    logger.info(f"[PROCESSAR] {len(dados_sistema)} movimentos do sistema normalizados")
                else:
                    dados_sistema = []
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
            
            # Retornar no formato especificado pelo plano detalhado
            return jsonify({
                'success': True,
                'dados_aberta': dados_sistema,     # Dados do sistema conforme especificação
                'dados_banco': resultado['data'],   # Dados dos bancos conforme especificação
                'status': {
                    'banco_identificado': resultado['banco'],
                    'formato_arquivo': resultado['arquivo'].split('.')[-1].upper() if 'arquivo' in resultado else 'CSV',
                    'registros_banco': len(resultado['data']),
                    'registros_sistema': len(dados_sistema),
                    'periodo': f"{data_inicio} a {data_fim}"
                },
                # Compatibilidade com frontend existente
                'dados_sistema': dados_sistema,
                'dados_bancarios': resultado['data']
            })
        else:
            logger.error(f"[PROCESSAR] Falha no processamento: {resultado['error']}")
            return jsonify({'success': False, 'message': resultado['error']}), 400
            
    except Exception as e:
        logger.error(f"[PROCESSAR] Erro inesperado: {str(e)}", exc_info=True)
        return jsonify({'success': False, 'error': f'Erro interno: {str(e)}'}), 500


def allowed_file(filename):
    """Verifica se o arquivo tem uma extensão permitida."""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@conciliacao_lancamentos_bp.route('/upload-arquivo', methods=['POST'])
def upload_arquivo_banco():
    """Upload e processamento de arquivos bancários (Excel para BB/Bradesco, TXT para Itaú)."""
    try:
        # Verificar bypass da API ou autenticação
        if not (verificar_api_bypass() or (session.get('user', {}).get('role') in ['admin', 'interno_unique'])):
            return jsonify({'error': 'Acesso negado'}), 403

        logger.info("[UPLOAD] Iniciando upload de arquivo bancário")

        # Compatibilidade com novos frontends (permite múltiplos arquivos)
        arquivos_env = request.files.getlist('arquivo_bancario')
        if not arquivos_env:
            arquivos_env = request.files.getlist('arquivo')

        if not arquivos_env:
            logger.warning("[UPLOAD] Nenhum arquivo foi enviado")
            return jsonify({'success': False, 'error': 'Nenhum arquivo foi enviado'}), 400

        if len(arquivos_env) > 1:
            logger.info(f"[UPLOAD] {len(arquivos_env)} arquivos recebidos - processando apenas o primeiro")

        file = arquivos_env[0]
        banco_selecionado = request.form.get('banco_origem', '').strip()

        if file.filename == '':
            logger.warning("[UPLOAD] Nome do arquivo está vazio")
            return jsonify({'success': False, 'error': 'Nome do arquivo está vazio'}), 400

        if not allowed_file(file.filename):
            logger.warning(f"[UPLOAD] Extensão de arquivo não permitida: {file.filename}")
            return jsonify({'success': False, 'error': 'Formato não suportado. Aceitamos arquivos OFX, XLSX ou TXT exportados do internet banking.'}), 400

        # Verificar tamanho do arquivo
        file.seek(0, 2)  # Mover para o final do arquivo
        file_size = file.tell()
        file.seek(0)  # Voltar para o início

        if file_size > MAX_FILE_SIZE:
            logger.warning(f"[UPLOAD] Arquivo muito grande: {file_size} bytes")
            return jsonify({'success': False, 'error': f'Arquivo muito grande. Máximo permitido: {MAX_FILE_SIZE/1024/1024:.1f}MB'}), 400

        # Salvar arquivo temporariamente
        filename = secure_filename(file.filename)
        unique_filename = f"{uuid.uuid4()}_{filename}"
        arquivo_path = os.path.join(UPLOAD_FOLDER, unique_filename)
        
        logger.info(f"[UPLOAD] Salvando arquivo em: {arquivo_path}")
        file.save(arquivo_path)

        # Processar arquivo usando a classe ProcessadorBancos (método unificado)
        processador = ProcessadorBancos()
        resultado = processador.processar_arquivo(arquivo_path)
        
        if not resultado['success']:
            logger.error(f"[UPLOAD] Erro no processamento: {resultado.get('message', 'Erro desconhecido')}")
            return jsonify({
                'success': False, 
                'error': resultado.get('message', 'Não foi possível processar o arquivo. Verifique se o formato está correto.')
            }), 400
        
        # Extrair dados do resultado
        banco_identificado = resultado.get('banco_identificado') or resultado.get('codigo_banco') or 'desconhecido'
        conta_identificada = resultado.get('conta') or resultado.get('info_adicional', {}).get('conta') or ''
        banco_legivel = resultado.get('banco_nome') or resultado.get('banco') or banco_identificado
        dados_brutos = resultado.get('lancamentos') or resultado.get('movimentos') or []

        logger.info(f"[UPLOAD] Banco identificado: {banco_identificado}")
        logger.info(f"[UPLOAD] {len(dados_brutos)} lançamentos processados")

        # Normalizar lançamentos para manter estrutura consistente
        lancamentos = []
        for idx, movimento in enumerate(dados_brutos):
            item = dict(movimento)

            # Garantir identificador único
            if not item.get('id'):
                item['id'] = f"{banco_identificado}_{uuid.uuid4().hex}"

            # Normalizar datas para formato ISO (YYYY-MM-DD)
            data_valor = item.get('data') or item.get('data_movimento') or item.get('data_lancamento')
            if isinstance(data_valor, str) and '/' in data_valor:
                try:
                    data_obj = datetime.strptime(data_valor, '%d/%m/%Y')
                    item['data'] = data_obj.strftime('%Y-%m-%d')
                except ValueError:
                    item['data'] = data_valor
            elif data_valor:
                item['data'] = str(data_valor)

            # Garantir valor numérico
            try:
                item['valor'] = float(item.get('valor', 0))
            except (TypeError, ValueError):
                item['valor'] = 0.0

            # Determinar tipo de movimento
            tipo_movimento = (item.get('tipo') or item.get('tipo_movimento') or '').upper()
            if tipo_movimento not in ['CREDITO', 'DEBITO']:
                tipo_movimento = 'CREDITO' if item['valor'] >= 0 else 'DEBITO'
            item['tipo'] = tipo_movimento

            # Normalizar referências UN/US
            ref_origem = item.get('ref_unique') or item.get('codigo_referencia') or item.get('descricao') or ''
            ref_normalizada = processador.normalize_ref(ref_origem)
            if ref_normalizada:
                item['codigo_referencia'] = ref_normalizada
            item['ref_unique_norm'] = ref_normalizada

            # Enriquecer metadados do banco
            item['banco_origem'] = banco_identificado
            item['banco'] = banco_legivel
            item['nome_banco'] = banco_legivel
            item['conta'] = conta_identificada
            item['numero_conta'] = item.get('numero_conta') or conta_identificada
            item['linha_origem'] = item.get('linha_origem') or (idx + 1)
            item['status'] = item.get('status', 'pendente').lower()

            lancamentos.append(item)

        # Limpar arquivo temporário
        try:
            os.remove(arquivo_path)
            logger.info(f"[UPLOAD] Arquivo temporário removido: {arquivo_path}")
        except Exception as e:
            logger.warning(f"[UPLOAD] Erro ao remover arquivo temporário: {e}")

        # Armazenar na sessão e em arquivos temporários
        session_id = session.get('session_id')
        if not session_id:
            session_id = str(uuid.uuid4())
            session['session_id'] = session_id

        session['arquivo_processado'] = {
            'nome': filename,
            'banco': banco_identificado,
            'banco_nome': banco_legivel,
            'conta': conta_identificada,
            'total_registros': len(lancamentos),
            'data_upload': datetime.now().isoformat()
        }
        session['registros_banco'] = len(lancamentos)
        session['ultimo_upload_banco'] = {
            'banco_identificado': banco_identificado,
            'conta': conta_identificada,
            'total_registros': len(lancamentos)
        }

        salvar_dados_temporarios(session_id, 'banco', lancamentos)
        session.modified = True

        logger.info(f"[UPLOAD] Upload concluído com sucesso: {len(lancamentos)} lançamentos processados")

        return jsonify({
            'success': True,
            'message': f'Arquivo processado com sucesso! {len(lancamentos)} lançamentos encontrados.',
            'data': {
                'total_registros': len(lancamentos),
                'banco_identificado': banco_identificado,
                'banco_nome': banco_legivel,
                'conta': conta_identificada,
                'nome_arquivo': filename,
                'lancamentos': lancamentos  # Retornar todos os lançamentos
            }
        })

    except Exception as e:
        logger.error(f"[UPLOAD] Erro no upload: {str(e)}", exc_info=True)
        return jsonify({'success': False, 'error': f'Erro no processamento: {str(e)}'}), 500


@conciliacao_lancamentos_bp.route('/api/movimentos-fin-conciliacao')
def movimentos_fin_conciliacao():
    """Buscar movimentos da nova tabela fin_conciliacao_movimentos."""
    try:
        # Verificar bypass da API ou autenticação
        if not (verificar_api_bypass() or (session.get('user', {}).get('role') in ['admin', 'interno_unique'])):
            return jsonify({'error': 'Acesso negado'}), 403
        
        logger.info("[CONCILIACAO] Buscando movimentos da tabela fin_conciliacao_movimentos")
        
        # Parâmetros de filtro
        banco_filtro = request.args.get('banco', 'todos')
        empresa_filtro = request.args.get('empresa', 'todas')
        data_inicio = request.args.get('data_inicio')
        data_fim = request.args.get('data_fim')
        
        # Construir query base
        query = supabase.table('fin_conciliacao_movimentos').select('*')
        
        # Aplicar filtro de banco se especificado
        if banco_filtro and banco_filtro != 'todos':
            query = query.ilike('nome_banco', f'%{banco_filtro}%')
        
        # Aplicar filtro de data se especificado
        if data_inicio:
            query = query.gte('data_lancamento', data_inicio)
        if data_fim:
            query = query.lte('data_lancamento', data_fim)
        
        # Executar query
        response = query.order('data_lancamento', desc=True).limit(1000).execute()
        
        if response.data:
            movimentos = []
            for item in response.data:
                movimento = {
                    'id': item.get('id'),
                    'data_lancamento': item.get('data_lancamento'),
                    'nome_banco': item.get('nome_banco'),
                    'numero_conta': item.get('numero_conta'),
                    'tipo_lancamento': item.get('tipo_lancamento'),
                    'valor': float(item.get('valor', 0)),
                    'descricao': item.get('descricao'),
                    'ref_unique': item.get('ref_unique'),
                    'status': 'pendente'  # Status padrão para conciliação
                }
                movimentos.append(movimento)
            
            logger.info(f"[CONCILIACAO] Encontrados {len(movimentos)} movimentos na tabela fin_conciliacao_movimentos")
            
            return jsonify({
                'success': True,
                'count': len(movimentos),
                'data': movimentos,
                'filtros': {
                    'banco': banco_filtro,
                    'data_inicio': data_inicio,
                    'data_fim': data_fim
                }
            })
        else:
            logger.warning("[CONCILIACAO] Nenhum movimento encontrado na tabela fin_conciliacao_movimentos")
            return jsonify({
                'success': True,
                'count': 0,
                'data': [],
                'message': 'Nenhum movimento encontrado'
            })
            
    except Exception as e:
        logger.error(f"[CONCILIACAO] Erro ao buscar movimentos fin_conciliacao_movimentos: {str(e)}", exc_info=True)
        return jsonify({'success': False, 'error': f'Erro interno: {str(e)}'}), 500

@conciliacao_lancamentos_bp.route('/api/movimentos-sistema')
def movimentos_sistema():
    """Buscar movimentos da tabela fin_conciliacao_movimentos para conciliação."""
    try:
        # Verificar bypass da API ou autenticação
        if not (verificar_api_bypass() or (session.get('user', {}).get('role') in ['admin', 'interno_unique'])):
            return jsonify({'error': 'Acesso negado'}), 403
        
        logger.info("[CONCILIACAO] Buscando movimentos da tabela fin_conciliacao_movimentos")
        
        # Parâmetros de filtro
        banco_filtro = request.args.get('banco', 'todos')
        empresa_filtro = request.args.get('empresa', 'todas')
        data_inicio = request.args.get('data_inicio')
        data_fim = request.args.get('data_fim')
        
        # Se não informar datas, usar o mês atual
        if not data_inicio or not data_fim:
            hoje = datetime.now()
            data_inicio = hoje.replace(day=1).strftime('%Y-%m-%d')
            data_fim = hoje.strftime('%Y-%m-%d')
        
        logger.info(
            "[CONCILIACAO] Filtros - Banco: %s, Empresa: %s, Data: %s a %s",
            banco_filtro,
            empresa_filtro,
            data_inicio,
            data_fim
        )

        processador = ProcessadorBancos()
        
        # Construir query base
        query = supabase.table('fin_conciliacao_movimentos').select(
            'id, data_lancamento, nome_banco, numero_conta, tipo_lancamento, '
            'valor, descricao, ref_unique, status, empresa'
        )
        
        # Aplicar filtro de data
        query = query.gte('data_lancamento', data_inicio).lte('data_lancamento', data_fim)
        
        # Aplicar filtro de banco se especificado
        if banco_filtro and banco_filtro != 'todos':
            query = query.ilike('nome_banco', f'%{banco_filtro}%')
        if empresa_filtro and empresa_filtro.lower() != 'todas':
            query = query.ilike('empresa', f'%{empresa_filtro}%')
        
        # Executar query (sem limite para pegar todos os registros do período)
        response = query.order('data_lancamento', desc=True).execute()
        
        if response.data:
            movimentos = []
            for item in response.data:
                # Normalizar nome do banco para ficar igual aos identificadores OFX
                nome_banco_original = item.get('nome_banco', 'N/A')
                nome_banco_normalizado = normalizar_nome_banco(nome_banco_original)
                ref_original = item.get('ref_unique') or ''
                ref_normalizada = processador.normalize_ref(ref_original)
                
                movimento = {
                    'id': item.get('id'),
                    'data_lancamento': item.get('data_lancamento'),
                    'nome_banco': nome_banco_normalizado,  # Nome normalizado
                    'nome_banco_original': nome_banco_original,  # Manter original para debug
                    'numero_conta': item.get('numero_conta', 'N/A'),
                    'tipo_lancamento': item.get('tipo_lancamento', 'N/A'),
                    'valor': float(item.get('valor', 0)),
                    'descricao': item.get('descricao') or 'Sem descrição',
                    'ref_unique': item.get('ref_unique'),
                    'ref_unique_norm': ref_normalizada,
                    'status': item.get('status', 'PENDENTE').lower(),
                    'empresa': item.get('empresa')
                }
                movimentos.append(movimento)
            
            logger.info(f"[CONCILIACAO] Encontrados {len(movimentos)} movimentos do sistema")

            # Persistir dados para conciliação automática
            session_id = session.get('session_id')
            if not session_id:
                session_id = str(uuid.uuid4())
                session['session_id'] = session_id

            session['registros_sistema'] = len(movimentos)
            session['ultimo_carregamento_sistema'] = {
                'banco': banco_filtro,
                'empresa': empresa_filtro,
                'data_inicio': data_inicio,
                'data_fim': data_fim,
                'total_registros': len(movimentos)
            }
            salvar_dados_temporarios(session_id, 'sistema', movimentos)
            session.modified = True
            
            return jsonify({
                'success': True,
                'data': movimentos,
                'total': len(movimentos),
                'filtros': {
                    'banco': banco_filtro,
                    'empresa': empresa_filtro,
                    'data_inicio': data_inicio,
                    'data_fim': data_fim
                }
            })
        else:
            logger.warning("[CONCILIACAO] Nenhum movimento encontrado")
            return jsonify({
                'success': True,
                'data': [],
                'total': 0,
                'message': 'Nenhum movimento encontrado para o período',
                'filtros': {
                    'banco': banco_filtro,
                    'empresa': empresa_filtro,
                    'data_inicio': data_inicio,
                    'data_fim': data_fim
                }
            })
        
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
                # Inicializar processador para usar normalize_ref
                processador = ProcessadorBancos()
                
                movimentos = []
                for mov in response.data:
                    # Normalizar referência do sistema
                    ref_unique_original = mov.get('ref_unique', '')
                    ref_unique_norm = processador.normalize_ref(ref_unique_original)
                    
                    # Padronizar campos conforme especificação
                    movimento_padronizado = {
                        'id': f"sistema_{mov.get('ref_unique', '')}_h{hash(str(mov))}",
                        'data_movimento': mov.get('data_lancamento'),
                        'data_lancamento': mov.get('data_lancamento'), 
                        'descricao': mov.get('descricao', ''),
                        'descricao_original': mov.get('descricao', ''),
                        'valor': float(mov.get('valor', 0)),
                        'tipo_movimento': mov.get('tipo_lancamento', ''),
                        'tipo_lancamento': mov.get('tipo_lancamento', ''),
                        'categoria': mov.get('categoria', ''),
                        'centro_resultado': mov.get('centro_resultado', ''),
                        'classe': mov.get('classe', ''),
                        'ref_unique': ref_unique_original,
                        'ref_unique_norm': ref_unique_norm,
                        'origem': 'SISTEMA_FINANCEIRO',
                        'status': 'PENDENTE',
                        'id_conciliacao': None
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
        keys_to_remove = [
            'session_id',
            'banco_identificado',
            'arquivo_processado',
            'registros_banco',
            'registros_sistema',
            'periodo_conciliacao',
            'movimentos_sistema',
            'movimentos_banco',
            'resultado_conciliacao'
        ]
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

        session_id = session.get('session_id')
        movimentos_sistema = []
        movimentos_banco = []

        if session_id:
            movimentos_sistema = carregar_dados_temporarios(session_id, 'sistema') or []
            movimentos_banco = carregar_dados_temporarios(session_id, 'banco') or []

        # Fallback para dados em sessão caso temporários estejam vazios
        if not movimentos_sistema:
            movimentos_sistema = session.get('movimentos_sistema', [])
        if not movimentos_banco:
            movimentos_banco = session.get('movimentos_banco', [])

        if not session_id:
            session_id = str(uuid.uuid4())
            session['session_id'] = session_id

        logger.info(
            "[CONCILIACAO] Dados carregados - Sistema: %s | Banco: %s",
            len(movimentos_sistema),
            len(movimentos_banco)
        )

        if not movimentos_sistema:
            return jsonify({'success': False, 'error': 'Movimentos do sistema não encontrados'}), 400
        if not movimentos_banco:
            return jsonify({'success': False, 'error': 'Movimentos bancários não encontrados'}), 400

        resultado = executar_conciliacao_automatica(movimentos_sistema, movimentos_banco)
        if resultado.get('erro'):
            logger.error("[CONCILIACAO] Erro na conciliação: %s", resultado['erro'])
            return jsonify({'success': False, 'error': resultado['erro']}), 500

        session['resultado_conciliacao'] = resultado

        # Persistir datasets atualizados
        salvar_dados_temporarios(session_id, 'sistema', movimentos_sistema)
        salvar_dados_temporarios(session_id, 'banco', movimentos_banco)

        response_payload = {
            'dados_aberta': resultado.get('dados_aberta', []),
            'dados_banco': resultado.get('dados_banco', []),
            'status': resultado.get('status', {}),
            'relatorio': resultado.get('relatorio'),
            'id_conciliacao': session_id,
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }

        logger.info(
            "[CONCILIACAO] Conciliação concluída - %s registros conciliados",
            resultado.get('status', {}).get('conciliados_automatico', 0)
        )

        return jsonify({'success': True, 'data': response_payload})
        
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


def salvar_dados_temporarios(session_id, tipo, dados):
    """Persiste dados de conciliação em arquivos temporários"""
    try:
        import tempfile
        import pickle

        temp_dir = tempfile.gettempdir()
        arquivo = os.path.join(temp_dir, f"{tipo}_{session_id}.pkl")

        with open(arquivo, 'wb') as handler:
            pickle.dump(dados, handler, protocol=pickle.HIGHEST_PROTOCOL)

        logger.debug(f"Dados temporários salvos: {arquivo} ({len(dados)} registros)")
    except Exception as e:
        logger.error(f"Erro ao salvar dados temporários {tipo}: {e}")

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
            logger.info(f"[UPLOAD] Banco identificado: {resultado.get('banco_identificado', 'N/A')}")
            logger.info(f"[UPLOAD] Total de lançamentos: {resultado.get('total_lancamentos', 0)}")
            
            return {
                'success': True,
                'data': resultado.get('lancamentos', []),
                'arquivo': filename,
                'banco': resultado.get('banco_identificado', 'N/A'),
                'registros_processados': resultado.get('total_lancamentos', 0),
                'formato': resultado.get('formato', 'N/A'),
                'conta': resultado.get('conta', 'N/A'),
                'info_adicional': resultado.get('info_adicional', {})
            }
        else:
            error_msg = resultado.get('message', 'Erro desconhecido no processamento')
            logger.error(f"[UPLOAD] Falha no processamento: {error_msg}")
            return {'success': False, 'error': error_msg}
        
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        logger.error(f"[UPLOAD] Erro inesperado ao processar {filename}: {str(e)}")
        logger.error(f"[UPLOAD] Stack trace completo: {error_details}")
        
        # Garantir limpeza do arquivo temporário
        if filepath and os.path.exists(filepath):
            try:
                os.remove(filepath)
                logger.info(f"[UPLOAD] Arquivo temporário removido após erro: {filepath}")
            except:
                logger.warning(f"[UPLOAD] Não foi possível remover arquivo temporário: {filepath}")
                
        return {'success': False, 'error': f'Erro no processamento: {str(e)}'}

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


def executar_conciliacao_automatica(movimentos_sistema_raw, movimentos_banco_raw):
    """Executa conciliação automática utilizando ConciliacaoService."""
    try:
        logger.info(
            "[CONCILIACAO] Iniciando conciliação - Sistema: %s registros | Banco: %s registros",
            len(movimentos_sistema_raw),
            len(movimentos_banco_raw)
        )

        if not movimentos_sistema_raw:
            return {'erro': 'Nenhum movimento do sistema carregado'}
        if not movimentos_banco_raw:
            return {'erro': 'Nenhum movimento bancário carregado'}

        service = ConciliacaoService()
        processador = ProcessadorBancos()

        banco_service_map = {
            'banco_brasil': 'BANCO DO BRASIL',
            'bb': 'BANCO DO BRASIL',
            'banco do brasil': 'BANCO DO BRASIL',
            'itau': 'ITAU',
            'itaú': 'ITAU',
            'banco itau': 'ITAU',
            'santander': 'SANTANDER',
            'banco santander': 'SANTANDER',
            'bradesco': 'BRADESCO'
        }

        def mapear_banco(valor: str) -> str:
            if not valor:
                return 'DESCONHECIDO'
            normalizado = normalizar_nome_banco(valor)
            return banco_service_map.get(normalizado, valor.upper())

        def garantir_iso(data_valor: str) -> str:
            if not data_valor:
                return ''
            texto = str(data_valor)
            if len(texto) >= 10 and texto[4] == '-' and texto[7] == '-':
                return texto[:10]
            if '/' in texto:
                try:
                    return datetime.strptime(texto[:10], '%d/%m/%Y').strftime('%Y-%m-%d')
                except ValueError:
                    return texto
            return texto

        movimentos_sistema_objs: List[MovimentoSistemaDTO] = []
        movimentos_banco_objs: List[MovimentoBancoDTO] = []
        sistema_payload: List[Dict] = []
        banco_payload: List[Dict] = []
        sistema_index_map: Dict[int, int] = {}
        banco_index_map: Dict[int, int] = {}

        # Preparar movimentos do sistema
        for movimento in movimentos_sistema_raw:
            payload = dict(movimento)
            payload['valor'] = float(payload.get('valor', 0) or 0)
            payload['data_lancamento'] = garantir_iso(
                payload.get('data_lancamento') or payload.get('data_movimento') or payload.get('data')
            )
            payload['status'] = payload.get('status', 'pendente').lower()

            ref_norm = payload.get('ref_unique_norm')
            if not ref_norm:
                ref_norm = processador.normalize_ref(payload.get('ref_unique') or payload.get('descricao') or '')
                payload['ref_unique_norm'] = ref_norm

            tipo_lancamento = (payload.get('tipo_lancamento') or '').upper()
            if tipo_lancamento not in ['RECEITA', 'DESPESA']:
                tipo_lancamento = 'RECEITA' if payload['valor'] >= 0 else 'DESPESA'

            banco_sistema = mapear_banco(payload.get('nome_banco_original') or payload.get('nome_banco'))

            movimento_obj = MovimentoSistemaDTO(
                id=str(payload.get('id')),
                data_lancamento=payload['data_lancamento'],
                nome_banco=banco_sistema,
                numero_conta=str(payload.get('numero_conta') or ''),
                tipo_lancamento=tipo_lancamento,
                valor=payload['valor'],
                descricao=payload.get('descricao', ''),
                ref_unique=ref_norm or payload.get('ref_unique')
            )

            movimentos_sistema_objs.append(movimento_obj)
            sistema_index_map[id(movimento_obj)] = len(sistema_payload)
            sistema_payload.append(payload)

        # Preparar movimentos bancários
        for movimento in movimentos_banco_raw:
            payload = dict(movimento)
            payload['valor'] = float(payload.get('valor', 0) or 0)
            payload['data'] = garantir_iso(payload.get('data') or payload.get('data_lancamento'))
            payload['status'] = payload.get('status', 'pendente').lower()

            ref_norm = payload.get('ref_unique_norm')
            if not ref_norm:
                ref_norm = processador.normalize_ref(
                    payload.get('codigo_referencia') or payload.get('ref_unique') or payload.get('descricao') or ''
                )
                payload['ref_unique_norm'] = ref_norm

            tipo_movimento = (payload.get('tipo') or payload.get('tipo_movimento') or '').upper()
            if tipo_movimento not in ['CREDITO', 'DEBITO']:
                tipo_movimento = 'CREDITO' if payload['valor'] >= 0 else 'DEBITO'
            payload['tipo'] = tipo_movimento

            banco_boleto = mapear_banco(payload.get('banco') or payload.get('banco_origem'))

            movimento_obj = MovimentoBancoDTO(
                data=payload['data'],
                data_original=str(payload.get('data_original') or payload['data']),
                descricao=payload.get('descricao') or payload.get('historico') or '',
                valor=payload['valor'],
                valor_original=str(payload.get('valor_original') or payload['valor']),
                tipo=tipo_movimento,
                codigo_referencia=ref_norm,
                linha_origem=int(payload.get('linha_origem') or 0),
                banco=banco_boleto,
                conta=str(payload.get('conta') or payload.get('numero_conta') or '')
            )

            movimentos_banco_objs.append(movimento_obj)
            banco_index_map[id(movimento_obj)] = len(banco_payload)
            banco_payload.append(payload)

        # Executar conciliação
        resultados = service.conciliar_movimentos(movimentos_sistema_objs, movimentos_banco_objs)
        relatorio = service.gerar_relatorio_conciliacao(resultados)

        status_map = {
            'CONCILIADO': 'conciliado',
            'PARCIAL': 'divergente',
            'NAO_CONCILIADO': 'pendente'
        }

        for resultado in resultados:
            idx_sistema = sistema_index_map.get(id(resultado.movimento_sistema))
            if idx_sistema is not None:
                sistema_payload[idx_sistema]['status'] = status_map.get(resultado.status, 'pendente')
                sistema_payload[idx_sistema]['match_score'] = round(resultado.score_match, 2)
                sistema_payload[idx_sistema]['criterios'] = resultado.criterios_atendidos
                sistema_payload[idx_sistema]['match_observacoes'] = resultado.observacoes

            if resultado.movimento_banco:
                idx_banco = banco_index_map.get(id(resultado.movimento_banco))
                if idx_banco is not None:
                    banco_payload[idx_banco]['status'] = status_map.get(resultado.status, 'pendente')
                    banco_payload[idx_banco]['match_score'] = round(resultado.score_match, 2)
                    banco_payload[idx_banco]['criterios'] = resultado.criterios_atendidos
                    banco_payload[idx_banco]['match_observacoes'] = resultado.observacoes

                if idx_banco is not None and idx_sistema is not None:
                    banco_payload[idx_banco]['match_id_sistema'] = sistema_payload[idx_sistema].get('id')
                    sistema_payload[idx_sistema]['match_id_banco'] = banco_payload[idx_banco].get('id')

        # Estatísticas resumidas
        total_sistema = len(sistema_payload)
        total_banco = len(banco_payload)
        conciliados = sum(1 for item in sistema_payload if item.get('status') == 'conciliado')
        divergentes = sum(1 for item in sistema_payload if item.get('status') == 'divergente')
        pendentes = sum(1 for item in sistema_payload if item.get('status') == 'pendente')

        resumo_status = {
            'total_sistema': total_sistema,
            'total_banco': total_banco,
            'conciliados_automatico': conciliados,
            'pendentes_manual': divergentes + pendentes,
            'divergencias': divergentes,
            'duplicatas': 0,
            'valor_total_sistema': sum(item.get('valor', 0) for item in sistema_payload),
            'valor_total_banco': sum(item.get('valor', 0) for item in banco_payload),
            'valor_conciliado': relatorio.get('valores', {}).get('valor_conciliado', 0),
            'taxa_conciliacao': round((conciliados / total_sistema * 100), 2) if total_sistema else 0.0
        }

        return {
            'dados_aberta': sistema_payload,
            'dados_banco': banco_payload,
            'status': resumo_status,
            'relatorio': relatorio
        }

    except Exception as e:
        logger.error(f"[CONCILIACAO] Erro na conciliação automática: {e}", exc_info=True)
        return {'erro': str(e)}


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
