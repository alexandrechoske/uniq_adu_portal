-- Adicionar dashboard_operacional ao perfil operacao_importacoes_acesso_comum
-- Data: 2025-09-22
-- Objetivo: Permitir que usuários com perfil operacao_importacoes_acesso_comum acessem o Dashboard Operacional

-- 1. Primeiro, verificar o perfil atual
SELECT perfil_nome, modulos 
FROM user_perfis 
WHERE perfil_nome = 'operacao_importacoes_acesso_comum';

-- 2. Atualizar o perfil para incluir dashboard_operacional
UPDATE user_perfis 
SET modulos = jsonb_set(
    modulos,
    '{0,paginas}',
    (
        SELECT CASE 
            WHEN jsonb_typeof(modulos->'0'->'paginas') = 'array' THEN
                modulos->'0'->'paginas' || '["dashboard_operacional"]'::jsonb
            ELSE
                '["dashboard_executivo", "dashboard_operacional", "dashboard_resumido", "relatorio", "documentos", "agente"]'::jsonb
        END
    )
)
WHERE perfil_nome = 'operacao_importacoes_acesso_comum'
AND NOT (modulos->'0'->'paginas' @> '["dashboard_operacional"]'::jsonb);

-- 3. Verificar a atualização
SELECT perfil_nome, modulos 
FROM user_perfis 
WHERE perfil_nome = 'operacao_importacoes_acesso_comum';

-- 4. Forçar atualização dos dados em cache (se necessário)
-- Os usuários podem precisar fazer logout/login para ver as mudanças

/*
ESTRUTURA ESPERADA APÓS A ATUALIZAÇÃO:
{
  "modulos": [
    {
      "codigo": "imp",
      "paginas": [
        "dashboard_executivo",
        "dashboard_operacional",  <-- NOVA PÁGINA
        "dashboard_resumido",
        "relatorio",
        "documentos",
        "agente"
      ]
    }
  ]
}
*/