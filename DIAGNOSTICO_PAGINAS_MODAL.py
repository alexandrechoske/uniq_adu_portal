#!/usr/bin/env python3
"""
Script para diagnosticar e corrigir o carregamento de páginas no modal de perfis
Problema: JavaScript está usando MODULOS_SISTEMA hardcoded, não busca da API
"""

import json

DIAGNOSTIC = """
╔══════════════════════════════════════════════════════════════════════════╗
║          DIAGNÓSTICO - PROBLEMA NO CARREGAMENTO DE PÁGINAS               ║
╚══════════════════════════════════════════════════════════════════════════╝

❌ PROBLEMA IDENTIFICADO:
   
   Arquivo: modules/usuarios/static/js/perfis.js (linhas 45-66)
   
   O JavaScript possui MODULOS_SISTEMA hardcoded com APENAS 4 páginas de fin:
   ✓ fin_dashboard_executivo
   ✓ fluxo_caixa
   ✓ despesas
   ✓ faturamento
   
   ❌ FALTAM:
   ✗ conciliacao
   ✗ categorizacao
   ✗ projecoes
   ✗ export_bases

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

✅ SOLUÇÃO:

   Opção 1 (RÁPIDA - 2 min): Atualizar hardcoded no JS
   └─ Editar: modules/usuarios/static/js/perfis.js (linhas 45-66)
   └─ Adicionar as 4 páginas faltantes

   Opção 2 (IDEAL - 5 min): Buscar dinamicamente da API
   └─ Criar endpoint: /usuarios/perfis/api/pages
   └─ Modificar JS para buscar da API ao abrir modal
   └─ Renderizar páginas dinamicamente

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

RECOMENDAÇÃO: Opção 1 (RÁPIDA) para resolver agora + Opção 2 (IDEAL) depois
"""

print(DIAGNOSTIC)

# Dados que faltam no JavaScript
MISSING_PAGES = {
    'fin': [
        {'code': 'conciliacao', 'name': 'Conciliação Bancária', 'icon': 'mdi-checkbox-marked-circle'},
        {'code': 'categorizacao', 'name': 'Categorização de Clientes', 'icon': 'mdi-tag-multiple'},
        {'code': 'projecoes', 'name': 'Projeções e Metas', 'icon': 'mdi-chart-line'},
        {'code': 'export_bases', 'name': 'Exportação de Bases', 'icon': 'mdi-database-export'}
    ],
    'imp': [
        {'code': 'materiais', 'name': 'Gestão de Materiais', 'icon': 'mdi-package'},
        {'code': 'dashboard_operacional', 'name': 'Dashboard Operacional', 'icon': 'mdi-chart-box'}
    ],
    'rh': [
        {'code': 'carreiras', 'name': 'Gestão de Carreiras', 'icon': 'mdi-timeline-text'},
        {'code': 'dashboard_analitico', 'name': 'Dashboard Analítico', 'icon': 'mdi-chart-scatter'}
    ]
}

print("\n📋 PÁGINAS FALTANDO NO JAVASCRIPT:\n")
for modulo, pages in MISSING_PAGES.items():
    print(f"   {modulo.upper()}:")
    for page in pages:
        print(f"      • {page['code']:<25} | {page['name']:<35} | {page['icon']}")

print("""

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🔧 COMO CORRIGIR (Opção 1 - Rápida):

1. Abra: modules/usuarios/static/js/perfis.js
2. Procure por: MODULOS_SISTEMA = {
3. Na seção 'fin', adicione após 'faturamento':
   
   { code: 'conciliacao', name: 'Conciliação Bancária', icon: 'mdi-checkbox-marked-circle' },
   { code: 'categorizacao', name: 'Categorização de Clientes', icon: 'mdi-tag-multiple' },
   { code: 'projecoes', name: 'Projeções e Metas', icon: 'mdi-chart-line' },
   { code: 'export_bases', name: 'Exportação de Bases', icon: 'mdi-database-export' }

4. Salve o arquivo
5. Limpe cache do navegador (Ctrl+Shift+Delete)
6. Recarregue a página (F5)
7. Abra modal "Novo Perfil"
8. Verifique se Conciliação Bancária aparece

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
""")
