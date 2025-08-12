"""
Utilitário compartilhado para branding dinâmico do cliente.
Centraliza a lógica de obtenção de logo e nome da empresa baseado no usuário logado.
"""
from extensions import supabase_admin

DEFAULT_BRANDING = {
    'name': 'Unique',
    'logo_url': '/static/medias/Logo_Unique.png'
}

def get_client_branding(user_email=None):
    """
    Obtém o branding (nome e logo) do cliente baseado no email do usuário.
    
    Args:
        user_email (str): Email do usuário logado
        
    Returns:
        dict: {'name': str, 'logo_url': str}
    """
    if not user_email:
        return DEFAULT_BRANDING.copy()
    
    client_branding = DEFAULT_BRANDING.copy()
    
    try:
        branding_q = supabase_admin.table('vw_user_client_logos') \
            .select('empresa, logo_url') \
            .eq('user_email', user_email) \
            .limit(1).execute()
            
        if branding_q.data:
            row = branding_q.data[0]
            if row.get('empresa'):
                client_branding['name'] = row.get('empresa')
            if row.get('logo_url'):
                client_branding['logo_url'] = row.get('logo_url')
                
        print(f"[DEBUG] Branding selecionado para {user_email}: {client_branding}")
        
    except Exception as e:
        print(f"[DEBUG] Erro ao obter branding do cliente: {e}")
    
    return client_branding
