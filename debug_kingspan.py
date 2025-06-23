import sys
sys.path.append('.')

from config import Config
from supabase import create_client, Client
import json

# Inicializar Supabase (usando cliente admin para bypassing RLS)
url = Config.SUPABASE_URL
service_key = Config.SUPABASE_SERVICE_KEY
supabase: Client = create_client(url, service_key)

# Buscar dados do usuário Kingspan
user_id = '15ed9539-e993-4733-9042-1a3280d7a0cb'
print(f'Buscando dados para user_id: {user_id}')

# Verificar dados na tabela clientes_agentes
agent_data = supabase.table('clientes_agentes').select('*').eq('user_id', user_id).execute()
print(f'Dados do agente: {agent_data.data}')

if agent_data.data:
    for agent in agent_data.data:
        print(f'usuario_ativo: {agent.get("usuario_ativo")}')
        print(f'aceite_termos: {agent.get("aceite_termos")}')
        print(f'empresa: {agent.get("empresa")}')
        
# Verificar se precisa criar/ativar o usuário
if agent_data.data:
    agent = agent_data.data[0]
    if agent.get('usuario_ativo') is None:
        print('Usuario não tem campo usuario_ativo definido. Ativando...')
        update_response = supabase.table('clientes_agentes').update({
            'usuario_ativo': True,
            'aceite_termos': True
        }).eq('user_id', user_id).execute()
        print(f'Resultado da atualização: {update_response.data}')
else:
    print('Usuário não tem registro em clientes_agentes. Criando...')    # Buscar empresas que o usuário deveria ter acesso (baseado no que vimos nos logs)
    empresas_kingspan = ['00.289.348/0008-17', '00.289.348/0007-36', '00.289.348/0001-40', '37.076.760/0001-92', '00.289.348/0006-55']
    
    insert_response = supabase.table('clientes_agentes').insert({
        'user_id': user_id,
        'empresa': empresas_kingspan,
        'usuario_ativo': True,
        'aceite_termos': True
    }).execute()
    print(f'Resultado da inserção: {insert_response.data}')
