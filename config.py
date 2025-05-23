import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class Config:
    # Supabase Configuration
    SUPABASE_URL = 'https://ixytthtngeifjumvbuwe.supabase.co'
    # Usando a service_role key que sabemos que funciona
    SUPABASE_KEY = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Iml4eXR0aHRuZ2VpZmp1bXZidXdlIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc0NzkyMjAwNCwiZXhwIjoyMDYzNDk4MDA0fQ.SGULtvLf25EMeqWzxnMg91IlTBABdDxABffJAGfNVNw'
    SUPABASE_SERVICE_KEY = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Iml4eXR0aHRuZ2VpZmp1bXZidXdlIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc0NzkyMjAwNCwiZXhwIjoyMDYzNDk4MDA0fQ.SGULtvLf25EMeqWzxnMg91IlTBABdDxABffJAGfNVNw'
    
    # Flask Configuration
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-key-change-in-production')
    DEBUG = True  # Forçando DEBUG para true para ver mais logs
    
    # Application Configuration
    APP_NAME = "Unique Aduaneira Portal"
    
    # Dashboard Configuration
    DASH_DEBUG = os.getenv('DASH_DEBUG', 'False').lower() == 'true'
    
    # PDF Generation Configuration
    PDF_TEMP_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'temp')
    
    @staticmethod
    def init_app(app):
        # Create temp directory for PDF generation if it doesn't exist
        if not os.path.exists(Config.PDF_TEMP_DIR):
            os.makedirs(Config.PDF_TEMP_DIR) 