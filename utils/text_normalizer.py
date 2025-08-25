"""
Função para normalizar strings removendo acentos e caracteres especiais
para gerar códigos seguros para perfis
"""
import unicodedata
import re

def normalize_string_for_code(text):
    """
    Normaliza uma string para ser usada como código:
    - Remove acentos
    - Converte para minúsculas
    - Remove caracteres especiais
    - Substitui espaços por underscore
    - Remove underscores duplos
    
    Args:
        text (str): Texto a ser normalizado
        
    Returns:
        str: Texto normalizado
    """
    if not text:
        return ''
    
    # Converter para string se não for
    text = str(text)
    
    # Normalizar Unicode (NFD) e remover acentos
    text = unicodedata.normalize('NFD', text)
    text = ''.join(char for char in text if unicodedata.category(char) != 'Mn')
    
    # Converter para minúsculas
    text = text.lower()
    
    # Manter apenas letras, números e espaços
    text = re.sub(r'[^a-zA-Z0-9\s]', '', text)
    
    # Substituir espaços por underscore
    text = re.sub(r'\s+', '_', text)
    
    # Remover underscores múltiplos
    text = re.sub(r'_+', '_', text)
    
    # Remover underscores do início e fim
    text = text.strip('_')
    
    return text

# Testes da função
if __name__ == "__main__":
    test_cases = [
        "Importações Completo",
        "Financeiro - Gestão",
        "Relatórios & Análises",
        "Usuários / Administração",
        "Configurações Gerais",
        "Módulo (Avançado)",
        "importacoes_completo",
        "teste@#$%especial",
        "   espaços   extras   ",
        "ÇÃO-JOÃO_123"
    ]
    
    print("TESTES DE NORMALIZAÇÃO:")
    print("=" * 50)
    
    for test in test_cases:
        normalized = normalize_string_for_code(test)
        print(f"'{test}' → '{normalized}'")
    
    print("\n✅ Função testada com sucesso!")
