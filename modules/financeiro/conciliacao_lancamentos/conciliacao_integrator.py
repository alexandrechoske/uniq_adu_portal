#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Serviço Integrador de Conciliação Bancária
Conecta parsers, conciliação e banco de dados
Author: Sistema UniqueAduaneira
Data: 24/09/2025
"""

import os
import json
import logging
from typing import Dict, List, Optional
from datetime import datetime

from .bank_parser import BankFileParser
from .conciliacao_service import ConciliacaoService, MovimentoSistema, MovimentoBanco, ResultadoConciliacao

# Configuração de logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ConciliacaoIntegrator:
    """Classe principal que integra parsing, conciliação e banco de dados"""
    
    def __init__(self, supabase_client=None):
        self.parser = BankFileParser()
        self.conciliacao_service = ConciliacaoService()
        self.supabase = supabase_client
        
    def load_movimentos_sistema(self, data_inicio: str = None, data_fim: str = None, 
                               banco: str = None) -> List[MovimentoSistema]:
        """
        Carrega movimentos do sistema da tabela fin_conciliacao_movimentos
        
        Args:
            data_inicio: Data inicial (YYYY-MM-DD)
            data_fim: Data final (YYYY-MM-DD)
            banco: Nome do banco para filtrar
            
        Returns:
            Lista de MovimentoSistema
        """
        try:
            if not self.supabase:
                logger.warning("Cliente Supabase não disponível, usando dados mock")
                return self._load_mock_sistema_data()
            
            # Constrói query
            query = self.supabase.table('fin_conciliacao_movimentos').select('*')
            
            if data_inicio:
                query = query.gte('data_lancamento', data_inicio)
            if data_fim:
                query = query.lte('data_lancamento', data_fim)
            if banco:
                query = query.eq('nome_banco', banco.upper())
            
            # Filtra apenas pendentes
            query = query.eq('status', 'PENDENTE')
            
            response = query.execute()
            
            if not response.data:
                logger.info("Nenhum movimento pendente encontrado no sistema")
                return []
            
            # Converte para objetos MovimentoSistema
            movimentos = []
            for row in response.data:
                movimento = MovimentoSistema(
                    id=str(row['id']),
                    data_lancamento=row['data_lancamento'],
                    nome_banco=row['nome_banco'],
                    numero_conta=row['numero_conta'] or '',
                    tipo_lancamento=row['tipo_lancamento'],
                    valor=float(row['valor']),
                    descricao=row['descricao'] or '',
                    ref_unique=row['ref_unique'],
                    status=row['status']
                )
                movimentos.append(movimento)
            
            logger.info(f"Carregados {len(movimentos)} movimentos do sistema")
            return movimentos
            
        except Exception as e:
            logger.error(f"Erro ao carregar movimentos do sistema: {e}")
            return []
    
    def _load_mock_sistema_data(self) -> List[MovimentoSistema]:
        """Dados mock para testes quando não há conexão com BD"""
        return [
            MovimentoSistema(
                id="24024",
                data_lancamento="2025-09-11",  # Ajustado para data dos extratos
                nome_banco="ITAU",
                numero_conta="988800",
                tipo_lancamento="DESPESA",
                valor=533.41,
                descricao="SISPAG UN25.7020",
                ref_unique="UN25.7020"
            ),
            MovimentoSistema(
                id="24025",
                data_lancamento="2025-09-11",
                nome_banco="ITAU", 
                numero_conta="988800",
                tipo_lancamento="DESPESA",
                valor=260.00,
                descricao="PIX ENVIADO UN25.6917",
                ref_unique="UN25.6917"
            ),
            MovimentoSistema(
                id="24026",
                data_lancamento="2025-09-01",
                nome_banco="BANCO DO BRASIL",
                numero_conta="38436-4",
                tipo_lancamento="RECEITA",
                valor=2300.00,
                descricao="TED-Crédito em Conta",
                ref_unique=None
            )
        ]
    
    def processar_arquivos_bancarios(self, arquivos_info: List[Dict]) -> Dict:
        """
        Processa múltiplos arquivos bancários
        
        Args:
            arquivos_info: Lista com [{'path': '', 'bank_type': ''}, ...]
            
        Returns:
            Dicionário com resultados do processamento
        """
        resultados_parsing = {}
        movimentos_banco_todos = []
        
        for info in arquivos_info:
            file_path = info['path']
            bank_type = info['bank_type']
            
            logger.info(f"Processando arquivo {bank_type}: {file_path}")
            
            # Parse do arquivo
            resultado_parse = self.parser.parse_file(file_path, bank_type)
            
            if 'erro' in resultado_parse:
                logger.error(f"Erro no parsing {bank_type}: {resultado_parse['erro']}")
                resultados_parsing[bank_type] = resultado_parse
                continue
            
            # Converte para objetos MovimentoBanco
            movimentos_banco = []
            for mov_data in resultado_parse['movimentos']:
                movimento = MovimentoBanco(
                    data=mov_data['data'],
                    data_original=mov_data['data_original'],
                    descricao=mov_data['descricao'],
                    valor=mov_data['valor'],
                    valor_original=mov_data['valor_original'],
                    tipo=mov_data['tipo'],
                    codigo_referencia=mov_data.get('codigo_referencia'),
                    linha_origem=mov_data['linha_origem'],
                    banco=resultado_parse['banco'],
                    conta=resultado_parse['conta']
                )
                movimentos_banco.append(movimento)
            
            movimentos_banco_todos.extend(movimentos_banco)
            resultados_parsing[bank_type] = resultado_parse
            
            logger.info(f"{bank_type} processado: {len(movimentos_banco)} movimentos")
        
        return {
            'parsing_results': resultados_parsing,
            'movimentos_banco': movimentos_banco_todos,
            'total_movimentos_banco': len(movimentos_banco_todos)
        }
    
    def executar_conciliacao_completa(self, arquivos_info: List[Dict], 
                                    data_inicio: str = None, data_fim: str = None) -> Dict:
        """
        Executa processo completo de conciliação
        
        Args:
            arquivos_info: Lista com informações dos arquivos bancários
            data_inicio: Data inicial para filtro (YYYY-MM-DD)
            data_fim: Data final para filtro (YYYY-MM-DD)
            
        Returns:
            Dicionário com resultados completos da conciliação
        """
        logger.info("Iniciando processo completo de conciliação")
        
        resultado_final = {
            'timestamp': datetime.now().isoformat(),
            'status': 'SUCESSO',
            'etapas': {}
        }
        
        try:
            # Etapa 1: Carrega movimentos do sistema
            logger.info("Etapa 1: Carregando movimentos do sistema")
            movimentos_sistema = self.load_movimentos_sistema(data_inicio, data_fim)
            
            if not movimentos_sistema:
                return {
                    'status': 'ERRO',
                    'erro': 'Nenhum movimento pendente encontrado no sistema',
                    'timestamp': datetime.now().isoformat()
                }
            
            resultado_final['etapas']['sistema'] = {
                'total_movimentos': len(movimentos_sistema),
                'valor_total': sum(m.valor for m in movimentos_sistema)
            }
            
            # Etapa 2: Processa arquivos bancários
            logger.info("Etapa 2: Processando arquivos bancários")
            resultado_parsing = self.processar_arquivos_bancarios(arquivos_info)
            
            if not resultado_parsing['movimentos_banco']:
                return {
                    'status': 'ERRO', 
                    'erro': 'Nenhum movimento válido encontrado nos arquivos bancários',
                    'parsing_details': resultado_parsing['parsing_results'],
                    'timestamp': datetime.now().isoformat()
                }
            
            resultado_final['etapas']['parsing'] = {
                'total_movimentos_banco': resultado_parsing['total_movimentos_banco'],
                'detalhes_por_banco': {
                    bank: {'total': data.get('total_movimentos', 0), 'erro': data.get('erro')} 
                    for bank, data in resultado_parsing['parsing_results'].items()
                }
            }
            
            # Etapa 3: Executa conciliação
            logger.info("Etapa 3: Executando conciliação")
            resultados_conciliacao = self.conciliacao_service.conciliar_movimentos(
                movimentos_sistema, resultado_parsing['movimentos_banco']
            )
            
            # Etapa 4: Gera relatório
            relatorio = self.conciliacao_service.gerar_relatorio_conciliacao(resultados_conciliacao)
            
            resultado_final['etapas']['conciliacao'] = {
                'total_processados': len(resultados_conciliacao),
                'relatorio': relatorio
            }
            
            # Etapa 5: Salva resultados (opcional)
            if self.supabase:
                self._salvar_resultados_conciliacao(resultados_conciliacao)
            
            resultado_final['resultados_detalhados'] = self._preparar_resultados_detalhados(resultados_conciliacao)
            
            return resultado_final
            
        except Exception as e:
            logger.error(f"Erro no processo de conciliação: {e}")
            return {
                'status': 'ERRO',
                'erro': str(e),
                'timestamp': datetime.now().isoformat()
            }
    
    def _preparar_resultados_detalhados(self, resultados: List[ResultadoConciliacao]) -> Dict:
        """Prepara resultados detalhados para exibição"""
        
        conciliados = []
        parciais = []
        nao_conciliados = []
        
        for resultado in resultados:
            item_base = {
                'id_sistema': resultado.movimento_sistema.id,
                'data_sistema': resultado.movimento_sistema.data_lancamento,
                'valor_sistema': resultado.movimento_sistema.valor,
                'descricao_sistema': resultado.movimento_sistema.descricao,
                'banco': resultado.movimento_sistema.nome_banco,
                'ref_unique': resultado.movimento_sistema.ref_unique,
                'score': resultado.score_match,
                'criterios': resultado.criterios_atendidos,
                'observacoes': resultado.observacoes
            }
            
            if resultado.movimento_banco:
                item_base.update({
                    'data_banco': resultado.movimento_banco.data,
                    'valor_banco': resultado.movimento_banco.valor,
                    'descricao_banco': resultado.movimento_banco.descricao,
                    'codigo_banco': resultado.movimento_banco.codigo_referencia,
                    'linha_origem': resultado.movimento_banco.linha_origem
                })
            
            if resultado.status == "CONCILIADO":
                conciliados.append(item_base)
            elif resultado.status == "PARCIAL":
                parciais.append(item_base)
            else:
                nao_conciliados.append(item_base)
        
        return {
            'conciliados': conciliados,
            'parciais': parciais,
            'nao_conciliados': nao_conciliados
        }
    
    def _salvar_resultados_conciliacao(self, resultados: List[ResultadoConciliacao]):
        """Salva resultados da conciliação no banco de dados"""
        try:
            if not self.supabase:
                return
            
            for resultado in resultados:
                if resultado.status == "CONCILIADO":
                    # Atualiza status no sistema
                    update_data = {
                        'status': 'CONCILIADO',
                        'data_conciliacao': datetime.now().isoformat(),
                        # Pode adicionar ID do usuário que executou a conciliação
                    }
                    
                    self.supabase.table('fin_conciliacao_movimentos')\
                        .update(update_data)\
                        .eq('id', resultado.movimento_sistema.id)\
                        .execute()
            
            logger.info("Resultados salvos no banco de dados")
            
        except Exception as e:
            logger.error(f"Erro ao salvar resultados: {e}")
    
    def testar_com_arquivos_exemplo(self) -> Dict:
        """Executa teste com os arquivos de exemplo disponíveis"""
        
        base_path = os.path.dirname(os.path.abspath(__file__))
        
        arquivos_exemplo = [
            {
                'path': os.path.join(base_path, 'Banco do Brasil.xlsx'),
                'bank_type': 'BANCO_DO_BRASIL'
            },
            {
                'path': os.path.join(base_path, 'Banco Itau.txt'),
                'bank_type': 'BANCO_ITAU'
            },
            {
                'path': os.path.join(base_path, 'Banco Santander.xlsx'),
                'bank_type': 'BANCO_SANTANDER'
            }
        ]
        
        # Filtra apenas arquivos que existem
        arquivos_validos = [info for info in arquivos_exemplo if os.path.exists(info['path'])]
        
        if not arquivos_validos:
            return {
                'status': 'ERRO',
                'erro': 'Nenhum arquivo de exemplo encontrado',
                'arquivos_procurados': [info['path'] for info in arquivos_exemplo]
            }
        
        logger.info(f"Executando teste com {len(arquivos_validos)} arquivos")
        
        return self.executar_conciliacao_completa(arquivos_validos)
    
    def exportar_resultados_json(self, resultados: Dict, output_path: str = None) -> str:
        """Exporta resultados para arquivo JSON"""
        
        if not output_path:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            output_path = f"conciliacao_resultados_{timestamp}.json"
        
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(resultados, f, indent=2, ensure_ascii=False, default=str)
            
            logger.info(f"Resultados exportados para: {output_path}")
            return output_path
            
        except Exception as e:
            logger.error(f"Erro ao exportar resultados: {e}")
            return None