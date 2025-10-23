-- ============================================================
-- SQL CORRIGIDO: Atualização da tabela module_pages
-- ============================================================
-- IMPORTANTE: Este SQL corrige os page_codes para coincidir
-- com os decorators @perfil_required usados nas rotas
-- ============================================================

-- Deletar registros existentes (se houver) para evitar duplicatas
DELETE FROM "public"."module_pages" 
WHERE "page_code" IN (
    -- Importações
    'dashboard_executivo', 'dashboard_operacional', 'dashboard_resumido', 
    'documentos', 'relatorio', 'agente', 'materiais', 'ajuste_status',
    -- Financeiro
    'fluxo_caixa', 'despesas', 'faturamento', 'conciliacao_lancamentos', 
    'categorizacao', 'projecoes', 'export_bases',
    -- RH
    'dashboard', 'colaboradores', 'estrutura_cargos', 'estrutura_departamentos', 
    'recrutamento', 'desempenho', 'carreiras', 'dashboard_analitico'
);

-- ============================================================
-- MÓDULO IMPORTAÇÕES (imp)
-- ============================================================

INSERT INTO "public"."module_pages" 
("id", "module_id", "page_code", "page_name", "description", "route_path", "icon_class", "sort_order", "is_active", "requires_special_permission", "created_at", "updated_at") 
VALUES (
  gen_random_uuid(), 
  'imp', 
  'dashboard_executivo', 
  'Dashboard Executivo',
  'Visão executiva completa das importações com KPIs e análises estratégicas',
  '/importacoes/dashboard-executivo',
  'mdi-view-dashboard',
  1,
  true,
  false,
  NOW(),
  NOW()
);

INSERT INTO "public"."module_pages" 
("id", "module_id", "page_code", "page_name", "description", "route_path", "icon_class", "sort_order", "is_active", "requires_special_permission", "created_at", "updated_at") 
VALUES (
  gen_random_uuid(), 
  'imp', 
  'dashboard_operacional', 
  'Dashboard Operacional',
  'Visão operacional detalhada com status e processos em andamento',
  '/importacoes/dashboard-operacional',
  'mdi-clipboard-text',
  2,
  true,
  false,
  NOW(),
  NOW()
);

INSERT INTO "public"."module_pages" 
("id", "module_id", "page_code", "page_name", "description", "route_path", "icon_class", "sort_order", "is_active", "requires_special_permission", "created_at", "updated_at") 
VALUES (
  gen_random_uuid(), 
  'imp', 
  'dashboard_resumido', 
  'Dashboard Resumido',
  'Visão resumida das principais métricas de importação',
  '/dash-importacoes-resumido',
  'mdi-chart-box',
  3,
  true,
  false,
  NOW(),
  NOW()
);

INSERT INTO "public"."module_pages" 
("id", "module_id", "page_code", "page_name", "description", "route_path", "icon_class", "sort_order", "is_active", "requires_special_permission", "created_at", "updated_at") 
VALUES (
  gen_random_uuid(), 
  'imp', 
  'documentos', 
  'Conferência Documental',
  'Sistema de conferência e validação de documentos de importação',
  '/conferencia/',
  'mdi-file-document-check',
  4,
  true,
  false,
  NOW(),
  NOW()
);

INSERT INTO "public"."module_pages" 
("id", "module_id", "page_code", "page_name", "description", "route_path", "icon_class", "sort_order", "is_active", "requires_special_permission", "created_at", "updated_at") 
VALUES (
  gen_random_uuid(), 
  'imp', 
  'relatorio', 
  'Exportação de Relatórios',
  'Geração e exportação de relatórios de importação em diversos formatos',
  '/export-relatorios',
  'mdi-file-export',
  5,
  true,
  false,
  NOW(),
  NOW()
);

INSERT INTO "public"."module_pages" 
("id", "module_id", "page_code", "page_name", "description", "route_path", "icon_class", "sort_order", "is_active", "requires_special_permission", "created_at", "updated_at") 
VALUES (
  gen_random_uuid(), 
  'imp', 
  'agente', 
  'Agente UniQ',
  'Assistente virtual inteligente para processamento de documentos',
  '/agente',
  'mdi-robot',
  6,
  true,
  false,
  NOW(),
  NOW()
);

INSERT INTO "public"."module_pages" 
("id", "module_id", "page_code", "page_name", "description", "route_path", "icon_class", "sort_order", "is_active", "requires_special_permission", "created_at", "updated_at") 
VALUES (
  gen_random_uuid(), 
  'imp', 
  'materiais', 
  'Análise de Materiais',
  'Análise e categorização inteligente de materiais importados',
  '/materiais',
  'mdi-package-variant',
  7,
  true,
  false,
  NOW(),
  NOW()
);

