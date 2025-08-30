"""
Serviço para carregar perfis de usuário durante o login
"""
from extensions import supabase_admin
import json

def load_user_perfis(user_id, supabase_client=None):
    """
    Carrega os perfis completos do usuário com módulos e páginas
    
    Args:
        user_id (str): ID do usuário
        supabase_client: Cliente Supabase (opcional, usa supabase_admin se não fornecido)
        
    Returns:
        list: Lista de perfis com estrutura completa
    """
    try:
        print(f"[PERFIS_LOADER] Carregando perfis para usuário {user_id}")
        
        # Usar cliente fornecido ou o padrão
        if supabase_client:
            client = supabase_client
            print("[PERFIS_LOADER] Usando cliente Supabase fornecido")
        else:
            from extensions import supabase_admin
            client = supabase_admin
            print("[PERFIS_LOADER] Usando cliente supabase_admin")
        
        if not client:
            print("[PERFIS_LOADER] ❌ Cliente Supabase não disponível")
            return []
        
        # Buscar perfis do usuário na tabela users
        from modules.usuarios.routes import get_users_table
        user_response = client.table(get_users_table()).select('perfis_json').eq('id', user_id).execute()
        
        if not user_response.data:
            print(f"[PERFIS_LOADER] ⚠️ Usuário {user_id} não encontrado")
            return []
        
        user_data = user_response.data[0]
        perfis_json = user_data.get('perfis_json')
        
        if not perfis_json:
            print(f"[PERFIS_LOADER] ⚠️ Usuário {user_id} não tem perfis atribuídos")
            return []
        
        # Converter para lista se for string
        if isinstance(perfis_json, str):
            try:
                perfis_list = json.loads(perfis_json)
            except json.JSONDecodeError:
                print(f"[PERFIS_LOADER] ❌ Erro ao decodificar perfis_json: {perfis_json}")
                return []
        else:
            perfis_list = perfis_json
        
        print(f"[PERFIS_LOADER] 📋 Perfis encontrados: {perfis_list}")
        
        # Carregar dados completos de cada perfil
        user_perfis_info = []
        
        for perfil_codigo in perfis_list:
            if not perfil_codigo:
                continue
                
            print(f"[PERFIS_LOADER] 🔍 Carregando dados do perfil: {perfil_codigo}")
            
            # Buscar módulos do perfil na tabela users_perfis
            perfil_response = client.table('users_perfis')\
                .select('modulo_codigo, modulo_nome, paginas_modulo')\
                .eq('perfil_nome', perfil_codigo)\
                .eq('is_active', True)\
                .execute()
            
            if not perfil_response.data:
                print(f"[PERFIS_LOADER] ⚠️ Nenhum módulo encontrado para perfil {perfil_codigo}")
                continue
            
            # Organizar módulos do perfil
            modulos = []
            for perfil_data in perfil_response.data:
                modulo_info = {
                    'codigo': perfil_data.get('modulo_codigo'),
                    'nome': perfil_data.get('modulo_nome'),
                    'paginas': perfil_data.get('paginas_modulo', [])
                }
                modulos.append(modulo_info)
                print(f"[PERFIS_LOADER]   📂 Módulo: {modulo_info['codigo']} ({len(modulo_info['paginas'])} páginas)")
            
            # Adicionar perfil completo
            perfil_info = {
                'perfil_nome': perfil_codigo,
                'modulos': modulos
            }
            
            user_perfis_info.append(perfil_info)
            print(f"[PERFIS_LOADER] ✅ Perfil {perfil_codigo} carregado com {len(modulos)} módulos")
        
        print(f"[PERFIS_LOADER] 🎯 Total de perfis carregados: {len(user_perfis_info)}")
        return user_perfis_info
        
    except Exception as e:
        print(f"[PERFIS_LOADER] ❌ Erro ao carregar perfis: {str(e)}")
        import traceback
        traceback.print_exc()
        return []

def test_perfis_loader():
    """Função de teste para debug"""
    import uuid
    
    # Simular teste com usuário fictício
    test_user_id = str(uuid.uuid4())
    print(f"Testando carregamento de perfis para usuário: {test_user_id}")
    
    result = load_user_perfis(test_user_id)
    print(f"Resultado: {result}")

if __name__ == "__main__":
    test_perfis_loader()
