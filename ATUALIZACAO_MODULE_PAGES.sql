-- =====================================================
-- Atualização da tabela module_pages - 23/10/2025 08:43
-- =====================================================
-- Este script atualiza a tabela de páginas de perfis com todas as rotas
-- da aplicação mapeadas corretamente

-- PASSO 1: Limpar registros antigos (OPCIONAL - comente se quiser manter histórico)
-- DELETE FROM "public"."module_pages" WHERE "is_active" = true;

-- PASSO 2: Inserir novas páginas mapeadas
INSERT INTO "public"."module_pages" ("id", "module_id", "page_code", "page_name", "description", "route_path", "icon_class", "sort_order", "is_active", "requires_special_permission", "created_at", "updated_at") 
VALUES ('0bac3942-04e7-4853-b3b6-54583ea40d17', 'imp', 'dashboard_executivo', 'Dashboard Executivo', 'Página do módulo imp', '/importacoes/dashboard-executivo', 'mdi-chart-pie', 1, true, false, NOW(), NOW());

INSERT INTO "public"."module_pages" ("id", "module_id", "page_code", "page_name", "description", "route_path", "icon_class", "sort_order", "is_active", "requires_special_permission", "created_at", "updated_at") 
VALUES ('67881e0d-51c7-4523-9614-a41970d543cc', 'imp', 'dashboard_resumido', 'Dashboard Importações', 'Página do módulo imp', '/importacoes/dashboard-resumido', 'mdi-chart-bar', 2, true, false, NOW(), NOW());

INSERT INTO "public"."module_pages" ("id", "module_id", "page_code", "page_name", "description", "route_path", "icon_class", "sort_order", "is_active", "requires_special_permission", "created_at", "updated_at") 
VALUES ('a24beed5-92ef-4fcc-812b-687eab5eb73c', 'imp', 'documentos', 'Conferência Documental', 'Página do módulo imp', '/importacoes/documentos', 'mdi-file-document', 3, true, false, NOW(), NOW());

INSERT INTO "public"."module_pages" ("id", "module_id", "page_code", "page_name", "description", "route_path", "icon_class", "sort_order", "is_active", "requires_special_permission", "created_at", "updated_at") 
VALUES ('c80d892d-2ecd-4811-b180-d667d2f1847a', 'imp', 'relatorio', 'Exportação de Relatórios', 'Página do módulo imp', '/importacoes/relatorios', 'mdi-file-chart', 4, true, false, NOW(), NOW());

INSERT INTO "public"."module_pages" ("id", "module_id", "page_code", "page_name", "description", "route_path", "icon_class", "sort_order", "is_active", "requires_special_permission", "created_at", "updated_at") 
VALUES ('c3d31a3e-f056-4769-bb5d-515a8c67f2c8', 'imp', 'agente', 'Agente UniQ', 'Página do módulo imp', '/importacoes/agente', 'mdi-robot', 5, true, false, NOW(), NOW());

INSERT INTO "public"."module_pages" ("id", "module_id", "page_code", "page_name", "description", "route_path", "icon_class", "sort_order", "is_active", "requires_special_permission", "created_at", "updated_at") 
VALUES ('7243f007-14e0-4303-b085-54d4680e93ef', 'imp', 'materiais', 'Gestão de Materiais', 'Página do módulo imp', '/importacoes/materiais', 'mdi-package', 6, true, false, NOW(), NOW());

INSERT INTO "public"."module_pages" ("id", "module_id", "page_code", "page_name", "description", "route_path", "icon_class", "sort_order", "is_active", "requires_special_permission", "created_at", "updated_at") 
VALUES ('38d9781c-1515-4d8d-afc4-55fd5878fe28', 'imp', 'dashboard_operacional', 'Dashboard Operacional', 'Página do módulo imp', '/importacoes/dashboard-operacional', 'mdi-chart-box', 7, true, false, NOW(), NOW());

