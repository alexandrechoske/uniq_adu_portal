# Agente Unique - Múltiplos Números por Usuário

## Resumo das Mudanças

O sistema foi modificado para permitir que um usuário cadastre múltiplos números de WhatsApp no Agente Unique usando um array JSONB na coluna `numero`.

### Estrutura do Banco

A tabela `clientes_agentes` agora funciona assim:

- **1 usuário : 1 registro**
- **Campo `numero`**: Array JSONB com múltiplos números
- **Campo `empresa`**: Array JSONB com empresas (mantido como antes)

Exemplo de dados após migração:
```json
{
  "user_id": "8c462a7a-1455-4ca7-b58c-ae84b5a3b333",
  "numero": ["5511999999999", "5511888888888"],
  "empresa": ["37.076.760/0001-92", "75.339.051/0001-41"],
  "aceite_termos": true,
  "usuario_ativo": true
}
```

### Funcionalidades Implementadas

#### 1. Cadastro de Múltiplos Números
- Usuário pode adicionar quantos números quiser ao array
- Cada número é validado individualmente
- Prevenção de números duplicados entre usuários diferentes

#### 2. Gerenciamento Individual
- Lista todos os números do array
- Permite remover números específicos do array
- Opção para remover todos os números (desativa usuário)

#### 3. Funções Utilitárias

```python
# Adicionar número ao array
add_numero_to_user(user_id, novo_numero)

# Remover número específico do array  
remove_numero_from_user(user_id, numero_para_remover)

# Buscar empresas do usuário
get_user_companies(user_id)

# Sincronizar empresas para o usuário
sync_user_companies_to_agent_numbers(user_id, companies)
```

### Vantagens da Nova Abordagem

1. **Melhor normalização**: 1 usuário = 1 registro
2. **Consistência**: Mesmo padrão da coluna `empresa` (array JSONB)
3. **Performance**: Menos registros na tabela
4. **Simplicidade**: Mais fácil de gerenciar e consultar
5. **Atomicidade**: Operações em um único registro

### Interface Atualizada

- **Formulário de adição**: Sempre disponível para adicionar novos números
- **Lista de números**: Mostra todos os números do array com opções de remoção
- **Design responsivo**: Funciona bem em dispositivos móveis

### Migração de Dados

Os dados existentes precisam ser migrados de múltiplos registros para array. Ver arquivo `migracao_agente_array.md` para o script SQL completo.

### Exemplo de Uso

```python
# Adicionar número
success, message = add_numero_to_user("user-123", "5511999999999")

# Remover número
success, message = remove_numero_from_user("user-123", "5511999999999") 

# Buscar números do usuário
user_record = supabase.table('clientes_agentes').select('numero').eq('user_id', user_id).execute()
numeros = user_record.data[0]['numero'] if user_record.data else []

# Sincronizar empresas
sync_user_companies_to_agent_numbers("user-123", ["12.345.678/0001-90"])
```

### Próximos Passos

1. **Executar migração**: Usar o script SQL no arquivo `migracao_agente_array.md`
2. **Implementar busca de empresas**: Na linha 93 do `agente.py`, implementar a lógica real
3. **Integrar com sistema de permissões**: Usar `sync_user_companies_to_agent_numbers()` quando permissões mudarem
4. **Testes**: Testar todos os cenários (add/remove números, validações, etc.)
