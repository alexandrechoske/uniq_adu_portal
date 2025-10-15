#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Serviço de Conciliação Bancária
Módulo responsável por conciliar movimentos bancários com dados do sistema
Author: Sistema UniqueAduaneira
Data: 24/09/2025
"""

import logging
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass
import re

# Configuração de logging
logger = logging.getLogger(__name__)

@dataclass
class MovimentoSistema:
    """Representa um movimento do sistema (tabela fin_conciliacao_movimentos)"""
    id: str
    data_lancamento: str
    nome_banco: str
    numero_conta: str
    tipo_lancamento: str  # RECEITA/DESPESA
    valor: float
    descricao: str
    ref_unique: Optional[str]
    status: str = "PENDENTE"

@dataclass
class MovimentoBanco:
    """Representa um movimento do extrato bancário"""
    data: str
    data_original: str
    descricao: str
    valor: float
    valor_original: str
    tipo: str  # CREDITO/DEBITO
    codigo_referencia: Optional[str]
    linha_origem: int
    banco: str
    conta: str

@dataclass
class ResultadoConciliacao:
    """Resultado da conciliação entre movimento do sistema e banco"""
    movimento_sistema: MovimentoSistema
    movimento_banco: Optional[MovimentoBanco]
    score_match: float
    criterios_atendidos: List[str]
    status: str  # CONCILIADO, NAO_CONCILIADO, PARCIAL
    observacoes: str

class ConciliacaoService:
    """Serviço principal de conciliação bancária"""
    
    def __init__(self):
        self.tolerancia_valor = 0.01  # Tolerância de R$ 0,01 para valores
        self.tolerancia_data = 0      # Tolerância de 0 dias para datas (exata)
        
    def normalize_bank_name(self, bank_name: str) -> str:
        """Normaliza nome do banco para comparação"""
        bank_name = str(bank_name).upper().strip()
        
        # Mapeamento de nomes
        bank_mapping = {
            'ITAU': 'ITAU',
            'BANCO ITAU': 'ITAU', 
            'ITAÚ': 'ITAU',
            'BANCO DO BRASIL': 'BANCO DO BRASIL',
            'BB': 'BANCO DO BRASIL',
            'BANCO BRASIL': 'BANCO DO BRASIL',
            'SANTANDER': 'SANTANDER',
            'BANCO SANTANDER': 'SANTANDER'
        }
        
        return bank_mapping.get(bank_name, bank_name)
    
    def normalize_reference_code(self, ref_code: str) -> str:
        """Normaliza código de referência para comparação"""
        if not ref_code:
            return ""
            
        ref_code = str(ref_code).upper().strip()
        
        # Padroniza separadores
        ref_code = ref_code.replace('.', '/').replace('-', '/')
        
        # Remove espaços extras
        ref_code = re.sub(r'\s+', '', ref_code)
        
        return ref_code
    
    def calculate_date_difference(self, data1: str, data2: str) -> int:
        """Calcula diferença em dias entre duas datas"""
        try:
            dt1 = datetime.strptime(data1, '%Y-%m-%d')
            dt2 = datetime.strptime(data2, '%Y-%m-%d')
            return abs((dt1 - dt2).days)
        except:
            return 999  # Diferença alta para datas inválidas
    
    def calculate_value_difference(self, valor1: float, valor2: float) -> float:
        """Calcula diferença percentual entre dois valores"""
        if valor1 == 0 and valor2 == 0:
            return 0.0
        if valor1 == 0 or valor2 == 0:
            return 100.0
            
        return abs(valor1 - valor2) / max(valor1, valor2) * 100
    
    def match_tipo_lancamento(self, tipo_sistema: str, tipo_banco: str) -> bool:
        """Verifica se os tipos de lançamento são compatíveis"""
        # Mapeamento: RECEITA/DESPESA (sistema) <-> CREDITO/DEBITO (banco)
        mapping = {
            'RECEITA': 'CREDITO',
            'DESPESA': 'DEBITO'
        }
        
        return mapping.get(tipo_sistema) == tipo_banco
    
    def find_matches(self, movimento_sistema: MovimentoSistema, 
                    movimentos_banco: List[MovimentoBanco]) -> List[Tuple[MovimentoBanco, float, List[str]]]:
        """
        Encontra possíveis matches para um movimento do sistema
        
        Returns:
            Lista de tuplas (movimento_banco, score, criterios_atendidos)
        """
        matches = []
        
        for mov_banco in movimentos_banco:
            score = 0.0
            criterios = []
            
            # Critério 1: Nome do banco (obrigatório)
            banco_sistema = self.normalize_bank_name(movimento_sistema.nome_banco)
            banco_extrato = self.normalize_bank_name(mov_banco.banco)
            
            if banco_sistema != banco_extrato:
                continue  # Pula se bancos diferentes
            
            criterios.append("banco")
            score += 20  # 20 pontos base por banco correto
            
            # Critério 2: Data (peso alto)
            diff_dias = self.calculate_date_difference(movimento_sistema.data_lancamento, mov_banco.data)
            
            if diff_dias <= self.tolerancia_data:
                criterios.append("data_exata")
                score += 30
            elif diff_dias <= 1:
                criterios.append("data_1dia")
                score += 20
            elif diff_dias <= 7:
                criterios.append("data_7dias")
                score += 10
            else:
                continue  # Pula se diferença de data muito grande
            
            # Critério 3: Valor (peso alto)
            valor_sistema_abs = abs(movimento_sistema.valor)
            valor_banco_abs = abs(mov_banco.valor)
            diff_valor_abs = abs(valor_sistema_abs - valor_banco_abs)
            diff_valor_perc = self.calculate_value_difference(valor_sistema_abs, valor_banco_abs)
            
            if diff_valor_abs <= self.tolerancia_valor:
                criterios.append("valor_exato")
                score += 30
            elif diff_valor_perc <= 1.0:  # 1% de diferença
                criterios.append("valor_1perc")
                score += 20
            elif diff_valor_perc <= 5.0:  # 5% de diferença
                criterios.append("valor_5perc")
                score += 10
            else:
                continue  # Pula se diferença de valor muito grande
            
            # Critério 4: Tipo de lançamento
            if self.match_tipo_lancamento(movimento_sistema.tipo_lancamento, mov_banco.tipo):
                criterios.append("tipo_compativel")
                score += 10
            
            # Critério 5: Código de referência (bônus se disponível)
            if movimento_sistema.ref_unique and mov_banco.codigo_referencia:
                ref_sistema = self.normalize_reference_code(movimento_sistema.ref_unique)
                ref_banco = self.normalize_reference_code(mov_banco.codigo_referencia)
                
                if ref_sistema == ref_banco:
                    criterios.append("codigo_exato")
                    score += 20
                elif ref_sistema in ref_banco or ref_banco in ref_sistema:
                    criterios.append("codigo_parcial")
                    score += 10
            
            # Critério 6: Conta bancária (bônus se bater)
            if movimento_sistema.numero_conta == mov_banco.conta:
                criterios.append("conta_correta")
                score += 5
            
            # Critério 7: Similaridade na descrição (bônus)
            if self.calculate_description_similarity(movimento_sistema.descricao, mov_banco.descricao) > 0.5:
                criterios.append("descricao_similar")
                score += 5
            
            if score >= 50:  # Score mínimo para considerar match
                matches.append((mov_banco, score, criterios))
        
        # Ordena por score decrescente
        matches.sort(key=lambda x: x[1], reverse=True)
        
        return matches
    
    def calculate_description_similarity(self, desc1: str, desc2: str) -> float:
        """Calcula similaridade entre descrições (método simples)"""
        try:
            if not desc1 or not desc2:
                return 0.0
            
            desc1 = desc1.upper().strip()
            desc2 = desc2.upper().strip()
            
            # Extrai palavras significativas (> 3 caracteres)
            words1 = set([w for w in re.split(r'\W+', desc1) if len(w) > 3])
            words2 = set([w for w in re.split(r'\W+', desc2) if len(w) > 3])
            
            if not words1 or not words2:
                return 0.0
            
            # Calcula Jaccard similarity
            intersection = len(words1.intersection(words2))
            union = len(words1.union(words2))
            
            return intersection / union if union > 0 else 0.0
            
        except:
            return 0.0
    
    def conciliar_movimentos(self, movimentos_sistema: List[MovimentoSistema], 
                           movimentos_banco: List[MovimentoBanco]) -> List[ResultadoConciliacao]:
        """
        Executa conciliação completa entre movimentos do sistema e banco
        
        Returns:
            Lista com resultados da conciliação
        """
        logger.info(f"Iniciando conciliação: {len(movimentos_sistema)} do sistema vs {len(movimentos_banco)} do banco")
        
        resultados = []
        movimentos_banco_usados = set()  # Usa índices ao invés dos objetos
        
        for mov_sistema in movimentos_sistema:
            logger.debug(f"Processando movimento sistema ID {mov_sistema.id}")
            
            # Filtra movimentos não utilizados do mesmo banco
            movimentos_disponiveis = [
                mb for i, mb in enumerate(movimentos_banco)
                if i not in movimentos_banco_usados 
                and self.normalize_bank_name(mb.banco) == self.normalize_bank_name(mov_sistema.nome_banco)
            ]
            
            # Busca matches
            matches = self.find_matches(mov_sistema, movimentos_disponiveis)
            
            if matches:
                # Pega o melhor match
                melhor_match, score, criterios = matches[0]
                
                # Encontra índice do movimento no array original
                for i, mb in enumerate(movimentos_banco):
                    if (mb.data == melhor_match.data and 
                        mb.valor == melhor_match.valor and
                        mb.descricao == melhor_match.descricao and
                        mb.linha_origem == melhor_match.linha_origem):
                        movimentos_banco_usados.add(i)
                        break
                
                # Determina status baseado no score
                if score >= 80:
                    status = "CONCILIADO"
                    observacoes = f"Match automático - Score: {score:.1f}%"
                elif score >= 60:
                    status = "PARCIAL"
                    observacoes = f"Match parcial - Score: {score:.1f}% - Revisar manualmente"
                else:
                    status = "NAO_CONCILIADO"
                    observacoes = f"Score baixo: {score:.1f}% - Verificar dados"
                
                resultado = ResultadoConciliacao(
                    movimento_sistema=mov_sistema,
                    movimento_banco=melhor_match,
                    score_match=score,
                    criterios_atendidos=criterios,
                    status=status,
                    observacoes=observacoes
                )
                
            else:
                # Nenhum match encontrado
                resultado = ResultadoConciliacao(
                    movimento_sistema=mov_sistema,
                    movimento_banco=None,
                    score_match=0.0,
                    criterios_atendidos=[],
                    status="NAO_CONCILIADO",
                    observacoes="Nenhuma correspondência encontrada no extrato bancário"
                )
            
            resultados.append(resultado)
        
        # Estatísticas finais
        conciliados = sum(1 for r in resultados if r.status == "CONCILIADO")
        parciais = sum(1 for r in resultados if r.status == "PARCIAL")
        nao_conciliados = sum(1 for r in resultados if r.status == "NAO_CONCILIADO")
        
        logger.info(f"Conciliação finalizada - Conciliados: {conciliados}, "
                   f"Parciais: {parciais}, Não conciliados: {nao_conciliados}")
        
        return resultados
    
    def gerar_relatorio_conciliacao(self, resultados: List[ResultadoConciliacao]) -> Dict:
        """Gera relatório resumido da conciliação"""
        
        total = len(resultados)
        conciliados = sum(1 for r in resultados if r.status == "CONCILIADO")
        parciais = sum(1 for r in resultados if r.status == "PARCIAL")
        nao_conciliados = sum(1 for r in resultados if r.status == "NAO_CONCILIADO")
        
        # Calcula valores
        valor_total_sistema = sum(r.movimento_sistema.valor for r in resultados)
        valor_conciliado = sum(r.movimento_sistema.valor for r in resultados if r.status == "CONCILIADO")
        
        relatorio = {
            "timestamp": datetime.now().isoformat(),
            "resumo": {
                "total_movimentos": total,
                "conciliados": conciliados,
                "parciais": parciais,
                "nao_conciliados": nao_conciliados,
                "taxa_conciliacao": (conciliados / total * 100) if total > 0 else 0,
                "taxa_sucesso": ((conciliados + parciais) / total * 100) if total > 0 else 0
            },
            "valores": {
                "valor_total_sistema": valor_total_sistema,
                "valor_conciliado": valor_conciliado,
                "percentual_valor_conciliado": (valor_conciliado / valor_total_sistema * 100) if valor_total_sistema > 0 else 0
            },
            "detalhes_por_banco": self._agrupar_por_banco(resultados),
            "criterios_mais_usados": self._analisar_criterios(resultados)
        }
        
        return relatorio
    
    def _agrupar_por_banco(self, resultados: List[ResultadoConciliacao]) -> Dict:
        """Agrupa resultados por banco"""
        bancos = {}
        
        for resultado in resultados:
            banco = self.normalize_bank_name(resultado.movimento_sistema.nome_banco)
            
            if banco not in bancos:
                bancos[banco] = {
                    "total": 0,
                    "conciliados": 0,
                    "parciais": 0,
                    "nao_conciliados": 0,
                    "valor_total": 0.0,
                    "valor_conciliado": 0.0
                }
            
            bancos[banco]["total"] += 1
            bancos[banco]["valor_total"] += resultado.movimento_sistema.valor
            
            if resultado.status == "CONCILIADO":
                bancos[banco]["conciliados"] += 1
                bancos[banco]["valor_conciliado"] += resultado.movimento_sistema.valor
            elif resultado.status == "PARCIAL":
                bancos[banco]["parciais"] += 1
            else:
                bancos[banco]["nao_conciliados"] += 1
        
        return bancos
    
    def _analisar_criterios(self, resultados: List[ResultadoConciliacao]) -> Dict:
        """Analisa quais critérios foram mais utilizados"""
        criterios_count = {}
        
        for resultado in resultados:
            for criterio in resultado.criterios_atendidos:
                criterios_count[criterio] = criterios_count.get(criterio, 0) + 1
        
        return dict(sorted(criterios_count.items(), key=lambda x: x[1], reverse=True))