INSERT INTO "public"."module_pages" ("id", "module_id", "page_code", "page_name", "description", "route_path", "icon_class", "sort_order", "is_active", "requires_special_permission", "created_at", "updated_at") 
VALUES ('880c13f0-2afd-4982-9c94-9a6dcab11aca', 'fin', 'fin_dashboard_executivo', 'Dashboard Executivo', 'Página do módulo fin', '/financeiro/dashboard-executivo', 'mdi-chart-pie', 1, true, false, NOW(), NOW());

INSERT INTO "public"."module_pages" ("id", "module_id", "page_code", "page_name", "description", "route_path", "icon_class", "sort_order", "is_active", "requires_special_permission", "created_at", "updated_at") 
VALUES ('ad555b57-103e-4ebe-a90f-911ad92fdef0', 'fin', 'fluxo_caixa', 'Fluxo de Caixa', 'Página do módulo fin', '/financeiro/fluxo-de-caixa', 'mdi-cash-flow', 2, true, false, NOW(), NOW());

INSERT INTO "public"."module_pages" ("id", "module_id", "page_code", "page_name", "description", "route_path", "icon_class", "sort_order", "is_active", "requires_special_permission", "created_at", "updated_at") 
VALUES ('0adc1136-139a-4177-9749-046193d31194', 'fin', 'despesas', 'Despesas', 'Página do módulo fin', '/financeiro/despesas', 'mdi-receipt', 3, true, false, NOW(), NOW());

INSERT INTO "public"."module_pages" ("id", "module_id", "page_code", "page_name", "description", "route_path", "icon_class", "sort_order", "is_active", "requires_special_permission", "created_at", "updated_at") 
VALUES ('c9c6f22a-ba86-402c-963c-99aaa1ff1655', 'fin', 'faturamento', 'Faturamento', 'Página do módulo fin', '/financeiro/faturamento', 'mdi-file-invoice-dollar', 4, true, false, NOW(), NOW());

INSERT INTO "public"."module_pages" ("id", "module_id", "page_code", "page_name", "description", "route_path", "icon_class", "sort_order", "is_active", "requires_special_permission", "created_at", "updated_at") 
VALUES ('61a2cef9-93d7-41fb-950b-fa82263109df', 'fin', 'conciliacao', 'Conciliação Bancária', 'Página do módulo fin', '/financeiro/conciliacao-lancamentos', 'mdi-checkbox-marked-circle', 5, true, false, NOW(), NOW());

INSERT INTO "public"."module_pages" ("id", "module_id", "page_code", "page_name", "description", "route_path", "icon_class", "sort_order", "is_active", "requires_special_permission", "created_at", "updated_at") 
VALUES ('28959a42-3c47-401b-bb5d-d6f39977a74b', 'fin', 'categorizacao', 'Categorização de Clientes', 'Página do módulo fin', '/financeiro/categorizacao-clientes', 'mdi-tag-multiple', 6, true, false, NOW(), NOW());

INSERT INTO "public"."module_pages" ("id", "module_id", "page_code", "page_name", "description", "route_path", "icon_class", "sort_order", "is_active", "requires_special_permission", "created_at", "updated_at") 
VALUES ('ea24fc81-3cce-4cf4-a468-a868fadba886', 'fin', 'projecoes', 'Projeções e Metas', 'Página do módulo fin', '/financeiro/projecoes-metas', 'mdi-chart-line', 7, true, false, NOW(), NOW());

INSERT INTO "public"."module_pages" ("id", "module_id", "page_code", "page_name", "description", "route_path", "icon_class", "sort_order", "is_active", "requires_special_permission", "created_at", "updated_at") 
VALUES ('0c9259e9-d492-41b4-812c-ededbcb1e454', 'fin', 'export_bases', 'Exportação de Bases', 'Página do módulo fin', '/financeiro/export-bases', 'mdi-database-export', 8, true, false, NOW(), NOW());

INSERT INTO "public"."module_pages" ("id", "module_id", "page_code", "page_name", "description", "route_path", "icon_class", "sort_order", "is_active", "requires_special_permission", "created_at", "updated_at") 
VALUES ('58fc1d8b-74d6-40f9-89e1-18a5ed688f02', 'rh', 'dashboard', 'Dashboard Executivo RH', 'Página do módulo rh', '/rh/dashboard', 'mdi-chart-box-outline', 1, true, false, NOW(), NOW());

