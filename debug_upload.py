#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
sys.path.append('.')
from routes.conferencia import generate_sample_result
import json

def simulate_upload_scenario():
    """Simula exatamente o cenário de upload para depuração"""
    
    # Simular dados de upload
    tipo_conferencia = 'invoice'
    saved_files = [
        {
            'filename': 'fatura1.pdf',
            'path': '/path/to/fatura1.pdf',
            'status': 'pending',
            'result': None
        },
        {
            'filename': 'fatura2.pdf', 
            'path': '/path/to/fatura2.pdf',
            'status': 'pending',
            'result': None
        },
        {
            'filename': 'fatura3.pdf',
            'path': '/path/to/fatura3.pdf', 
            'status': 'pending',
            'result': None
        }
    ]
    
    print("=== SIMULAÇÃO DO CENÁRIO DE UPLOAD ===\n")
    
    # Processar exatamente como no código real
    for i, file_info in enumerate(saved_files):
        filename = file_info['filename']
        print(f"DEBUG: Processando arquivo {i+1}: {filename}")
        
        file_info['status'] = 'completed'
        file_info['result'] = generate_sample_result(tipo_conferencia, filename)
        
        # Debug: verificar se o resultado foi gerado corretamente
        if file_info['result'] and 'sumario' in file_info['result']:
            sumario = file_info['result']['sumario']
            print(f"DEBUG: Resultado gerado para {filename} - Status: {sumario['status']}, Conclusão: {sumario['conclusao']}")
            
            # Verificar dados específicos
            if 'itens_da_fatura' in file_info['result'] and file_info['result']['itens_da_fatura']:
                item = file_info['result']['itens_da_fatura'][0]
                print(f"DEBUG: Produto: {item['descricao_completa']['valor_extraido']}")
        else:
            print(f"DEBUG: ERRO - Resultado inválido para {filename}")
    
    print(f"\nDEBUG: Total de arquivos processados: {len(saved_files)}")
    
    # Verificar se os resultados estão realmente diferentes
    print("\n=== VERIFICAÇÃO DE DIFERENÇAS ===")
    for i, file_info in enumerate(saved_files):
        print(f"\nArquivo {i+1}: {file_info['filename']}")
        result = file_info['result']
        print(f"  Conclusão: {result['sumario']['conclusao']}")
        if 'itens_da_fatura' in result:
            item = result['itens_da_fatura'][0]
            print(f"  Produto: {item['descricao_completa']['valor_extraido']}")
    
    # Criar estrutura de job como seria salva
    job_data = {
        'id': 'test-job-123',
        'status': 'completed',
        'tipo_conferencia': tipo_conferencia,
        'total_arquivos': len(saved_files),
        'arquivos_processados': len(saved_files),
        'arquivos': saved_files
    }
    
    print(f"\n=== DADOS DO JOB (JSON) ===")
    print(json.dumps(job_data, indent=2, ensure_ascii=False))

if __name__ == "__main__":
    simulate_upload_scenario()
