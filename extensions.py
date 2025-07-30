from supabase import create_client, Client
from flask import current_app

supabase: Client = None
supabase_admin: Client = None

def init_supabase(app):
    global supabase, supabase_admin
    
    print("\n[DEBUG] ===== Iniciando configuração do Supabase =====")
    
    # Check if required environment variables are set
    if not app.config['SUPABASE_URL']:
        print("[DEBUG] ERRO: SUPABASE_URL não está configurado")
        raise ValueError("SUPABASE_URL environment variable is not set")
    if not app.config['SUPABASE_SERVICE_KEY']:
        print("[DEBUG] ERRO: SUPABASE_SERVICE_KEY não está configurado")
        raise ValueError("SUPABASE_SERVICE_KEY environment variable is not set")
    if not app.config['SUPABASE_SERVICE_KEY']:
        print("[DEBUG] ERRO: SUPABASE_SERVICE_KEY não está configurado")
        raise ValueError("SUPABASE_SERVICE_KEY environment variable is not set. This is required for admin operations.")
    
    print(f"[DEBUG] SUPABASE_URL: {app.config['SUPABASE_URL']}")
    print(f"[DEBUG] SUPABASE_SERVICE_KEY (primeiros 10 caracteres): {app.config['SUPABASE_SERVICE_KEY'][:10] if app.config['SUPABASE_SERVICE_KEY'] else 'None'}")
    print(f"[DEBUG] SUPABASE_SERVICE_KEY (primeiros 10 caracteres): {app.config['SUPABASE_SERVICE_KEY'][:10] if app.config['SUPABASE_SERVICE_KEY'] else 'None'}")
    
    try:
        # Regular client for normal operations
        print("\n[DEBUG] Criando cliente regular do Supabase...")
        print(f"[DEBUG] URL do cliente regular: {app.config['SUPABASE_URL']}")
        print(f"[DEBUG] Chave do cliente regular (primeiros 10 caracteres): {app.config['SUPABASE_SERVICE_KEY'][:10]}")
        supabase = create_client(app.config['SUPABASE_URL'], app.config['SUPABASE_SERVICE_KEY'])
        
        # Test the regular client
        print("[DEBUG] Testando cliente regular...")
        response = supabase.table('users').select("*").limit(1).execute()
        print(f"[DEBUG] Resposta do teste do cliente regular: {response}")
        print("[DEBUG] Cliente regular do Supabase criado e testado com sucesso")
        
        # Admin client for privileged operations
        print("\n[DEBUG] Criando cliente admin do Supabase...")
        print(f"[DEBUG] URL do cliente admin: {app.config['SUPABASE_URL']}")
        print(f"[DEBUG] Chave do cliente admin (primeiros 10 caracteres): {app.config['SUPABASE_SERVICE_KEY'][:10]}")
        supabase_admin = create_client(app.config['SUPABASE_URL'], app.config['SUPABASE_SERVICE_KEY'])
        
        # Test the admin client
        print("[DEBUG] Testando cliente admin...")
        response = supabase_admin.table('users').select("*").limit(1).execute()
        print(f"[DEBUG] Resposta do teste do cliente admin: {response}")
        print("[DEBUG] Cliente admin do Supabase criado e testado com sucesso")
        
    except Exception as e:
        print(f"\n[DEBUG] ERRO ao criar/testar clientes Supabase:")
        print(f"[DEBUG] Tipo do erro: {type(e)}")
        print(f"[DEBUG] Mensagem do erro: {str(e)}")
        raise
    
    print("[DEBUG] ===== Configuração do Supabase concluída =====\n") 