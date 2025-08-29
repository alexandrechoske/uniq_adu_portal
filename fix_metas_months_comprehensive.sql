-- Comprehensive SQL script to update month values in fin_metas_financeiras table
-- This handles various possible variations of month names in Portuguese

-- First, let's check what we currently have in the table
SELECT DISTINCT mes, COUNT(*) as count
FROM public.fin_metas_financeiras 
GROUP BY mes
ORDER BY mes;

-- Update statements for each month with various possible variations
UPDATE public.fin_metas_financeiras 
SET mes = '01' 
WHERE UPPER(mes) IN ('JANEIRO', 'JAN');

UPDATE public.fin_metas_financeiras 
SET mes = '02' 
WHERE UPPER(mes) IN ('FEVEREIRO', 'FEV');

UPDATE public.fin_metas_financeiras 
SET mes = '03' 
WHERE UPPER(mes) IN ('MARÇO', 'MARCO', 'MAR');

UPDATE public.fin_metas_financeiras 
SET mes = '04' 
WHERE UPPER(mes) IN ('ABRIL', 'ABR');

UPDATE public.fin_metas_financeiras 
SET mes = '05' 
WHERE UPPER(mes) IN ('MAIO', 'MAI');

UPDATE public.fin_metas_financeiras 
SET mes = '06' 
WHERE UPPER(mes) IN ('JUNHO', 'JUN');

UPDATE public.fin_metas_financeiras 
SET mes = '07' 
WHERE UPPER(mes) IN ('JULHO', 'JUL');

UPDATE public.fin_metas_financeiras 
SET mes = '08' 
WHERE UPPER(mes) IN ('AGOSTO', 'AGO');

UPDATE public.fin_metas_financeiras 
SET mes = '09' 
WHERE UPPER(mes) IN ('SETEMBRO', 'SET');

UPDATE public.fin_metas_financeiras 
SET mes = '10' 
WHERE UPPER(mes) IN ('OUTUBRO', 'OUT');

UPDATE public.fin_metas_financeiras 
SET mes = '11' 
WHERE UPPER(mes) IN ('NOVEMBRO', 'NOV');

UPDATE public.fin_metas_financeiras 
SET mes = '12' 
WHERE UPPER(mes) IN ('DEZEMBRO', 'DEZ');

-- Handle any NULL or empty values that should be annual metas
UPDATE public.fin_metas_financeiras 
SET mes = NULL 
WHERE mes = '' OR UPPER(mes) = 'ANUAL' OR UPPER(mes) = 'ANUAL';

-- Verify the updates
SELECT id, ano, mes, 
       CASE 
         WHEN mes = '01' THEN 'Janeiro'
         WHEN mes = '02' THEN 'Fevereiro'
         WHEN mes = '03' THEN 'Março'
         WHEN mes = '04' THEN 'Abril'
         WHEN mes = '05' THEN 'Maio'
         WHEN mes = '06' THEN 'Junho'
         WHEN mes = '07' THEN 'Julho'
         WHEN mes = '08' THEN 'Agosto'
         WHEN mes = '09' THEN 'Setembro'
         WHEN mes = '10' THEN 'Outubro'
         WHEN mes = '11' THEN 'Novembro'
         WHEN mes = '12' THEN 'Dezembro'
         WHEN mes IS NULL THEN 'Anual'
         ELSE mes
       END as mes_descricao,
       meta, tipo 
FROM public.fin_metas_financeiras 
ORDER BY ano DESC, mes NULLS FIRST;