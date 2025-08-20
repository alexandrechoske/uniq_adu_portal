-- Views e funções para o módulo de Fluxo de Caixa

-- View para resultado anual agregado
CREATE OR REPLACE VIEW vw_resultado_anual AS
SELECT 
    DATE_TRUNC('month', data) as mes,
    EXTRACT(year FROM data) as ano,
    categoria,
    classe,
    tipo,
    SUM(valor) as valor
FROM fin_base_resultado
GROUP BY DATE_TRUNC('month', data), EXTRACT(year FROM data), categoria, classe, tipo
ORDER BY mes DESC;

-- Função para calcular burn rate
CREATE OR REPLACE FUNCTION calcular_burn_rate(
    p_data_inicio DATE DEFAULT NULL,
    p_data_fim DATE DEFAULT NULL
) 
RETURNS NUMERIC AS $$
DECLARE
    v_burn_rate NUMERIC := 0;
BEGIN
    -- Se não informar datas, usa últimos 6 meses
    IF p_data_inicio IS NULL THEN
        p_data_inicio := DATE_TRUNC('month', CURRENT_DATE) - INTERVAL '6 months';
    END IF;
    
    IF p_data_fim IS NULL THEN
        p_data_fim := CURRENT_DATE;
    END IF;
    
    -- Calcular média dos resultados negativos mensais
    SELECT COALESCE(AVG(ABS(resultado_mensal)), 0)
    INTO v_burn_rate
    FROM (
        SELECT 
            DATE_TRUNC('month', data) as mes,
            SUM(CASE WHEN tipo = 'Receita' THEN valor ELSE -valor END) as resultado_mensal
        FROM fin_base_resultado
        WHERE data BETWEEN p_data_inicio AND p_data_fim
        GROUP BY DATE_TRUNC('month', data)
        HAVING SUM(CASE WHEN tipo = 'Receita' THEN valor ELSE -valor END) < 0
    ) resultados_negativos;
    
    RETURN v_burn_rate;
END;
$$ LANGUAGE plpgsql;

-- Função para calcular runway
CREATE OR REPLACE FUNCTION calcular_runway(
    p_saldo_atual NUMERIC,
    p_burn_rate NUMERIC
) 
RETURNS NUMERIC AS $$
BEGIN
    IF p_burn_rate <= 0 THEN
        RETURN 999; -- Runway "infinito"
    END IF;
    
    RETURN p_saldo_atual / p_burn_rate;
END;
$$ LANGUAGE plpgsql;

-- Função para obter fluxo estrutural (FCO, FCI, FCF)
CREATE OR REPLACE FUNCTION obter_fluxo_estrutural(
    p_data_inicio DATE DEFAULT NULL,
    p_data_fim DATE DEFAULT NULL
) 
RETURNS TABLE(
    mes DATE,
    fco NUMERIC,
    fci NUMERIC,
    fcf NUMERIC
) AS $$
BEGIN
    -- Se não informar datas, usa ano atual
    IF p_data_inicio IS NULL THEN
        p_data_inicio := DATE_TRUNC('year', CURRENT_DATE);
    END IF;
    
    IF p_data_fim IS NULL THEN
        p_data_fim := CURRENT_DATE;
    END IF;
    
    RETURN QUERY
    SELECT 
        DATE_TRUNC('month', r.data) as mes,
        
        -- FCO (Fluxo de Caixa Operacional)
        SUM(CASE 
            WHEN UPPER(r.categoria) IN ('IMPORTAÇÃO', 'EXPORTAÇÃO', 'CONSULTORIA') 
                OR UPPER(r.categoria) LIKE '%FUNCIONÁRIOS%'
                OR UPPER(r.categoria) LIKE '%DIRETORIA%'
                OR UPPER(r.categoria) LIKE '%IMPOSTOS%'
                OR UPPER(r.categoria) LIKE '%OPERACIONAIS%'
                OR UPPER(r.categoria) LIKE '%COMERCIAIS%'
                OR UPPER(r.categoria) LIKE '%ADMINISTRATIVAS%'
            THEN 
                CASE WHEN r.tipo = 'Receita' THEN r.valor ELSE -r.valor END
            ELSE 0 
        END) as fco,
        
        -- FCI (Fluxo de Caixa de Investimento)
        SUM(CASE 
            WHEN UPPER(r.categoria) LIKE '%ATIVO%'
            THEN 
                CASE WHEN r.tipo = 'Receita' THEN r.valor ELSE -r.valor END
            ELSE 0 
        END) as fci,
        
        -- FCF (Fluxo de Caixa de Financiamento)
        SUM(CASE 
            WHEN UPPER(r.categoria) IN ('EMPRÉSTIMOS', 'RENDIMENTO')
            THEN 
                CASE WHEN r.tipo = 'Receita' THEN r.valor ELSE -r.valor END
            ELSE 0 
        END) as fcf
        
    FROM fin_base_resultado r
    WHERE r.data BETWEEN p_data_inicio AND p_data_fim
    GROUP BY DATE_TRUNC('month', r.data)
    ORDER BY mes;
END;
$$ LANGUAGE plpgsql;

-- Índices para performance
CREATE INDEX IF NOT EXISTS idx_fin_base_resultado_data_mes 
    ON fin_base_resultado (DATE_TRUNC('month', data));

CREATE INDEX IF NOT EXISTS idx_fin_base_resultado_categoria_upper 
    ON fin_base_resultado (UPPER(categoria));

-- Comentários
COMMENT ON VIEW vw_resultado_anual IS 'View agregada por mês/ano para análise de fluxo de caixa';
COMMENT ON FUNCTION calcular_burn_rate IS 'Calcula o burn rate médio baseado em resultados mensais negativos';
COMMENT ON FUNCTION calcular_runway IS 'Calcula quantos meses a empresa pode operar com o saldo atual';
COMMENT ON FUNCTION obter_fluxo_estrutural IS 'Retorna fluxo estrutural (FCO, FCI, FCF) por mês';
