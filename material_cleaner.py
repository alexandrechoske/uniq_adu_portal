#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Utilitário para limpeza e tratamento de dados de materiais/mercadorias
Limpa e normaliza os dados da coluna 'mercadoria' do banco de dados
"""

import re
import json
from typing import Optional, List, Dict


class MaterialCleaner:
    """Classe para limpeza e normalização de dados de materiais"""
    
    def __init__(self):
        # Padrões regex para identificar e extrair informações relevantes
        self.patterns = {
            # NFE/NF patterns - captura números de notas fiscais
            'nfe_pattern': r'NFE?\d*\s*:?\s*([0-9,/\-\s|]+)',
            'nfe_multi_pattern': r'NFE\d*:\s*([0-9]+)',
            
            # Fornecedor patterns - para extrair nome do fornecedor principal
            'fornecedor_pattern': r'Fornecedor:\s*([^-]+?)(?:\s*-\s*Cod|$)',
            
            # PO patterns - Purchase Orders
            'po_pattern': r'PO\s+([A-Z0-9\+\-\.]+)',
            
            # Código patterns - códigos diversos
            'codigo_pattern': r"AC'S\s+([0-9]+)",
            
            # Padrões de lixo para remover
            'remove_patterns': [
                r'Nº Proc\.:\s*[0-9/]+',  # Número do processo
                r'DI:\s*[0-9/\-]+',       # Declaração de importação
                r'Cod\.?\s*Fornecedor:?\s*[0-9]+',  # Código do fornecedor
                r'COD\s+FORNECEDOR:?\s*[0-9]+',     # Código fornecedor alternativo
                r'Cód\.?\s*Fornecedor:?\s*[0-9]+',  # Código fornecedor com acento
                r'\r\n\r\n',              # Quebras de linha duplas
                r'\r\n',                  # Quebras de linha
                r'Segue comprovante.*?:',  # Textos administrativos
                r'OBS:.*',                # Observações
                r'FORNECEDOR:',           # Label fornecedor
                r'Fornecedor:',           # Label fornecedor
                r'\s*-\s*$',              # Traços no final
                r'^\s*-\s*',              # Traços no início
            ]
        }
    
    def extract_supplier(self, text: str) -> Optional[str]:
        """Extrai o nome do fornecedor principal do texto"""
        match = re.search(self.patterns['fornecedor_pattern'], text, re.IGNORECASE)
        if match:
            supplier = match.group(1).strip()
            # Limpar caracteres extras
            supplier = re.sub(r'\s+', ' ', supplier)
            return supplier
        return None
    
    def extract_nfe_numbers(self, text: str) -> List[str]:
        """Extrai números de NFE/NF do texto"""
        numbers = []
        
        # Primeira tentativa: padrão múltiplo NFE1:, NFE2:, etc
        multi_matches = re.findall(self.patterns['nfe_multi_pattern'], text, re.IGNORECASE)
        if multi_matches:
            numbers.extend(multi_matches)
        
        # Segunda tentativa: padrão geral
        match = re.search(self.patterns['nfe_pattern'], text, re.IGNORECASE)
        if match:
            nfe_text = match.group(1)
            # Separar por vírgulas, barras ou espaços
            parsed_numbers = re.split(r'[,/|\s]+', nfe_text)
            # Filtrar apenas números válidos
            for n in parsed_numbers:
                clean_n = n.strip()
                if clean_n and clean_n.isdigit():
                    numbers.append(clean_n)
        
        # Remover duplicatas e retornar
        return list(dict.fromkeys(numbers))
    
    def extract_po_number(self, text: str) -> Optional[str]:
        """Extrai número de PO (Purchase Order)"""
        match = re.search(self.patterns['po_pattern'], text, re.IGNORECASE)
        if match:
            return match.group(1).strip()
        return None
    
    def extract_ac_codes(self, text: str) -> List[str]:
        """Extrai códigos AC's"""
        matches = re.findall(self.patterns['codigo_pattern'], text)
        return [f"AC {code}" for code in matches]
    
    def remove_junk(self, text: str) -> str:
        """Remove padrões de lixo do texto"""
        cleaned = text
        
        for pattern in self.patterns['remove_patterns']:
            cleaned = re.sub(pattern, '', cleaned, flags=re.IGNORECASE)
        
        # Limpeza final
        cleaned = re.sub(r'\s+', ' ', cleaned)  # Múltiplos espaços
        cleaned = cleaned.strip()
        
        return cleaned
    
    def clean_material(self, raw_material: str) -> Dict[str, any]:
        """
        Função principal para limpeza de material
        
        Args:
            raw_material: Texto bruto da coluna mercadoria
            
        Returns:
            Dict com informações limpas e estruturadas
        """
        if not raw_material:
            return {
                'material_limpo': '',
                'fornecedor_principal': None,
                'numeros_nfe': [],
                'po_number': None,
                'codigos_ac': [],
                'texto_original': raw_material
            }
        
        # Extrair informações estruturadas
        supplier = self.extract_supplier(raw_material)
        nfe_numbers = self.extract_nfe_numbers(raw_material)
        po_number = self.extract_po_number(raw_material)
        ac_codes = self.extract_ac_codes(raw_material)
        
        # Limpar o texto
        cleaned_text = self.remove_junk(raw_material)
        
        # Construir material limpo baseado nas informações extraídas
        material_parts = []
        
        # Priorizar PO se existir
        if po_number:
            material_parts.append(f"PO {po_number}")
        
        # Adicionar NFEs se existirem
        if nfe_numbers:
            if len(nfe_numbers) == 1:
                material_parts.append(f"NFE {nfe_numbers[0]}")
            else:
                material_parts.append(f"NFE {', '.join(nfe_numbers)}")
        
        # Adicionar códigos AC se existirem
        if ac_codes:
            material_parts.extend(ac_codes)
        
        # Adicionar fornecedor se relevante
        if supplier and len(material_parts) > 0:
            material_parts.append(f"({supplier})")
        
        # Se não conseguiu extrair nada útil, usar texto limpo
        if not material_parts:
            material_limpo = cleaned_text[:100] + "..." if len(cleaned_text) > 100 else cleaned_text
        else:
            material_limpo = " - ".join(material_parts)
        
        return {
            'material_limpo': material_limpo,
            'fornecedor_principal': supplier,
            'numeros_nfe': nfe_numbers,
            'po_number': po_number,
            'codigos_ac': ac_codes,
            'texto_original': raw_material
        }


