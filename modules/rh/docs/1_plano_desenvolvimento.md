1. Estrutura da Aplicação Atualizada (modules/rh)
A estrutura de pastas foi consolidada para refletir a modelagem de dados final, organizando as responsabilidades de forma clara e escalável, seguindo o padrão já existente no seu projeto.

modules/rh/
│
├── 📄 __init__.py                  # Registra todos os blueprints do módulo de RH
├── 📄 README.md                    # Documentação técnica e guia de uso do módulo de RH
│
├── 📁 recrutamento/                 # Sub-módulo para Recrutamento e Seleção
│   ├── __init__.py
│   ├── routes.py                  # Blueprint: recrutamento_bp (/rh/recrutamento)
│   ├── templates/recrutamento/
│   │   ├── portal_vagas.html      # (Público) Lista de vagas abertas
│   │   ├── detalhe_vaga.html      # (Público) Detalhes e formulário de aplicação da vaga
│   │   ├── gestao_vagas.html      # (Interno RH) Dashboard para criar, editar e gerenciar vagas (CRUD)
│   │   └── gestao_candidatos.html # (Interno RH) Kanban/Funil de candidatos por vaga
│   └── static/recrutamento/
│       ├── css/recrutamento.css
│       └── js/recrutamento.js
│
├── 📁 colaboradores/               # Sub-módulo para o "Coração do RH" - Gestão de Colaboradores
│   ├── __init__.py
│   ├── routes.py                  # Blueprint: colaboradores_bp (/rh/colaboradores)
│   ├── templates/colaboradores/
│   │   ├── lista_colaboradores.html # (Interno RH/Gestores) Tabela principal com filtros de busca
│   │   ├── perfil_colaborador.html  # (Interno RH/Gestores) "Dossiê" completo com dados e linha do tempo histórica
│   │   └── portal_colaborador.html  # (Visão do Colaborador) Acesso aos seus próprios dados e histórico
│   └── static/colaboradores/
│       ├── css/perfil_colaborador.css
│       └── js/colaboradores.js
│
├── 📁 desempenho/                  # Sub-módulo para Avaliações e Feedbacks
│   ├── __init__.py
│   ├── routes.py                  # Blueprint: desempenho_bp (/rh/desempenho)
│   ├── templates/desempenho/
│   │   ├── dashboard_avaliacoes.html # (Interno RH/Gestores) Painel para ciclos de avaliação
│   │   └── formulario_avaliacao.html # Tela para preenchimento da avaliação de um colaborador
│   └── static/desempenho/
│       ├── css/desempenho.css
│       └── js/desempenho.js
│
└── 📁 estrutura_org/               # Sub-módulo para gerenciar dados mestres (Cargos, Deptos)
    ├── __init__.py
    ├── routes.py                  # Blueprint: estrutura_org_bp (/rh/estrutura)
    ├── templates/estrutura_org/
    │   ├── gestao_cargos.html     # (Interno RH) CRUD de Cargos
    │   └── gestao_departamentos.html # (Interno RH) CRUD de Departamentos
    └── static/estrutura_org/
        ├── css/estrutura.css
        └── js/estrutura.js
2. DDL Completo para PostgreSQL
Este script contém tudo o que é necessário para criar o schema do módulo de RH no banco de dados.

2.1. Função e Trigger de Auditoria
Primeiro, criamos uma função genérica para atualizar timestamps. Isso garante que saibamos sempre quando um registro foi modificado pela última vez.

SQL

-- =====================================================================
-- FUNÇÃO DE AUDITORIA (TIMESTAMPS)
-- =====================================================================
-- Esta função será usada por triggers para atualizar automaticamente o
-- campo 'updated_at' em qualquer tabela que a utilize.
-- =====================================================================

CREATE OR REPLACE FUNCTION trigger_set_timestamp()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = NOW();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;
2.2. Tabelas de Estrutura Organizacional (Dados Mestres)
Estas tabelas armazenam informações que são usadas como base para os colaboradores, evitando redundância e garantindo consistência.