INSERT INTO "public"."module_pages" 
("id", "module_id", "page_code", "page_name", "description", "route_path", "icon_class", "sort_order", "is_active", "requires_special_permission", "created_at", "updated_at") 
VALUES (
  gen_random_uuid(), 
  'imp', 
  'ajuste_status', 
  'Ajuste de Status',
  'Ajuste manual de status das importações',
  '/ajuste-status',
  'mdi-pencil-box',
  8,
  true,
  false,
  NOW(),
  NOW()
);

-- ============================================================
-- MÓDULO FINANCEIRO (fin)
-- ============================================================

INSERT INTO "public"."module_pages" 
("id", "module_id", "page_code", "page_name", "description", "route_path", "icon_class", "sort_order", "is_active", "requires_special_permission", "created_at", "updated_at") 
VALUES (
  gen_random_uuid(), 
  'fin', 
  'dashboard_executivo', 
  'Dashboard Executivo',
  'Visão executiva completa das finanças com KPIs e indicadores estratégicos',
  '/financeiro/dashboard-executivo',
  'mdi-finance',
  1,
  true,
  false,
  NOW(),
  NOW()
);

INSERT INTO "public"."module_pages" 
("id", "module_id", "page_code", "page_name", "description", "route_path", "icon_class", "sort_order", "is_active", "requires_special_permission", "created_at", "updated_at") 
VALUES (
  gen_random_uuid(), 
  'fin', 
  'fluxo_caixa', 
  'Fluxo de Caixa',
  'Gestão e análise do fluxo de caixa da empresa',
  '/financeiro/fluxo-de-caixa',
  'mdi-cash-multiple',
  2,
  true,
  false,
  NOW(),
  NOW()
);

INSERT INTO "public"."module_pages" 
("id", "module_id", "page_code", "page_name", "description", "route_path", "icon_class", "sort_order", "is_active", "requires_special_permission", "created_at", "updated_at") 
VALUES (
  gen_random_uuid(), 
  'fin', 
  'despesas', 
  'Gestão de Despesas',
  'Controle e análise de despesas por categoria e período',
  '/financeiro/despesas',
  'mdi-credit-card',
  3,
  true,
  false,
  NOW(),
  NOW()
);

INSERT INTO "public"."module_pages" 
("id", "module_id", "page_code", "page_name", "description", "route_path", "icon_class", "sort_order", "is_active", "requires_special_permission", "created_at", "updated_at") 
VALUES (
  gen_random_uuid(), 
  'fin', 
  'faturamento', 
  'Gestão de Faturamento',
  'Controle e análise de faturamento por cliente e período',
  '/financeiro/faturamento',
  'mdi-currency-usd',
  4,
  true,
  false,
  NOW(),
  NOW()
);

INSERT INTO "public"."module_pages" 
("id", "module_id", "page_code", "page_name", "description", "route_path", "icon_class", "sort_order", "is_active", "requires_special_permission", "created_at", "updated_at") 
VALUES (
  gen_random_uuid(), 
  'fin', 
  'conciliacao_lancamentos', 
  'Conciliação Bancária',
  'Conciliação automatizada de lançamentos bancários com IA',
  '/financeiro/conciliacao-lancamentos',
  'mdi-bank-check',
  5,
  true,
  false,
  NOW(),
  NOW()
);

INSERT INTO "public"."module_pages" 
("id", "module_id", "page_code", "page_name", "description", "route_path", "icon_class", "sort_order", "is_active", "requires_special_permission", "created_at", "updated_at") 
VALUES (
  gen_random_uuid(), 
  'fin', 
  'categorizacao', 
  'Categorização de Clientes',
  'Sistema de categorização inteligente de clientes',
  '/financeiro/categorizacao-clientes',
  'mdi-tag-multiple',
  6,
  true,
  false,
  NOW(),
  NOW()
);

INSERT INTO "public"."module_pages" 
("id", "module_id", "page_code", "page_name", "description", "route_path", "icon_class", "sort_order", "is_active", "requires_special_permission", "created_at", "updated_at") 
VALUES (
  gen_random_uuid(), 
  'fin', 
  'projecoes', 
  'Projeções e Metas',
  'Projeções financeiras e acompanhamento de metas',
  '/financeiro/projecoes-metas',
  'mdi-chart-line',
  7,
  true,
  false,
  NOW(),
  NOW()
);

INSERT INTO "public"."module_pages" 
("id", "module_id", "page_code", "page_name", "description", "route_path", "icon_class", "sort_order", "is_active", "requires_special_permission", "created_at", "updated_at") 
VALUES (
  gen_random_uuid(), 
  'fin', 
  'export_bases', 
  'Exportação de Bases',
  'Exportação de dados financeiros em diversos formatos',
  '/financeiro/export-bases',
  'mdi-database-export',
  8,
  true,
  false,
  NOW(),
  NOW()
);

