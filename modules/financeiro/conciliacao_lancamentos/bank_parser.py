#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Serviço de Parsing de Arquivos Bancários
Módulo responsável por processar arquivos dos bancos e padronizar em formato JSON
Author: Sistema UniqueAduaneira
Data: 24/09/2025
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
    
    def parse_file(self, file_path: str, bank_type: str) -> Dict:
        """
        Método principal para parsing de arquivos baseado no tipo de banco
        
        Args:
            file_path: Caminho para o arquivo
            bank_type: Tipo do banco (BANCO_DO_BRASIL, BANCO_ITAU, BANCO_SANTANDER)
            
        Returns:
            Dicionário com dados padronizados
        """
        if bank_type not in self.supported_banks:
            return {"erro": f"Banco não suportado: {bank_type}"}
        
        if bank_type == "BANCO_DO_BRASIL":
            return self.parse_banco_brasil(file_path)
        elif bank_type == "BANCO_ITAU":
            return self.parse_banco_itau(file_path)
        elif bank_type == "BANCO_SANTANDER":
            return self.parse_banco_santander(file_path)
        
        return {"erro": f"Parser não implementado para {bank_type}"}