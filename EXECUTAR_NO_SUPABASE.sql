-- =====================================================================
-- MIGRATION: Adicionar campos completos em rh_vagas e rh_candidatos
-- EXECUTE NO SQL EDITOR DO SUPABASE
-- =====================================================================

BEGIN;

-- =====================================================================
-- PARTE 1: rh_candidatos (17 novos campos)
-- =====================================================================

ALTER TABLE public.rh_candidatos
    -- Dados Demográficos
    ADD COLUMN IF NOT EXISTS sexo VARCHAR(1),
    ADD COLUMN IF NOT EXISTS data_nascimento DATE,
    ADD COLUMN IF NOT EXISTS estado_civil VARCHAR(50),
    ADD COLUMN IF NOT EXISTS cidade VARCHAR(100),
    ADD COLUMN IF NOT EXISTS estado VARCHAR(2),
    
    -- Dados de Indicação
    ADD COLUMN IF NOT EXISTS foi_indicacao BOOLEAN DEFAULT FALSE,
    ADD COLUMN IF NOT EXISTS indicado_por VARCHAR(255),
    
    -- Formação e Experiência
    ADD COLUMN IF NOT EXISTS area_objetivo VARCHAR(100),
    ADD COLUMN IF NOT EXISTS formacao_academica VARCHAR(100),
    ADD COLUMN IF NOT EXISTS curso_especifico VARCHAR(200),
    ADD COLUMN IF NOT EXISTS trabalha_atualmente BOOLEAN,
    ADD COLUMN IF NOT EXISTS experiencia_na_area BOOLEAN,
    
    -- Processo Seletivo
    ADD COLUMN IF NOT EXISTS realizou_entrevista BOOLEAN DEFAULT FALSE,
    ADD COLUMN IF NOT EXISTS data_entrevista DATE,
    
    -- Contratação
    ADD COLUMN IF NOT EXISTS foi_contratado BOOLEAN DEFAULT FALSE,
    ADD COLUMN IF NOT EXISTS data_contratacao DATE,
    ADD COLUMN IF NOT EXISTS colaborador_id UUID;

-- Constraints rh_candidatos
ALTER TABLE public.rh_candidatos
ADD CONSTRAINT IF NOT EXISTS rh_candidatos_colaborador_fkey 
FOREIGN KEY (colaborador_id) REFERENCES rh_colaboradores(id) ON DELETE SET NULL;

ALTER TABLE public.rh_candidatos
DROP CONSTRAINT IF EXISTS rh_candidatos_sexo_check;
ALTER TABLE public.rh_candidatos
ADD CONSTRAINT rh_candidatos_sexo_check 
CHECK (sexo IN ('M', 'F') OR sexo IS NULL);

ALTER TABLE public.rh_candidatos
DROP CONSTRAINT IF EXISTS rh_candidatos_formacao_check;
ALTER TABLE public.rh_candidatos
ADD CONSTRAINT rh_candidatos_formacao_check CHECK (
    formacao_academica IN (
        'Ensino Fundamental',
        'Ensino Médio',
        'Técnico',
        'Cursando Graduação',
        'Graduação',
        'Pós-graduação',
        'Mestrado',
        'Doutorado',
        'Sem informação'
    ) OR formacao_academica IS NULL
);

-- Índices rh_candidatos
CREATE INDEX IF NOT EXISTS idx_rh_candidatos_cidade ON public.rh_candidatos(cidade);
CREATE INDEX IF NOT EXISTS idx_rh_candidatos_estado ON public.rh_candidatos(estado);
CREATE INDEX IF NOT EXISTS idx_rh_candidatos_foi_indicacao ON public.rh_candidatos(foi_indicacao);
CREATE INDEX IF NOT EXISTS idx_rh_candidatos_experiencia ON public.rh_candidatos(experiencia_na_area);
CREATE INDEX IF NOT EXISTS idx_rh_candidatos_colaborador ON public.rh_candidatos(colaborador_id);

-- =====================================================================
-- PARTE 2: rh_vagas (10 novos campos)
-- =====================================================================

ALTER TABLE public.rh_vagas
    -- Remuneração e Benefícios
    ADD COLUMN IF NOT EXISTS faixa_salarial_min NUMERIC(10, 2),
    ADD COLUMN IF NOT EXISTS faixa_salarial_max NUMERIC(10, 2),
    ADD COLUMN IF NOT EXISTS beneficios TEXT,
    
    -- Detalhes da Vaga
    ADD COLUMN IF NOT EXISTS nivel_senioridade VARCHAR(50),
    ADD COLUMN IF NOT EXISTS quantidade_vagas INTEGER DEFAULT 1,
    ADD COLUMN IF NOT EXISTS regime_trabalho VARCHAR(50),
    ADD COLUMN IF NOT EXISTS carga_horaria VARCHAR(50),
    
    -- Requisitos Detalhados
    ADD COLUMN IF NOT EXISTS requisitos_obrigatorios TEXT,
    ADD COLUMN IF NOT EXISTS requisitos_desejaveis TEXT,
    ADD COLUMN IF NOT EXISTS diferenciais TEXT;

-- Constraints rh_vagas
ALTER TABLE public.rh_vagas
DROP CONSTRAINT IF EXISTS rh_vagas_nivel_check;
ALTER TABLE public.rh_vagas
ADD CONSTRAINT rh_vagas_nivel_check CHECK (
    nivel_senioridade IN (
        'Estágio', 'Júnior', 'Pleno', 'Sênior', 'Especialista', 'Liderança'
    ) OR nivel_senioridade IS NULL
);

ALTER TABLE public.rh_vagas
DROP CONSTRAINT IF EXISTS rh_vagas_regime_check;
ALTER TABLE public.rh_vagas
ADD CONSTRAINT rh_vagas_regime_check CHECK (
    regime_trabalho IN ('Presencial', 'Híbrido', 'Remoto') OR regime_trabalho IS NULL
);

ALTER TABLE public.rh_vagas
DROP CONSTRAINT IF EXISTS rh_vagas_salario_check;
ALTER TABLE public.rh_vagas
ADD CONSTRAINT rh_vagas_salario_check CHECK (
    (faixa_salarial_min IS NULL AND faixa_salarial_max IS NULL) OR
    (faixa_salarial_max >= faixa_salarial_min)
);

-- Índices rh_vagas
CREATE INDEX IF NOT EXISTS idx_rh_vagas_nivel ON public.rh_vagas(nivel_senioridade);
CREATE INDEX IF NOT EXISTS idx_rh_vagas_regime ON public.rh_vagas(regime_trabalho);
CREATE INDEX IF NOT EXISTS idx_rh_vagas_salario_min ON public.rh_vagas(faixa_salarial_min);
CREATE INDEX IF NOT EXISTS idx_rh_vagas_salario_max ON public.rh_vagas(faixa_salarial_max);

COMMIT;

-- =====================================================================
-- VALIDAÇÃO (execute separadamente depois)
-- =====================================================================

-- Verificar colunas de rh_vagas
SELECT column_name, data_type 
FROM information_schema.columns 
WHERE table_name = 'rh_vagas' 
  AND column_name IN ('faixa_salarial_min', 'nivel_senioridade', 'regime_trabalho', 'carga_horaria')
ORDER BY column_name;

-- Deve retornar 4 linhas se deu certo!
