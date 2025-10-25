-- ============================================================================
-- QUERIES DE ANÁLISE - ANALYTICS DE CLIQUES EM NOTÍCIAS COMEX
-- ============================================================================

-- 1. RANKING DE NOTÍCIAS MAIS CLICADAS
-- Mostra quais notícias tiveram mais engajamento
SELECT 
    SUBSTRING(page_name FROM 'Notícia COMEX: (.*)') AS titulo_noticia,
    COUNT(*) AS total_cliques,
    COUNT(DISTINCT user_id) AS usuarios_unicos,
    COUNT(DISTINCT user_email) AS emails_unicos,
    MIN(created_at_br) AS primeiro_clique,
    MAX(created_at_br) AS ultimo_clique,
    ROUND(
        EXTRACT(EPOCH FROM (MAX(created_at_br) - MIN(created_at_br))) / 3600, 
        2
    ) AS horas_de_engajamento
FROM public.access_logs
WHERE action_type = 'news_click'
GROUP BY page_name
ORDER BY total_cliques DESC
LIMIT 20;

-- 2. ANÁLISE POR USUÁRIO (COM USER_ID)
-- Mostra quem são os usuários mais engajados com as notícias
SELECT 
    al.user_id,
    al.user_email,
    al.user_name,
    al.user_role,
    COUNT(*) AS total_cliques,
    COUNT(DISTINCT DATE(al.created_at_br)) AS dias_ativos,
    MIN(al.created_at_br) AS primeira_interacao,
    MAX(al.created_at_br) AS ultima_interacao,
    STRING_AGG(
        DISTINCT SUBSTRING(al.page_name FROM 'Notícia COMEX: (.*)'), 
        ' | ' 
        ORDER BY SUBSTRING(al.page_name FROM 'Notícia COMEX: (.*)')
    ) AS noticias_lidas
FROM public.access_logs al
WHERE al.action_type = 'news_click'
GROUP BY al.user_id, al.user_email, al.user_name, al.user_role
ORDER BY total_cliques DESC;

-- 3. ANÁLISE TEMPORAL - CLIQUES POR DIA
-- Mostra tendência de engajamento ao longo do tempo
SELECT 
    DATE(created_at_br) AS data,
    COUNT(*) AS total_cliques,
    COUNT(DISTINCT user_id) AS usuarios_unicos,
    COUNT(DISTINCT SUBSTRING(page_name FROM 'Notícia COMEX: (.*)')) AS noticias_diferentes,
    ROUND(COUNT(*)::numeric / COUNT(DISTINCT user_id), 2) AS cliques_por_usuario
FROM public.access_logs
WHERE action_type = 'news_click'
    AND created_at_br >= CURRENT_DATE - INTERVAL '30 days'
GROUP BY DATE(created_at_br)
ORDER BY data DESC;

-- 4. ANÁLISE POR HORÁRIO DO DIA
-- Identifica em quais horários há mais engajamento
SELECT 
    EXTRACT(HOUR FROM created_at_br) AS hora_do_dia,
    COUNT(*) AS total_cliques,
    COUNT(DISTINCT user_id) AS usuarios_unicos,
    ROUND(AVG(EXTRACT(EPOCH FROM response_time)), 2) AS tempo_resposta_medio_ms
FROM public.access_logs
WHERE action_type = 'news_click'
GROUP BY EXTRACT(HOUR FROM created_at_br)
ORDER BY hora_do_dia;

-- 5. ANÁLISE POR PERFIL DE USUÁRIO
-- Compara engajamento entre diferentes tipos de usuários
SELECT 
    user_role,
    COUNT(*) AS total_cliques,
    COUNT(DISTINCT user_id) AS usuarios_unicos,
    ROUND(COUNT(*)::numeric / NULLIF(COUNT(DISTINCT user_id), 0), 2) AS cliques_por_usuario,
    COUNT(DISTINCT SUBSTRING(page_name FROM 'Notícia COMEX: (.*)')) AS noticias_diferentes
FROM public.access_logs
WHERE action_type = 'news_click'
GROUP BY user_role
ORDER BY total_cliques DESC;

-- 6. ÚLTIMOS 50 CLIQUES (LOG COMPLETO)
-- Para auditoria e debugging
SELECT 
    id,
    user_id,
    user_email,
    user_name,
    user_role,
    SUBSTRING(page_name FROM 'Notícia COMEX: (.*)') AS titulo_noticia,
    ip_address,
    SUBSTRING(user_agent, 1, 50) AS navegador,
    session_id,
    created_at_br
FROM public.access_logs
WHERE action_type = 'news_click'
ORDER BY created_at_br DESC
LIMIT 50;

