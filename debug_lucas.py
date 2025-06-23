import sys
sys.path.append('.')

from config import Config
from supabase import create_client, Client
import json

# Inicializar Supabase (usando cliente admin para bypassing RLS)
url = Config.SUPABASE_URL
service_key = Config.SUPABASE_SERVICE_KEY
supabase: Client = create_client(url, service_key)

# Buscar dados do usuário Lucas Vexani
user_id_lucas = '379966ab-6d30-4bbe-a31c-e9fa2232ca5f'
print(f'Buscando dados para Lucas Vexani: {user_id_lucas}')

# Verificar dados na tabela clientes_agentes
agent_data_lucas = supabase.table('clientes_agentes').select('*').eq('user_id', user_id_lucas).execute()
print(f'Dados do agente Lucas: {agent_data_lucas.data}')

if agent_data_lucas.data:
    for agent in agent_data_lucas.data:
        print(f'usuario_ativo: {agent.get("usuario_ativo")}')
        print(f'aceite_termos: {agent.get("aceite_termos")}')
        print(f'empresa: {agent.get("empresa")}')

# Verificar se precisa ativar o usuário Lucas
if agent_data_lucas.data:
    agent_lucas = agent_data_lucas.data[0]
    if agent_lucas.get('usuario_ativo') is None:
        print('\nUsuário Lucas não tem campo usuario_ativo definido. Ativando...')
        update_response_lucas = supabase.table('clientes_agentes').update({
            'usuario_ativo': True,
            'aceite_termos': True
        }).eq('user_id', user_id_lucas).execute()
        print(f'Resultado da atualização Lucas: {update_response_lucas.data}')
    else:
        print('Usuario Lucas já está ativo')
else:
    print('Usuário Lucas não tem registro em clientes_agentes. Criando...')
    # Buscar empresas que o usuário deveria ter acesso (baseado no que vimos nos logs)
    empresas_lucas = ['00.289.348/0008-17', '00.289.348/0007-36', '00.289.348/0001-40', '37.076.760/0001-92', '00.289.348/0006-55']
    
    insert_response_lucas = supabase.table('clientes_agentes').insert({
        'user_id': user_id_lucas,
        'empresa': empresas_lucas,
        'usuario_ativo': True,
        'aceite_termos': True
    }).execute()
    print(f'Resultado da inserção Lucas: {insert_response_lucas.data}')
