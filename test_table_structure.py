import requests
import json

# Configuração do teste
BASE_URL = "http://127.0.0.1:5000"

def test_table_structure():
    """Testa o endpoint de estrutura da tabela"""
    try:
        response = requests.get(f"{BASE_URL}/materiais/debug-table-structure")
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"Total records: {data.get('total_records', 'N/A')}")
            print("\nColumns Info:")
            
            columns = data.get('columns_info', {})
            for col_name, col_info in columns.items():
                print(f"  {col_name}: {col_info['type']} = {col_info['value']} (empty: {col_info['is_empty']})")
                
            print(f"\nSample Data:")
            sample = data.get('sample_data', [])
            for i, record in enumerate(sample):
                print(f"  Record {i+1}: {len(record)} fields")
                
        else:
            print(f"Error: {response.text}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_table_structure()