-- 7. TAXA DE RETENÇÃO - USUÁRIOS QUE VOLTAM
-- Identifica usuários que clicam em múltiplas notícias (mais engajados)
SELECT 
    CASE 
        WHEN cliques = 1 THEN '1 clique (novo)'
        WHEN cliques BETWEEN 2 AND 5 THEN '2-5 cliques (engajado)'
        WHEN cliques BETWEEN 6 AND 10 THEN '6-10 cliques (muito engajado)'
        ELSE '10+ cliques (super engajado)'
    END AS nivel_engajamento,
    COUNT(*) AS quantidade_usuarios,
    ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 2) AS percentual
FROM (
    SELECT 
        user_id,
        COUNT(*) AS cliques
    FROM public.access_logs
    WHERE action_type = 'news_click'
        AND user_id IS NOT NULL
    GROUP BY user_id
) AS user_engagement
GROUP BY 
    CASE 
        WHEN cliques = 1 THEN '1 clique (novo)'
        WHEN cliques BETWEEN 2 AND 5 THEN '2-5 cliques (engajado)'
        WHEN cliques BETWEEN 6 AND 10 THEN '6-10 cliques (muito engajado)'
        ELSE '10+ cliques (super engajado)'
    END
ORDER BY MIN(cliques);

-- 8. ANÁLISE POR DEVICE TYPE (se disponível)
-- Mostra se usuários clicam mais no desktop ou mobile
SELECT 
    device_type,
    COUNT(*) AS total_cliques,
    COUNT(DISTINCT user_id) AS usuarios_unicos,
    ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 2) AS percentual
FROM public.access_logs
WHERE action_type = 'news_click'
GROUP BY device_type
ORDER BY total_cliques DESC;

-- 9. CROSS-REFERENCE: USUÁRIOS QUE CLICAM EM NOTÍCIAS E USAM OUTRAS FUNCIONALIDADES
-- Identifica se usuários engajados com notícias também usam outros módulos
SELECT 
    u.user_email,
    u.user_name,
    COUNT(CASE WHEN u.action_type = 'news_click' THEN 1 END) AS cliques_noticias,
    COUNT(CASE WHEN u.action_type != 'news_click' THEN 1 END) AS outras_acoes,
    COUNT(DISTINCT u.module_name) AS modulos_acessados,
    STRING_AGG(DISTINCT u.module_name, ', ') AS lista_modulos
FROM public.access_logs u
WHERE u.user_id IN (
    SELECT DISTINCT user_id 
    FROM public.access_logs 
    WHERE action_type = 'news_click' 
        AND user_id IS NOT NULL
)
GROUP BY u.user_email, u.user_name
ORDER BY cliques_noticias DESC;

-- 10. EXPORT PARA ANÁLISE EXTERNA (CSV)
-- Dados completos para análise em Excel/Power BI
SELECT 
    al.created_at_br AS data_hora,
    DATE(al.created_at_br) AS data,
    EXTRACT(HOUR FROM al.created_at_br) AS hora,
    TO_CHAR(al.created_at_br, 'Day') AS dia_semana,
    al.user_id,
    al.user_email,
    al.user_name,
    al.user_role,
    SUBSTRING(al.page_name FROM 'Notícia COMEX: (.*)') AS titulo_noticia,
    al.ip_address,
    al.device_type,
    al.session_id
FROM public.access_logs al
WHERE al.action_type = 'news_click'
ORDER BY al.created_at_br DESC;

-- ============================================================================
-- VIEWS ÚTEIS (OPCIONAL - CRIAR SE QUISER FACILITAR CONSULTAS RECORRENTES)
-- ============================================================================

-- View: Notícias mais populares (últimos 30 dias)
CREATE OR REPLACE VIEW v_noticias_populares_30d AS
SELECT 
    SUBSTRING(page_name FROM 'Notícia COMEX: (.*)') AS titulo,
    COUNT(*) AS cliques,
    COUNT(DISTINCT user_id) AS usuarios_unicos,
    MAX(created_at_br) AS ultimo_clique
FROM public.access_logs
WHERE action_type = 'news_click'
    AND created_at_br >= CURRENT_DATE - INTERVAL '30 days'
GROUP BY page_name
ORDER BY cliques DESC;

-- View: Usuários mais engajados
CREATE OR REPLACE VIEW v_usuarios_engajados_noticias AS
SELECT 
    user_id,
    user_email,
    user_name,
    user_role,
    COUNT(*) AS total_cliques,
    MAX(created_at_br) AS ultimo_clique,
    MIN(created_at_br) AS primeiro_clique
FROM public.access_logs
WHERE action_type = 'news_click'
    AND user_id IS NOT NULL
GROUP BY user_id, user_email, user_name, user_role
ORDER BY total_cliques DESC;
