import os
import sys
from dotenv import load_dotenv
from supabase import create_client, Client

# Load environment variables
load_dotenv()

# Supabase configuration
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY")

if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
    print("Error: SUPABASE_URL and SUPABASE_SERVICE_KEY must be set in .env file")
    sys.exit(1)

# Create Supabase client
supabase: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

def verify_metas_data():
    """Verify that the metas data has been correctly updated"""
    try:
        # Get all metas ordered by year and month
        response = supabase.table('fin_metas_financeiras').select('*').order('ano', desc=True).order('mes').execute()
        
        if not response.data:
            print("No metas found in the database")
            return
        
        print("Current Metas Data:")
        print("-" * 80)
        print(f"{'ID':<5} {'Ano':<6} {'Mês':<6} {'Meta':<15} {'Tipo':<12}")
        print("-" * 80)
        
        month_names = {
            '01': 'Janeiro',
            '02': 'Fevereiro',
            '03': 'Março',
            '04': 'Abril',
            '05': 'Maio',
            '06': 'Junho',
            '07': 'Julho',
            '08': 'Agosto',
            '09': 'Setembro',
            '10': 'Outubro',
            '11': 'Novembro',
            '12': 'Dezembro',
            None: 'Anual',
            '': 'Anual'
        }
        
        for meta in response.data:
            mes_desc = month_names.get(meta.get('mes'), meta.get('mes') or 'Anual')
            meta_value = f"R$ {meta['meta']:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
            print(f"{meta['id']:<5} {meta['ano']:<6} {mes_desc:<6} {meta_value:<15} {meta.get('tipo', 'N/A'):<12}")
        
        # Check for any non-numeric month values
        print("\n" + "=" * 80)
        print("Checking for invalid month values:")
        print("=" * 80)
        
        invalid_months = []
        for meta in response.data:
            mes = meta.get('mes')
            if mes is not None and mes != '':
                # Check if it's a valid numeric month
                if mes not in ['01', '02', '03', '04', '05', '06', '07', '08', '09', '10', '11', '12']:
                    invalid_months.append(meta)
        
        if invalid_months:
            print("Found invalid month values:")
            for meta in invalid_months:
                print(f"  ID: {meta['id']}, Ano: {meta['ano']}, Mês: {meta['mes']}, Meta: {meta['meta']}")
        else:
            print("✓ All month values are valid!")
            
    except Exception as e:
        print(f"Error verifying metas data: {e}")

if __name__ == "__main__":
    verify_metas_data()