-- SQL script to update month values in fin_metas_financeiras table to use numeric format
-- This will convert Portuguese month names to their corresponding numeric values

UPDATE public.fin_metas_financeiras 
SET mes = '01' 
WHERE mes = 'JANEIRO' OR mes = 'Janeiro';

UPDATE public.fin_metas_financeiras 
SET mes = '02' 
WHERE mes = 'FEVEREIRO' OR mes = 'Fevereiro';

UPDATE public.fin_metas_financeiras 
SET mes = '03' 
WHERE mes = 'MARÇO' OR mes = 'MARCO' OR mes = 'Março' OR mes = 'Marco';

UPDATE public.fin_metas_financeiras 
SET mes = '04' 
WHERE mes = 'ABRIL' OR mes = 'Abril';

UPDATE public.fin_metas_financeiras 
SET mes = '05' 
WHERE mes = 'MAIO' OR mes = 'Maio';

UPDATE public.fin_metas_financeiras 
SET mes = '06' 
WHERE mes = 'JUNHO' OR mes = 'Junho';

UPDATE public.fin_metas_financeiras 
SET mes = '07' 
WHERE mes = 'JULHO' OR mes = 'Julho';

UPDATE public.fin_metas_financeiras 
SET mes = '08' 
WHERE mes = 'AGOSTO' OR mes = 'Agosto';

UPDATE public.fin_metas_financeiras 
SET mes = '09' 
WHERE mes = 'SETEMBRO' OR mes = 'Setembro';

UPDATE public.fin_metas_financeiras 
SET mes = '10' 
WHERE mes = 'OUTUBRO' OR mes = 'Outubro';

UPDATE public.fin_metas_financeiras 
SET mes = '11' 
WHERE mes = 'NOVEMBRO' OR mes = 'Novembro';

UPDATE public.fin_metas_financeiras 
SET mes = '12' 
WHERE mes = 'DEZEMBRO' OR mes = 'Dezembro';

-- Verify the updates
SELECT id, ano, mes, meta, tipo 
FROM public.fin_metas_financeiras 
ORDER BY ano DESC, mes;