INSERT INTO "public"."module_pages" ("id", "module_id", "page_code", "page_name", "description", "route_path", "icon_class", "sort_order", "is_active", "requires_special_permission", "created_at", "updated_at") 
VALUES ('0c0a6be2-3b45-4979-b87f-dea3c755cbeb', 'rh', 'colaboradores', 'Gestão de Colaboradores', 'Página do módulo rh', '/rh/colaboradores', 'mdi-account-multiple', 2, true, false, NOW(), NOW());

INSERT INTO "public"."module_pages" ("id", "module_id", "page_code", "page_name", "description", "route_path", "icon_class", "sort_order", "is_active", "requires_special_permission", "created_at", "updated_at") 
VALUES ('64569280-f9d4-4116-b2a4-c5dc9f479e65', 'rh', 'estrutura_cargos', 'Cargos', 'Página do módulo rh', '/rh/cargos', 'mdi-briefcase', 3, true, false, NOW(), NOW());

INSERT INTO "public"."module_pages" ("id", "module_id", "page_code", "page_name", "description", "route_path", "icon_class", "sort_order", "is_active", "requires_special_permission", "created_at", "updated_at") 
VALUES ('b860b6ae-f78e-4e90-9e16-49ca7e04c437', 'rh', 'estrutura_departamentos', 'Departamentos', 'Página do módulo rh', '/rh/departamentos', 'mdi-office-building', 4, true, false, NOW(), NOW());

INSERT INTO "public"."module_pages" ("id", "module_id", "page_code", "page_name", "description", "route_path", "icon_class", "sort_order", "is_active", "requires_special_permission", "created_at", "updated_at") 
VALUES ('4d8aa3a7-fd3e-416a-ab1a-b714d029c4a6', 'rh', 'recrutamento', 'Recrutamento e Seleção', 'Página do módulo rh', '/rh/recrutamento', 'mdi-account-search', 5, true, false, NOW(), NOW());

INSERT INTO "public"."module_pages" ("id", "module_id", "page_code", "page_name", "description", "route_path", "icon_class", "sort_order", "is_active", "requires_special_permission", "created_at", "updated_at") 
VALUES ('78f39626-585f-4821-9296-80d1058d6f57', 'rh', 'desempenho', 'Avaliação de Desempenho', 'Página do módulo rh', '/rh/avaliacao-desempenho', 'mdi-star', 6, true, false, NOW(), NOW());

INSERT INTO "public"."module_pages" ("id", "module_id", "page_code", "page_name", "description", "route_path", "icon_class", "sort_order", "is_active", "requires_special_permission", "created_at", "updated_at") 
VALUES ('1294034c-7b75-43e2-9c59-8005617b3d35', 'rh', 'carreiras', 'Gestão de Carreiras', 'Página do módulo rh', '/rh/carreiras', 'mdi-timeline-text', 7, true, false, NOW(), NOW());

INSERT INTO "public"."module_pages" ("id", "module_id", "page_code", "page_name", "description", "route_path", "icon_class", "sort_order", "is_active", "requires_special_permission", "created_at", "updated_at") 
VALUES ('f73b1835-9b30-491b-a565-6d632ac62eb9', 'rh', 'dashboard_analitico', 'Dashboard Analítico', 'Página do módulo rh', '/rh/dashboard-analitico', 'mdi-chart-scatter', 8, true, false, NOW(), NOW());


-- PASSO 3: Verificar integridade dos dados
SELECT COUNT(*) as total_paginas, module_id, COUNT(DISTINCT module_id) as modulos
FROM "public"."module_pages"
WHERE "is_active" = true
GROUP BY module_id;

-- PASSO 4: Listar todas as páginas cadastradas
SELECT module_id, page_code, page_name, route_path, sort_order, is_active
FROM "public"."module_pages"
WHERE "is_active" = true
ORDER BY module_id, sort_order;
