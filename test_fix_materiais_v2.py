"""
Script para corrigir todas as ocorrências de session.get('dashboard_v2_data') 
em materiais_v2.py para usar o cache
"""

import re

# Ler o arquivo original
with open('routes/materiais_v2.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Padrão para encontrar session.get('dashboard_v2_data', [])
pattern = r"data = session\.get\('dashboard_v2_data', \[\]\)"

# Replacement
replacement = """# Obter dados do cache
        user_data = session.get('user', {})
        user_id = user_data.get('id')
        
        data = data_cache.get_cache(user_id, 'dashboard_v2_data')"""

# Aplicar correção
new_content = re.sub(pattern, replacement, content)

# Salvar o arquivo corrigido
with open('routes/materiais_v2.py', 'w', encoding='utf-8') as f:
    f.write(new_content)

print("Arquivo materiais_v2.py corrigido com sucesso!")
print("Alterações aplicadas:")
print("- Todos os session.get('dashboard_v2_data') foram substituídos")
print("- Agora usa data_cache.get_cache(user_id, 'dashboard_v2_data')")
