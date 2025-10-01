#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Serviço de Parsing de Arquivos Bancários
Módulo responsável por processar arquivos dos bancos e padronizar em formato JSON
Suporte para Excel, CSV, TXT e OFX (novo)
Author: Sistema UniqueAduaneira
Data: 29/09/2025 - Atualizado para suportar OFX
"""

import pandas as pd
import os
import re
from datetime import datetime
from typing import Dict, List, Optional, Tuple
import logging

# Configuração de logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class BankFileParser:
    """Classe principal para parsing de arquivos bancários"""
    
    def __init__(self):
        self.supported_banks = ['BANCO_DO_BRASIL', 'BANCO_ITAU', 'BANCO_SANTANDER']
        self.supported_formats = ['xlsx', 'xls', 'csv', 'txt', 'ofx']
        
    def parse_date(self, date_str: str) -> Optional[str]:
        """
        Converte data de DD/MM/AAAA para YYYY-MM-DD
        
        Args:
            date_str: String com data no formato DD/MM/AAAA
            
        Returns:
            String com data no formato YYYY-MM-DD ou None se inválida
        """
        try:
            date_str = str(date_str).strip()
            if not date_str or date_str == 'nan':
                return None
                
            # Verifica formato DD/MM/AAAA
            if '/' in date_str and len(date_str.split('/')) == 3:
                parts = date_str.split('/')
                if len(parts[0]) <= 2 and len(parts[1]) <= 2 and len(parts[2]) == 4:
                    day, month, year = parts
                    return f"{year}-{month.zfill(2)}-{day.zfill(2)}"
            
            return None
        except Exception as e:
            logger.warning(f"Erro ao processar data '{date_str}': {e}")
            return None
    
    def parse_valor(self, valor_str: str, detect_negative_as_debit: bool = False) -> Tuple[float, str, bool]:
        """
        Converte valor para float e determina tipo CREDITO/DEBITO
        
        Args:
            valor_str: String com valor monetário
            detect_negative_as_debit: Se True, valores negativos são DEBITO
            
        Returns:
            Tupla (valor_float, tipo, is_negative)
        """
        try:
            valor_clean = str(valor_str).strip().replace(' ', '')
            
            if not valor_clean or valor_clean in ['nan', 'None']:
                return 0.0, "CREDITO", False
            
            # Detecta sinal negativo
            is_negative = valor_clean.startswith('-')
            valor_clean = valor_clean.replace('-', '').replace('+', '')
            
            # Trata formato brasileiro: 1.234.567,89
            if ',' in valor_clean and '.' in valor_clean:
                # Remove pontos de milhares e substitui vírgula por ponto decimal
                valor_clean = valor_clean.replace('.', '').replace(',', '.')
            elif ',' in valor_clean:
                # Apenas vírgula decimal
                valor_clean = valor_clean.replace(',', '.')
            
            valor_float = abs(float(valor_clean))
            
            # Determina tipo
            if detect_negative_as_debit:
                tipo = "DEBITO" if is_negative else "CREDITO"
            else:
                tipo = "CREDITO"  # Será definido externamente para Banco do Brasil
                
            return valor_float, tipo, is_negative
            
        except Exception as e:
            logger.warning(f"Erro ao processar valor '{valor_str}': {e}")
            return 0.0, "CREDITO", False
    
    def extract_reference_code(self, descricao: str) -> Optional[str]:
        """
        Extrai código de referência da descrição
        
        Args:
            descricao: Texto da descrição do movimento
            
        Returns:
            Código de referência encontrado ou None
        """
        if not descricao:
            return None
            
        descricao = str(descricao).upper()
        
        # Padrões de códigos UN/US
        patterns = [
            r'UN\d{2}/\d{4}-\d+',  # UN25/1234-1
            r'UN\d{2}\.\d{4}',     # UN25.1234
            r'US\d{2}/\d{4}-\d+',  # US25/0045-1
            r'US\d{2}\.\d{4}'      # US25.0034
        ]
        
        for pattern in patterns:
            match = re.search(pattern, descricao)
            if match:
                found_code = match.group()
                logger.debug(f"Código extraído: {found_code} de '{descricao[:50]}...'")
                return found_code
                
        return None
    
    def parse_banco_brasil(self, file_path: str) -> Dict:
        """
        Parser específico para arquivos do Banco do Brasil
        
        Args:
            file_path: Caminho para o arquivo Excel
            
        Returns:
            Dicionário com dados padronizados
        """
        try:
            logger.info(f"Iniciando parsing do Banco do Brasil: {file_path}")
            
            if not os.path.exists(file_path):
                raise FileNotFoundError(f"Arquivo não encontrado: {file_path}")
            
            # Lê arquivo Excel
            df = pd.read_excel(file_path)
            logger.info(f"Arquivo carregado: {len(df)} linhas, colunas: {list(df.columns)}")
            
            movimentos = []
            linhas_processadas = 0
            
            for i, row in df.iterrows():
                try:
                    # Verifica se é linha de dados (tem data válida na primeira coluna)
                    data_original = str(row.iloc[0]) if pd.notna(row.iloc[0]) else ""
                    
                    if "/" in data_original and len(data_original) <= 15:
                        # Extrai dados das colunas corretas
                        descricao = str(row.iloc[7]) if len(row) > 7 and pd.notna(row.iloc[7]) else ""
                        valor_original = str(row.iloc[8]) if len(row) > 8 and pd.notna(row.iloc[8]) else ""
                        tipo_original = str(row.iloc[9]) if len(row) > 9 and pd.notna(row.iloc[9]) else ""
                        
                        # Processa dados
                        data_padrao = self.parse_date(data_original.strip())
                        if not data_padrao:
                            continue
                            
                        valor_float, _, _ = self.parse_valor(valor_original)
                        if valor_float <= 0:
                            continue
                        
                        # Determina tipo baseado na coluna C/D
                        tipo = "CREDITO" if tipo_original.upper().strip() == "C" else "DEBITO"
                        
                        # Extrai código de referência
                        codigo_referencia = self.extract_reference_code(descricao)
                        
                        movimento = {
                            "data": data_padrao,
                            "data_original": data_original.strip(),
                            "descricao": descricao.strip(),
                            "valor": valor_float,
                            "valor_original": valor_original.strip(),
                            "tipo": tipo,
                            "codigo_referencia": codigo_referencia,
                            "linha_origem": i + 1
                        }
                        
                        movimentos.append(movimento)
                        linhas_processadas += 1
                        
                except Exception as e:
                    logger.warning(f"Erro ao processar linha {i+1}: {e}")
                    continue
            
            logger.info(f"Banco do Brasil processado: {len(movimentos)} movimentos válidos de {linhas_processadas} linhas")
            
            return {
                "banco": "BANCO DO BRASIL",
                "conta": self._extract_conta_bb(df),
                "arquivo_origem": os.path.basename(file_path),
                "data_processamento": datetime.now().isoformat(),
                "total_movimentos": len(movimentos),
                "movimentos": movimentos
            }
            
        except Exception as e:
            logger.error(f"Erro no parsing do Banco do Brasil: {e}")
            return {"erro": f"Erro ao processar Banco do Brasil: {str(e)}"}
    
    def parse_banco_itau(self, file_path: str) -> Dict:
        """
        Parser específico para arquivos do Banco Itaú
        
        Args:
            file_path: Caminho para o arquivo TXT
            
        Returns:
            Dicionário com dados padronizados
        """
        try:
            logger.info(f"Iniciando parsing do Banco Itaú: {file_path}")
            
            if not os.path.exists(file_path):
                raise FileNotFoundError(f"Arquivo não encontrado: {file_path}")
            
            # Lê arquivo TXT com separador ;
            df = pd.read_csv(file_path, sep=';', header=None, encoding='utf-8')
            df.columns = ['data', 'descricao', 'valor']
            
            logger.info(f"Arquivo carregado: {len(df)} linhas")
            
            movimentos = []
            
            for i, row in df.iterrows():
                try:
                    data_original = str(row['data']).strip()
                    descricao = str(row['descricao']).strip()
                    valor_original = str(row['valor']).strip()
                    
                    # Processa dados
                    data_padrao = self.parse_date(data_original)
                    if not data_padrao:
                        continue
                    
                    valor_float, tipo, is_negative = self.parse_valor(valor_original, True)
                    if valor_float <= 0:
                        continue
                    
                    # Extrai código de referência
                    codigo_referencia = self.extract_reference_code(descricao)
                    
                    movimento = {
                        "data": data_padrao,
                        "data_original": data_original,
                        "descricao": descricao,
                        "valor": valor_float,
                        "valor_original": valor_original,
                        "tipo": tipo,
                        "codigo_referencia": codigo_referencia,
                        "linha_origem": i + 1
                    }
                    
                    movimentos.append(movimento)
                    
                except Exception as e:
                    logger.warning(f"Erro ao processar linha {i+1} do Itaú: {e}")
                    continue
            
            logger.info(f"Banco Itaú processado: {len(movimentos)} movimentos válidos")
            
            return {
                "banco": "BANCO ITAU",
                "conta": "988800",  # Conta principal identificada na análise
                "arquivo_origem": os.path.basename(file_path),
                "data_processamento": datetime.now().isoformat(),
                "total_movimentos": len(movimentos),
                "movimentos": movimentos
            }
            
        except Exception as e:
            logger.error(f"Erro no parsing do Banco Itaú: {e}")
            return {"erro": f"Erro ao processar Banco Itaú: {str(e)}"}
    
    def parse_banco_santander(self, file_path: str) -> Dict:
        """
        Parser específico para arquivos do Banco Santander
        
        Args:
            file_path: Caminho para o arquivo Excel
            
        Returns:
            Dicionário com dados padronizados
        """
        try:
            logger.info(f"Iniciando parsing do Banco Santander: {file_path}")
            
            if not os.path.exists(file_path):
                raise FileNotFoundError(f"Arquivo não encontrado: {file_path}")
            
            # Lê arquivo Excel
            df = pd.read_excel(file_path)
            logger.info(f"Arquivo carregado: {len(df)} linhas, colunas: {list(df.columns)}")
            
            movimentos = []
            
            for i, row in df.iterrows():
                try:
                    # Verifica se é linha de dados (tem data válida na primeira coluna)
                    data_original = str(row.iloc[0]) if pd.notna(row.iloc[0]) else ""
                    
                    if "/" in data_original and len(data_original) <= 15:
                        descricao = str(row.iloc[1]) if len(row) > 1 and pd.notna(row.iloc[1]) else ""
                        documento = str(row.iloc[2]) if len(row) > 2 and pd.notna(row.iloc[2]) else ""
                        valor_original = str(row.iloc[3]) if len(row) > 3 and pd.notna(row.iloc[3]) else ""
                        saldo = str(row.iloc[4]) if len(row) > 4 and pd.notna(row.iloc[4]) else ""
                        
                        # Processa dados
                        data_padrao = self.parse_date(data_original.strip())
                        if not data_padrao:
                            continue
                            
                        valor_float, tipo, is_negative = self.parse_valor(valor_original, True)
                        if valor_float <= 0:
                            continue
                        
                        # Extrai código de referência
                        codigo_referencia = self.extract_reference_code(descricao)
                        
                        movimento = {
                            "data": data_padrao,
                            "data_original": data_original.strip(),
                            "descricao": descricao.strip(),
                            "valor": valor_float,
                            "valor_original": valor_original.strip(),
                            "tipo": tipo,
                            "codigo_referencia": codigo_referencia,
                            "documento": documento.strip() if documento != "nan" else None,
                            "saldo": saldo.strip() if saldo != "nan" else None,
                            "linha_origem": i + 1
                        }
                        
                        movimentos.append(movimento)
                        
                except Exception as e:
                    logger.warning(f"Erro ao processar linha {i+1} do Santander: {e}")
                    continue
            
            logger.info(f"Banco Santander processado: {len(movimentos)} movimentos válidos")
            
            return {
                "banco": "BANCO SANTANDER",
                "conta": "13006244",  # Conta identificada na análise
                "arquivo_origem": os.path.basename(file_path),
                "data_processamento": datetime.now().isoformat(),
                "total_movimentos": len(movimentos),
                "movimentos": movimentos
            }
            
        except Exception as e:
            logger.error(f"Erro no parsing do Banco Santander: {e}")
            return {"erro": f"Erro ao processar Banco Santander: {str(e)}"}
    
    def _extract_conta_bb(self, df: pd.DataFrame) -> str:
        """Extrai número da conta do DataFrame do Banco do Brasil"""
        try:
            # Procura por número de conta nas primeiras linhas
            for i in range(min(10, len(df))):
                row = df.iloc[i]
                for col in row:
                    if pd.notna(col) and str(col).isdigit() and len(str(col)) >= 6:
                        return str(col)
            return "38436-4"  # Conta padrão identificada na análise
        except:
            return "38436-4"
    
    def parse_file(self, file_path: str, bank_type: str = None) -> Dict:
        """
        Método principal para parsing de arquivos baseado no tipo de banco
        
        Args:
            file_path: Caminho para o arquivo
            bank_type: Tipo do banco (BANCO_DO_BRASIL, BANCO_ITAU, BANCO_SANTANDER) ou None para auto-detectar
            
        Returns:
            Dicionário com dados padronizados
        """
        # Detectar formato do arquivo
        file_ext = os.path.splitext(file_path)[1].lower().replace('.', '')
        
        if file_ext == 'ofx':
            return self.parse_ofx_file(file_path)
        
        # Para formatos legados (xlsx, txt, csv)
        if bank_type and bank_type not in self.supported_banks:
            return {"erro": f"Banco não suportado: {bank_type}"}
        
        if bank_type == "BANCO_DO_BRASIL":
            return self.parse_banco_brasil(file_path)
        elif bank_type == "BANCO_ITAU":
            return self.parse_banco_itau(file_path)
        elif bank_type == "BANCO_SANTANDER":
            return self.parse_banco_santander(file_path)
        else:
            return {"erro": "Tipo de banco não especificado para arquivo não-OFX"}
    
    # ==========================================
    # MÉTODOS OFX (NOVO FORMATO PADRÃO)
    # ==========================================
    
    def parse_ofx_file(self, file_path: str) -> Dict:
        """
        Parser principal para arquivos OFX dos 3 bancos
        """
        logger.info(f"Iniciando parsing OFX: {file_path}")
        
        if not os.path.exists(file_path):
            return {"erro": f"Arquivo não encontrado: {file_path}"}
        
        # Detecta banco
        banco = self._detect_bank_from_ofx(file_path)
        logger.info(f"Banco detectado: {banco}")
        
        try:
            # Lê arquivo OFX e processa transações
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            
            # Extrai conta bancária
            account_info = self._extract_account_info_ofx(content)
            
            # Extrai todas as transações STMTTRN
            transactions = []
            
            # Regex para capturar blocos STMTTRN completos
            stmttrn_pattern = r'<STMTTRN>(.*?)</STMTTRN>'
            matches = re.findall(stmttrn_pattern, content, re.DOTALL | re.IGNORECASE)
            
            logger.info(f"Encontradas {len(matches)} transações")
            
            for i, match in enumerate(matches):
                try:
                    # Extrai campos individuais
                    trntype = self._extract_field_ofx(match, 'TRNTYPE')
                    dtposted = self._extract_field_ofx(match, 'DTPOSTED') 
                    trnamt = self._extract_field_ofx(match, 'TRNAMT')
                    memo = self._extract_field_ofx(match, 'MEMO')
                    fitid = self._extract_field_ofx(match, 'FITID')
                    
                    # Processa dados
                    data_padrao = self._parse_ofx_date(dtposted)
                    if not data_padrao:
                        continue
                        
                    valor, tipo = self._parse_ofx_amount(trnamt, trntype, banco)
                    if valor <= 0:
                        continue
                    
                    # Extrai referência UN
                    ref_un = self._extract_un_reference_ofx(memo)
                    
                    transaction = {
                        "data": data_padrao,
                        "data_original": dtposted,
                        "descricao": memo.strip() if memo else "",
                        "valor": valor,
                        "valor_original": trnamt,
                        "tipo": tipo,
                        "trntype_original": trntype,
                        "codigo_referencia": ref_un,  # Mantém compatibilidade
                        "ref_unique": ref_un,  # Novo campo
                        "fitid": fitid,
                        "linha_origem": i + 1
                    }
                    
                    transactions.append(transaction)
                    
                except Exception as e:
                    logger.warning(f"Erro ao processar transação OFX {i+1}: {e}")
                    continue
            
            logger.info(f"OFX processado: {len(transactions)} transações válidas")
            
            banco_names = {
                'BB': 'BANCO DO BRASIL',
                'SANTANDER': 'BANCO SANTANDER', 
                'ITAU': 'BANCO ITAU'
            }
            
            return {
                "banco": banco_names.get(banco, banco),
                "codigo_banco": banco,
                "conta": account_info.get('conta', 'N/A'),
                "agencia": account_info.get('agencia', 'N/A'),
                "arquivo_origem": os.path.basename(file_path),
                "data_processamento": datetime.now().isoformat(),
                "total_movimentos": len(transactions),
                "movimentos": transactions
            }
            
        except Exception as e:
            logger.error(f"Erro no parsing OFX: {e}")
            return {"erro": f"Erro ao processar OFX: {str(e)}"}
    
    def _detect_bank_from_ofx(self, file_path: str) -> str:
        """Detecta banco pelo conteúdo do arquivo OFX"""
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read().upper()
            
            if 'BANCO DO BRASIL' in content or '<ORG>001' in content:
                return 'BB'
            elif 'SANTANDER' in content:
                return 'SANTANDER' 
            elif 'ITAU' in content or '<BANKID>0341' in content:
                return 'ITAU'
                
        except Exception as e:
            logger.error(f"Erro ao detectar banco OFX: {e}")
            
        return 'DESCONHECIDO'
    
    def _extract_account_info_ofx(self, content: str) -> Dict:
        """Extrai informações de conta do OFX"""
        info = {'conta': 'N/A', 'agencia': 'N/A'}
        
        try:
            # Extrai BANKID e ACCTID
            bankid_match = re.search(r'<BANKID>([^<]+)', content, re.IGNORECASE)
            acctid_match = re.search(r'<ACCTID>([^<]+)', content, re.IGNORECASE)
            
            if bankid_match:
                info['agencia'] = bankid_match.group(1).strip()
            if acctid_match:
                info['conta'] = acctid_match.group(1).strip()
                
        except Exception as e:
            logger.warning(f"Erro ao extrair info da conta OFX: {e}")
            
        return info
    
    def _extract_field_ofx(self, transaction_block: str, field_name: str) -> Optional[str]:
        """Extrai campo específico do bloco de transação OFX"""
        pattern = f'<{field_name}>(.*?)(?:\n|<)'
        match = re.search(pattern, transaction_block, re.IGNORECASE | re.DOTALL)
        return match.group(1).strip() if match else None
    
    def _parse_ofx_date(self, date_str: str) -> Optional[str]:
        """
        Converte data OFX para formato padronizado YYYY-MM-DD
        
        Formatos suportados:
        - BB: 20250910
        - Santander: 20250910000000[-3:GMT] 
        - Itaú: 20250910100000[-03:EST]
        """
        if not date_str:
            return None
            
        try:
            # Remove timezone e outros sufixos, fica apenas YYYYMMDD
            clean_date = re.sub(r'(\d{8}).*', r'\1', date_str)
            
            if len(clean_date) == 8:
                year = clean_date[:4]
                month = clean_date[4:6]  
                day = clean_date[6:8]
                return f"{year}-{month}-{day}"
                
        except Exception as e:
            logger.warning(f"Erro ao processar data OFX '{date_str}': {e}")
            
        return None
    
    def _parse_ofx_amount(self, amount_str: str, trntype: str, banco: str) -> tuple:
        """
        Processa valor OFX e determina tipo CREDITO/DEBITO baseado no banco
        
        Returns: (valor_absoluto, tipo_operacao)
        """
        if not amount_str:
            return 0.0, "CREDITO"
            
        try:
            # Remove espaços e converte vírgula para ponto
            clean_amount = str(amount_str).strip().replace(',', '.')
            
            # Detecta se é negativo
            is_negative = clean_amount.startswith('-')
            
            # Obtém valor absoluto
            valor_absoluto = abs(float(clean_amount))
            
            # Determina tipo baseado no banco e TRNTYPE
            if banco == 'BB':
                if trntype in ['DEP', 'CREDIT', 'XFER'] and not is_negative:
                    return valor_absoluto, "CREDITO"
                else:
                    return valor_absoluto, "DEBITO"
                    
            elif banco == 'SANTANDER':
                if trntype == 'CREDIT':
                    return valor_absoluto, "CREDITO"
                else:
                    return valor_absoluto, "DEBITO"
                    
            elif banco == 'ITAU':
                return valor_absoluto, "CREDITO" if trntype == 'CREDIT' else "DEBITO"
            
            # Fallback
            return valor_absoluto, "CREDITO" if not is_negative else "DEBITO"
            
        except Exception as e:
            logger.warning(f"Erro ao processar valor OFX '{amount_str}': {e}")
            return 0.0, "CREDITO"
    
    def _extract_un_reference_ofx(self, memo: str) -> Optional[str]:
        """
        Extrai referência UN da descrição conforme padrão especificado:
        UN[0-9]{2}[./]?[0-9]{4,5} -> UN25xxxx
        """
        if not memo:
            return None
            
        memo_upper = str(memo).upper()
        
        # Padrões UN conforme especificação 
        patterns = [
            r'UN\s*\d{2}[./]\d{4,5}',    # UN25/7093, UN25.7020
            r'UN\s*\d{2}\s+\d{4,5}',     # UN 25 7093  
            r'UN\s*\d{6,7}',             # UN257093
        ]
        
        for pattern in patterns:
            match = re.search(pattern, memo_upper)
            if match:
                found = match.group()
                # Extrai apenas os números
                numbers = re.findall(r'\d+', found)
                if len(numbers) >= 2:
                    # UN + primeiros 2 dígitos + últimos 4-5 dígitos
                    return f"UN{''.join(numbers)}"
                elif len(numbers) == 1 and len(numbers[0]) >= 6:
                    # UN seguido de 6+ dígitos diretos
                    return f"UN{numbers[0]}"
        
        return None
        
        return {"erro": f"Parser não implementado para {bank_type}"}