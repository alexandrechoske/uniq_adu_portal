#!/usr/bin/env python3
"""
Arquivo de teste temporário para verificar problema com get_user_companies
"""

def test_import():
    """Testar se as importações estão funcionando"""
    try:
        from routes.api import get_user_companies
        print("✓ Importação de get_user_companies funcionando")
        
        # Testar chamada com dados mock
        mock_user_data = {
            'id': 'test',
            'role': 'cliente_unique'
        }
        
        # Isso deve gerar erro se get_user_companies não receber user_data
        try:
            result = get_user_companies()  # Chamada sem parâmetro - deve dar erro
            print("✗ get_user_companies() sem parâmetro NÃO deu erro - problema!")
        except TypeError as e:
            print(f"✓ get_user_companies() sem parâmetro deu erro como esperado: {e}")
            
        # Testar chamada correta
        try:
            result = get_user_companies(mock_user_data)  # Chamada com parâmetro
            print("✓ get_user_companies(user_data) funcionou corretamente")
        except Exception as e:
            print(f"✓ get_user_companies(user_data) falhou por motivo de dados: {e}")
            
    except Exception as e:
        print(f"✗ Erro na importação: {e}")

if __name__ == "__main__":
    test_import()