def test_cleaner_with_samples():
    """Função de teste com dados reais"""
    cleaner = MaterialCleaner()
    
    # Carregar algumas amostras do arquivo JSON
    try:
        with open('coluna_mercadorias.json', 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        print("=== TESTE DE LIMPEZA DE MATERIAIS ===\n")
        
        # Testar com as primeiras 10 amostras
        for i, item in enumerate(data[:10]):
            raw = item['mercadoria']
            result = cleaner.clean_material(raw)
            
            print(f"--- Amostra {i+1} ---")
            print(f"Original: {raw[:100]}...")
            print(f"Limpo: {result['material_limpo']}")
            print(f"Fornecedor: {result['fornecedor_principal']}")
            print(f"NFEs: {result['numeros_nfe']}")
            print(f"PO: {result['po_number']}")
            print(f"ACs: {result['codigos_ac']}")
            print()
            
    except FileNotFoundError:
        print("Arquivo coluna_mercadorias.json não encontrado")
        print("Executando teste com dados de exemplo...")
        
        # Dados de exemplo para teste
        samples = [
            "NFE: 199329 - Fornecedor: GARDNER DENVER OY - Cod. Fornecedor: 4252\r\nNº Proc.: 0127/20\r\nDI: 20/0829584-1",
            "PO 1607+1630.SUN.22",
            "AC'S 20220052824\r\nAC'S 20220053006",
            "OBS: Habilitação do Radar da paciente : ANA CAROLINA DE CAMPOS VIEIRA FORMAGGI CPF 16020021858"
        ]
        
        for i, sample in enumerate(samples):
            result = cleaner.clean_material(sample)
            print(f"--- Exemplo {i+1} ---")
            print(f"Original: {sample}")
            print(f"Limpo: {result['material_limpo']}")
            print()


if __name__ == "__main__":
    test_cleaner_with_samples()
