"""
Script para atualizar todas as funções do materiais_v2.py 
para usar a função helper get_or_reload_cache
"""

import re

# Ler o arquivo
with open('routes/materiais_v2.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Padrão para encontrar e substituir o código de cache
pattern = r"""# Obter dados do cache
        user_data = session\.get\('user', \{\}\)
        user_id = user_data\.get\('id'\)
        
        data = data_cache\.get_cache\(user_id, 'dashboard_v2_data'\)"""

replacement = """# Obter dados do cache ou recarregar
        user_data = session.get('user', {})
        user_id = user_data.get('id')
        user_role = user_data.get('role')
        
        data = get_or_reload_cache(user_id, user_role)"""

# Aplicar substituição
new_content = re.sub(pattern, replacement, content, flags=re.MULTILINE)

# Salvar o arquivo atualizado
with open('routes/materiais_v2.py', 'w', encoding='utf-8') as f:
    f.write(new_content)

print("Arquivo materiais_v2.py atualizado com sucesso!")
print("Todas as funções agora usam get_or_reload_cache()")
