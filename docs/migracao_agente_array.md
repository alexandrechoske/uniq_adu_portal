# Script de Migração - Agente Unique
# Conversão de múltiplos registros para array de números

## ANTES DA MIGRAÇÃO - ESTRUTURA ATUAL
Os dados estão assim (múltiplos registros por usuário):
```
user_id: 8c462a7a-1455-4ca7-b58c-ae84b5a3b333
├── registro 1: numero = ""
├── registro 2: numero = "555123456789"

user_id: c77fa726-bebd-45af-a3bc-fd85f7567acf  
├── registro 1: numero = "555499576758"
```

## APÓS A MIGRAÇÃO - NOVA ESTRUTURA
Os dados ficarão assim (1 registro por usuário):
```
user_id: 8c462a7a-1455-4ca7-b58c-ae84b5a3b333
└── registro único: numero = ["555123456789"] (números válidos apenas)

user_id: c77fa726-bebd-45af-a3bc-fd85f7567acf
└── registro único: numero = ["555499576758"]
```

## SCRIPT SQL PARA MIGRAÇÃO

```sql
-- 1. Criar uma tabela temporária para consolidar os dados
CREATE TEMP TABLE temp_consolidation AS
SELECT 
    user_id,
    array_agg(DISTINCT numero) FILTER (WHERE numero IS NOT NULL AND numero != '') as numeros_consolidados,
    empresa[1] as empresa_consolidada,  -- Pega a primeira empresa (todas devem ser iguais)
    bool_or(aceite_termos) as aceite_termos_consolidado,
    bool_or(usuario_ativo) as usuario_ativo_consolidado,
    nome[1] as nome_consolidado,  -- Pega o primeiro nome
    min(created_at) as created_at_consolidado
FROM clientes_agentes 
WHERE user_id IS NOT NULL
GROUP BY user_id, empresa[1], nome[1];

-- 2. Limpar a tabela original (fazer backup antes!)
-- BACKUP: CREATE TABLE clientes_agentes_backup AS SELECT * FROM clientes_agentes;
DELETE FROM clientes_agentes;

-- 3. Inserir dados consolidados
INSERT INTO clientes_agentes (user_id, numero, empresa, aceite_termos, usuario_ativo, nome, created_at)
SELECT 
    user_id,
    numeros_consolidados,  -- Array de números
    empresa_consolidada,
    aceite_termos_consolidado,
    usuario_ativo_consolidado,
    nome_consolidado,
    created_at_consolidado
FROM temp_consolidation
WHERE array_length(numeros_consolidados, 1) > 0;  -- Só usuários com números válidos
```

## VERIFICAÇÃO PÓS-MIGRAÇÃO

```sql
-- Verificar se a migração foi bem-sucedida
SELECT 
    user_id,
    numero,
    array_length(numero, 1) as qtd_numeros,
    empresa,
    usuario_ativo
FROM clientes_agentes
ORDER BY user_id;
```

## EXECUTAR A MIGRAÇÃO

1. **FAZER BACKUP COMPLETO DOS DADOS**
2. Executar o script SQL acima
3. Testar a aplicação
4. Verificar se todos os números estão corretos

## ROLLBACK (SE NECESSÁRIO)

```sql
-- Se algo der errado, restaurar do backup
DROP TABLE clientes_agentes;
ALTER TABLE clientes_agentes_backup RENAME TO clientes_agentes;
```
