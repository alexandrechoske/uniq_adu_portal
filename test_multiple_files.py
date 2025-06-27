#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
sys.path.append('.')
from routes.conferencia import generate_sample_result
import json

def test_multiple_files():
    """Simula o upload de múltiplos arquivos e verifica se geram resultados diferentes"""
    
    # Simular dados como no upload real
    test_files = [
        {'filename': 'invoice_ABC123.pdf'},
        {'filename': 'invoice_XYZ789.pdf'},
        {'filename': 'fatura_especial.pdf'},
        {'filename': 'documento_teste.pdf'}
    ]
    
    tipo_conferencia = 'invoice'
    
    print(f"=== TESTE DE MÚLTIPLOS ARQUIVOS - {tipo_conferencia.upper()} ===\n")
    
    for i, file_info in enumerate(test_files):
        filename = file_info['filename']
        file_info['status'] = 'completed'
        file_info['result'] = generate_sample_result(tipo_conferencia, filename)
        
        result = file_info['result']
        sumario = result['sumario']
        
        print(f"Arquivo {i+1}: {filename}")
        print(f"  Status: {sumario['status']}")
        print(f"  Erros Críticos: {sumario['total_erros_criticos']}")
        print(f"  Observações: {sumario['total_observacoes']}")
        print(f"  Alertas: {sumario['total_alertas']}")
        print(f"  Conclusão: {sumario['conclusao']}")
        
        if 'itens_da_fatura' in result and result['itens_da_fatura']:
            item = result['itens_da_fatura'][0]
            print(f"  Produto: {item['descricao_completa']['valor_extraido']}")
            print(f"  Quantidade: {item['quantidade_unidade']['valor_extraido']}")
            print(f"  Preço Unit.: {item['preco_unitario']['valor_extraido']}")
            print(f"  Valor Total: {item['valor_total_item']['valor_extraido']}")
        
        print("-" * 60)
    
    # Testar tipo inconsistências também
    print(f"\n=== TESTE DE MÚLTIPLOS ARQUIVOS - INCONSISTÊNCIAS ===\n")
    
    for i, file_info in enumerate(test_files):
        filename = file_info['filename']
        result = generate_sample_result('inconsistencias', filename)
        sumario = result['sumario']
        
        print(f"Arquivo {i+1}: {filename}")
        print(f"  Status: {sumario['status']}")
        print(f"  Erros Críticos: {sumario['total_erros_criticos']}")
        print(f"  Observações: {sumario['total_observacoes']}")
        print(f"  Alertas: {sumario['total_alertas']}")
        print(f"  Conclusão: {sumario['conclusao']}")
        print("-" * 60)

if __name__ == "__main__":
    test_multiple_files()