SQL

-- =====================================================================
-- TABELA: rh_cargos
-- DESCRIÇÃO: Cadastro central de todos os cargos existentes na empresa.
-- =====================================================================
CREATE TABLE rh_cargos (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    nome_cargo VARCHAR(255) NOT NULL UNIQUE,
    descricao TEXT,
    grupo_cargo VARCHAR(150),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE rh_cargos IS 'Armazena a lista de cargos oficiais da empresa, servindo como dado mestre.';
COMMENT ON COLUMN rh_cargos.nome_cargo IS 'Nome único do cargo (Ex: Analista de Importação Sênior).';
COMMENT ON COLUMN rh_cargos.grupo_cargo IS 'Agrupamento para relatórios (Ex: Operacional, Liderança, Administrativo).';

-- Trigger para atualizar 'updated_at'
CREATE TRIGGER set_timestamp
BEFORE UPDATE ON rh_cargos
FOR EACH ROW
EXECUTE FUNCTION trigger_set_timestamp();

-- =====================================================================
-- TABELA: rh_departamentos
-- DESCRIÇÃO: Cadastro de departamentos, áreas ou centros de custo.
-- =====================================================================
CREATE TABLE rh_departamentos (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    nome_departamento VARCHAR(255) NOT NULL UNIQUE,
    codigo_centro_custo VARCHAR(50) UNIQUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE rh_departamentos IS 'Armazena a lista de departamentos ou centros de custo da empresa.';

-- Trigger para atualizar 'updated_at'
CREATE TRIGGER set_timestamp
BEFORE UPDATE ON rh_departamentos
FOR EACH ROW
EXECUTE FUNCTION trigger_set_timestamp();

-- =====================================================================
-- TABELA: rh_empresas
-- DESCRIÇÃO: Se a Unique tiver múltiplas entidades (CNPJs), esta tabela as gerencia.
-- =====================================================================
CREATE TABLE rh_empresas (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    razao_social VARCHAR(255) NOT NULL,
    cnpj VARCHAR(18) NOT NULL UNIQUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE rh_empresas IS 'Gerencia as diferentes entidades legais (empresas com CNPJ) do grupo.';
2.3. Tabelas do Ciclo de Vida do Colaborador (Coração do Módulo)
Estas são as tabelas principais que gerenciam todo o fluxo de vida do colaborador.

SQL

-- =====================================================================
-- TABELA: rh_colaboradores
-- DESCRIÇÃO: Armazena os dados cadastrais principais e quase-estáticos de cada pessoa
-- que já foi ou é colaboradora da empresa. É o "dossiê" central.
-- =====================================================================
CREATE TABLE rh_colaboradores (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    -- IDs e Vínculos
    user_id UUID UNIQUE REFERENCES auth.users(id) ON DELETE SET NULL,
    matricula VARCHAR(20) UNIQUE,
    email_corporativo VARCHAR(255) UNIQUE,
    -- Dados Pessoais
    nome_completo VARCHAR(255) NOT NULL,
    nome_social VARCHAR(255),
    cpf VARCHAR(14) NOT NULL UNIQUE,
    data_nascimento DATE NOT NULL,
    genero VARCHAR(50),
    raca_cor VARCHAR(50),
    nacionalidade VARCHAR(100) DEFAULT 'Brasileira',
    -- Documentação
    rg VARCHAR(20),
    rg_orgao_emissor VARCHAR(20),
    rg_data_expedicao DATE,
    pis_pasep VARCHAR(20) UNIQUE,
    ctps_numero VARCHAR(20),
    ctps_serie VARCHAR(10),
    cnh_numero VARCHAR(20),
    cnh_categoria VARCHAR(5),
    -- Contato e Endereço
    telefones_jsonb JSONB,
    endereco_jsonb JSONB,
    -- Status Geral do Ciclo de Vida
    status VARCHAR(50) NOT NULL DEFAULT 'Ativo' CHECK (status IN ('Ativo', 'Inativo', 'Férias', 'Afastado')),
    data_admissao DATE NOT NULL,
    data_desligamento DATE,
    -- Metadados
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE rh_colaboradores IS 'Tabela central com os dados cadastrais de todos os colaboradores (ativos e inativos).';
COMMENT ON COLUMN rh_colaboradores.matricula IS 'Número de matrícula único do colaborador na empresa.';
COMMENT ON COLUMN rh_colaboradores.cpf IS 'CPF é o identificador único natural da pessoa, usado para evitar duplicidade e gerenciar recontratações.';
COMMENT ON COLUMN rh_colaboradores.status IS 'Status geral do colaborador na empresa (Ativo, Inativo, etc.).';
COMMENT ON COLUMN rh_colaboradores.data_admissao IS 'Data da última admissão do colaborador.';

-- Trigger para atualizar 'updated_at'
CREATE TRIGGER set_timestamp
BEFORE UPDATE ON rh_colaboradores
FOR EACH ROW
EXECUTE FUNCTION trigger_set_timestamp();

-- =====================================================================
-- TABELA: rh_historico_colaborador
-- DESCRIÇÃO: O coração do sistema. Cada linha é um evento na "linha do tempo" do
-- colaborador, garantindo um histórico imutável e auditável de todas as mudanças.
-- =====================================================================
CREATE TABLE rh_historico_colaborador (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    colaborador_id UUID NOT NULL REFERENCES rh_colaboradores(id) ON DELETE CASCADE,
    data_evento DATE NOT NULL,
    tipo_evento VARCHAR(50) NOT NULL CHECK (tipo_evento IN ('Admissão', 'Alteração Salarial', 'Promoção', 'Alteração de Cargo', 'Férias', 'Afastamento', 'Alteração Estrutural', 'Reajuste', 'Feedback', 'Demissão')),
    -- A "fotografia" da estrutura organizacional no momento do evento
    empresa_id UUID REFERENCES rh_empresas(id),
    departamento_id UUID REFERENCES rh_departamentos(id),
    cargo_id UUID REFERENCES rh_cargos(id),
    gestor_id UUID REFERENCES rh_colaboradores(id),
    -- A "fotografia" da remuneração e contrato no momento do evento
    salario_mensal NUMERIC(10, 2),
    tipo_contrato VARCHAR(100),
    modelo_trabalho VARCHAR(100),
    -- Detalhes e Auditoria
    descricao_e_motivos TEXT,
    dados_adicionais_jsonb JSONB,
    -- Responsável pela Ação
    responsavel_id UUID REFERENCES auth.users(id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE rh_historico_colaborador IS 'Registra cada evento significativo na carreira do colaborador, formando uma linha do tempo imutável.';
COMMENT ON COLUMN rh_historico_colaborador.tipo_evento IS 'Tipo do evento ocorrido (Ex: Admissão, Promoção, Demissão).';
COMMENT ON COLUMN rh_historico_colaborador.data_evento IS 'Data em que o evento se tornou efetivo.';
COMMENT ON COLUMN rh_historico_colaborador.gestor_id IS 'Indica quem era o gestor do colaborador na data do evento.';
COMMENT ON COLUMN rh_historico_colaborador.dados_adicionais_jsonb IS 'Campo flexível para auditoria, armazenando dados de "antes e depois" de uma mudança.';
2.4. Índices para Performance
Índices são cruciais para que as consultas em um sistema com muitos dados permaneçam rápidas. Eles funcionam como o índice de um livro, permitindo ao banco de dados encontrar a informação sem precisar ler a tabela inteira.

SQL

-- =====================================================================
-- ÍNDICES DE PERFORMANCE
-- =====================================================================

-- Índices na tabela de Colaboradores
CREATE INDEX idx_rh_colaboradores_status ON rh_colaboradores(status); -- Para filtrar rapidamente por colaboradores ativos/inativos.
CREATE INDEX idx_rh_colaboradores_nome ON rh_colaboradores USING GIN (to_tsvector('portuguese', nome_completo)); -- Para buscas textuais rápidas por nome.
CREATE INDEX idx_rh_colaboradores_email ON rh_colaboradores(email_corporativo); -- Para buscas por e-mail.

-- Índices na tabela de Histórico (MAIS IMPORTANTES)
CREATE INDEX idx_rh_historico_colaborador_id_data ON rh_historico_colaborador(colaborador_id, data_evento DESC); -- O índice MAIS IMPORTANTE: para buscar a linha do tempo de um colaborador de forma ultra-rápida.
CREATE INDEX idx_rh_historico_cargo_id ON rh_historico_colaborador(cargo_id); -- Para encontrar todos os colaboradores que já ocuparam um cargo.
CREATE INDEX idx_rh_historico_departamento_id ON rh_historico_colaborador(departamento_id); -- Para encontrar todos que já passaram por um departamento.
CREATE INDEX idx_rh_historico_gestor_id ON rh_historico_colaborador(gestor_id); -- Para encontrar rapidamente os liderados de um gestor.
CREATE INDEX idx_rh_historico_tipo_evento ON rh_historico_colaborador(tipo_evento); -- Para relatórios (ex: contar todas as 'Promoções' do ano).
3. Regras e Lógicas de Negócio Documentadas
Esta seção explica a lógica por trás do modelo e como ele deve ser utilizado pela aplicação.

Fonte da Verdade:

Cadastro (rh_colaboradores): Contém os dados que definem a pessoa. O CPF é a chave-mestra que garante que uma pessoa, mesmo que saia e volte, terá sempre um único registro cadastral.

Linha do Tempo (rh_historico_colaborador): Contém os dados que definem o contrato/vínculo da pessoa com a empresa em um determinado momento. Cada mudança gera um novo registro. A informação "atual" (cargo, salário, gestor) é sempre o registro mais recente (por data_evento) nesta tabela para um dado colaborador.

Fluxo de Admissão:

Quando um candidato é contratado, a aplicação deve:

Criar um registro em rh_colaboradores com os dados pessoais.

Criar o primeiro registro em rh_historico_colaborador com tipo_evento = 'Admissão', preenchendo todas as informações daquele momento (cargo, salário, gestor, etc.).

Fluxo de Alteração (Promoção, Reajuste, Mudança de Área):

A aplicação NÃO deve alterar o registro de histórico anterior.

Ela deve criar um NOVO registro em rh_historico_colaborador, copiando a maioria das informações do registro anterior, mas atualizando os campos que mudaram (ex: cargo_id, salario_mensal).

O campo dados_adicionais_jsonb DEVE ser usado para armazenar o estado anterior da mudança para fins de auditoria. Ex: {"salario_anterior": 5000, "cargo_anterior_id": "uuid-do-cargo-antigo"}.

Fluxo de Desligamento:

A aplicação deve:

Atualizar o registro em rh_colaboradores, setando status = 'Inativo' e preenchendo data_desligamento.

Criar o último registro em rh_historico_colaborador com tipo_evento = 'Demissão'.

Fluxo de Recontratação:

Ao iniciar uma admissão para um CPF que já existe em rh_colaboradores com status 'Inativo', a aplicação deve:

Atualizar o registro existente em rh_colaboradores, mudando o status para 'Ativo', atualizando a data_admissao para a nova data e setando data_desligamento como NULL.

Seguir o fluxo normal de admissão, criando um novo evento de 'Admissão' na tabela de histórico, que marcará o início do segundo ciclo de vida da pessoa na empresa.

Com esta estrutura e regras, você terá um sistema de RH robusto, auditável e preparado para o crescimento, resolvendo as dores de falta de histórico, inconsistência de dados e processos manuais que foram levantadas na reunião.