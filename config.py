import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class Config:
    # Supabase Configuration
    SUPABASE_URL = os.getenv('SUPABASE_URL')
    SUPABASE_KEY = os.getenv('SUPABASE_KEY')
    SUPABASE_SERVICE_KEY = os.getenv('SUPABASE_SERVICE_KEY')
    SUPABASE_CURL_BEARER = os.getenv('SUPABASE_CURL_BEARER')
    
    # Flask Configuration
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-key-change-in-production')
    DEBUG = os.getenv('FLASK_DEBUG', 'False').lower() == 'true'
    
    # Performance Configuration
    QUERY_TIMEOUT = int(os.getenv('QUERY_TIMEOUT', '15'))  # 15 segundos de timeout para queries normais
    GEMINI_TIMEOUT = int(os.getenv('GEMINI_TIMEOUT', '120'))  # 120 segundos para processamento IA
    UPLOAD_TIMEOUT = int(os.getenv('UPLOAD_TIMEOUT', '300'))  # 300 segundos para upload/processamento
    MAX_ROWS_DASHBOARD = int(os.getenv('MAX_ROWS_DASHBOARD', '1000'))  # Máximo 1000 linhas no dashboard
    
    # Application Configuration
    APP_NAME = "UniSystem Portal"
      # Dashboard Configuration
    DASH_DEBUG = os.getenv('DASH_DEBUG', 'False').lower() == 'true'
      # PDF Generation Configuration
    PDF_TEMP_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'temp')
      # AI Configuration
    GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
    
    # Upload Configuration
    UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static/uploads/conferencia')
    MAX_CONTENT_LENGTH = 20 * 1024 * 1024  # 20MB limit for uploads
    
    @staticmethod
    def init_app(app):
        # Create temp directory for PDF generation if it doesn't exist
        if not os.path.exists(Config.PDF_TEMP_DIR):
            os.makedirs(Config.PDF_TEMP_DIR)
        
        # Create uploads directory if it doesn't exist
        if not os.path.exists(Config.UPLOAD_FOLDER):
            os.makedirs(Config.UPLOAD_FOLDER)