"""
Script para atualizar materiais_v2.py para usar colunas normalizadas
"""

import re

# Ler o arquivo
with open('routes/materiais_v2.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Substituições para usar colunas normalizadas
substitutions = [
    # Atualizar referências de mercadoria para mercadoria_normalizado
    (r"row\.get\('mercadoria', ''\)", "row.get('mercadoria_normalizado', '')"),
    (r"'mercadoria' in df\.columns", "'mercadoria_normalizado' in df.columns"),
    (r"df\['mercadoria'\]", "df['mercadoria_normalizado']"),
    (r"df\['mercadoria_clean'\] = df\['mercadoria'\]", "df['mercadoria_clean'] = df['mercadoria_normalizado']"),
    
    # Atualizar filtros para usar mercadoria_normalizado
    (r"material\.lower\(\) in str\(item\.get\('mercadoria', ''\)\)\.lower\(\)", "material.lower() in str(item.get('mercadoria_normalizado', '')).lower()"),
    
    # Atualizar URF para usar colunas normalizadas
    (r"'urf_entrada' in df\.columns", "'urf_entrada_normalizado' in df.columns"),
    (r"df\['urf_entrada'\]", "df['urf_entrada_normalizado']"),
    (r"'urf_despacho' in df\.columns", "'urf_despacho_normalizado' in df.columns"),
    (r"df\['urf_despacho'\]", "df['urf_despacho_normalizado']"),
]

# Aplicar todas as substituições
for pattern, replacement in substitutions:
    content = re.sub(pattern, replacement, content)

# Salvar o arquivo atualizado
with open('routes/materiais_v2.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("✅ Arquivo materiais_v2.py atualizado com sucesso!")
print("📋 Substituições aplicadas:")
for pattern, replacement in substitutions:
    print(f"  - {pattern} → {replacement}")