-- ============================================================
-- MÓDULO RH (rh)
-- ============================================================

INSERT INTO "public"."module_pages" 
("id", "module_id", "page_code", "page_name", "description", "route_path", "icon_class", "sort_order", "is_active", "requires_special_permission", "created_at", "updated_at") 
VALUES (
  gen_random_uuid(), 
  'rh', 
  'dashboard', 
  'Dashboard Executivo',
  'Visão executiva completa de Recursos Humanos com KPIs principais',
  '/rh/dashboard',
  'mdi-account-group',
  1,
  true,
  false,
  NOW(),
  NOW()
);

INSERT INTO "public"."module_pages" 
("id", "module_id", "page_code", "page_name", "description", "route_path", "icon_class", "sort_order", "is_active", "requires_special_permission", "created_at", "updated_at") 
VALUES (
  gen_random_uuid(), 
  'rh', 
  'colaboradores', 
  'Gestão de Colaboradores',
  'Cadastro e gestão completa de colaboradores',
  '/rh/colaboradores',
  'mdi-account-multiple',
  2,
  true,
  false,
  NOW(),
  NOW()
);

INSERT INTO "public"."module_pages" 
("id", "module_id", "page_code", "page_name", "description", "route_path", "icon_class", "sort_order", "is_active", "requires_special_permission", "created_at", "updated_at") 
VALUES (
  gen_random_uuid(), 
  'rh', 
  'estrutura_cargos', 
  'Estrutura de Cargos',
  'Definição e gestão da estrutura de cargos da empresa',
  '/rh/estrutura/cargos',
  'mdi-briefcase',
  3,
  true,
  false,
  NOW(),
  NOW()
);

INSERT INTO "public"."module_pages" 
("id", "module_id", "page_code", "page_name", "description", "route_path", "icon_class", "sort_order", "is_active", "requires_special_permission", "created_at", "updated_at") 
VALUES (
  gen_random_uuid(), 
  'rh', 
  'estrutura_departamentos', 
  'Estrutura de Departamentos',
  'Definição e gestão da estrutura organizacional por departamentos',
  '/rh/estrutura/departamentos',
  'mdi-sitemap',
  4,
  true,
  false,
  NOW(),
  NOW()
);

INSERT INTO "public"."module_pages" 
("id", "module_id", "page_code", "page_name", "description", "route_path", "icon_class", "sort_order", "is_active", "requires_special_permission", "created_at", "updated_at") 
VALUES (
  gen_random_uuid(), 
  'rh', 
  'recrutamento', 
  'Recrutamento e Seleção',
  'Gestão de processos seletivos e candidatos',
  '/rh/recrutamento',
  'mdi-account-search',
  5,
  true,
  false,
  NOW(),
  NOW()
);

INSERT INTO "public"."module_pages" 
("id", "module_id", "page_code", "page_name", "description", "route_path", "icon_class", "sort_order", "is_active", "requires_special_permission", "created_at", "updated_at") 
VALUES (
  gen_random_uuid(), 
  'rh', 
  'desempenho', 
  'Avaliações de Desempenho',
  'Sistema de avaliação de desempenho de colaboradores',
  '/rh/desempenho',
  'mdi-chart-box',
  6,
  true,
  false,
  NOW(),
  NOW()
);

INSERT INTO "public"."module_pages" 
("id", "module_id", "page_code", "page_name", "description", "route_path", "icon_class", "sort_order", "is_active", "requires_special_permission", "created_at", "updated_at") 
VALUES (
  gen_random_uuid(), 
  'rh', 
  'carreiras', 
  'Plano de Carreiras',
  'Gestão de planos de carreira e desenvolvimento profissional',
  '/carreiras',
  'mdi-stairs-up',
  7,
  true,
  false,
  NOW(),
  NOW()
);

INSERT INTO "public"."module_pages" 
("id", "module_id", "page_code", "page_name", "description", "route_path", "icon_class", "sort_order", "is_active", "requires_special_permission", "created_at", "updated_at") 
VALUES (
  gen_random_uuid(), 
  'rh', 
  'dashboard_analitico', 
  'Dashboard Analítico',
  'Análises avançadas e inteligência de dados de RH',
  '/rh/dashboard-analitico',
  'mdi-google-analytics',
  8,
  true,
  false,
  NOW(),
  NOW()
);

-- ============================================================
-- VERIFICAÇÃO: Consultar páginas inseridas
-- ============================================================
SELECT module_id, page_code, page_name, route_path, sort_order
FROM "public"."module_pages"
ORDER BY module_id, sort_order;
