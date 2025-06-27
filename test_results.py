#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
sys.path.append('.')
from routes.conferencia import generate_sample_result

# Teste com diferentes arquivos
arquivos = ['invoice1.pdf', 'invoice2.pdf', 'invoice3.pdf', 'documento_especial.pdf']
tipos = ['invoice', 'inconsistencias']

for tipo in tipos:
    print(f'\n=== TESTE {tipo.upper()} ===')
    for arquivo in arquivos:
        print(f'\nArquivo: {arquivo}')
        resultado = generate_sample_result(tipo, arquivo)
        sumario = resultado['sumario']
        print(f'Status: {sumario["status"]}')
        print(f'Erros: {sumario["total_erros_criticos"]}')
        print(f'Observações: {sumario["total_observacoes"]}')
        print(f'Alertas: {sumario["total_alertas"]}')
        print(f'Conclusão: {sumario["conclusao"]}')
        if tipo == 'invoice' and 'itens_da_fatura' in resultado:
            item = resultado['itens_da_fatura'][0]
            print(f'Produto: {item["descricao_completa"]["valor_extraido"]}')
