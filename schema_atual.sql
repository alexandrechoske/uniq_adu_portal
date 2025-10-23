-- WARNING: This schema is for context only and is not meant to be run.
-- Table order and constraints may not be valid for execution.

CREATE TABLE public.DANGER_TABLE_MANUTENCAO (
  id character varying NOT NULL DEFAULT '1'::character varying,
  manutencao boolean NOT NULL DEFAULT false,
  mensagem_customizada text,
  data_inicio timestamp without time zone DEFAULT now(),
  data_prevista_fim timestamp without time zone,
  updated_at timestamp without time zone DEFAULT now(),
  updated_by text,
  CONSTRAINT DANGER_TABLE_MANUTENCAO_pkey PRIMARY KEY (id)
);
CREATE TABLE public.access_logs (
  id uuid NOT NULL DEFAULT gen_random_uuid(),
  user_id uuid,
  user_email character varying,
  user_name character varying,
  user_role character varying,
  action_type character varying NOT NULL,
  page_url character varying,
  page_name character varying,
  module_name character varying,
  ip_address inet,
  user_agent text,
  browser character varying,
  device_type character varying,
  platform character varying,
  session_id character varying,
  session_duration integer,
  country character varying,
  city character varying,
  timezone character varying,
  success boolean DEFAULT true,
  error_message text,
  response_time integer,
  http_status integer,
  created_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP,
  created_at_br timestamp without time zone DEFAULT (CURRENT_TIMESTAMP AT TIME ZONE 'America/Sao_Paulo'::text),
  CONSTRAINT access_logs_pkey PRIMARY KEY (id),
  CONSTRAINT access_logs_user_id_fkey FOREIGN KEY (user_id) REFERENCES auth.users(id)
);
CREATE TABLE public.agent_interaction_logs (
  id uuid NOT NULL DEFAULT gen_random_uuid(),
  user_id uuid,
  whatsapp_number character varying NOT NULL,
  user_name character varying,
  push_name character varying,
  empresa_nome character varying,
  cnpjs_consultados jsonb,
  total_cnpjs integer DEFAULT 0,
  user_message text NOT NULL,
  message_type character varying,
  conversation_context jsonb,
  agent_response text,
  response_type character varying,
  total_processos_encontrados integer DEFAULT 0,
  empresas_encontradas integer DEFAULT 0,
  status_distribuicao jsonb,
  whatsapp_instance character varying,
  instance_id uuid,
  execution_mode character varying,
  webhook_source character varying,
  response_time_ms integer,
  edge_function_calls integer DEFAULT 0,
  message_timestamp timestamp with time zone,
  processed_at timestamp with time zone DEFAULT now(),
  session_id character varying,
  is_successful boolean DEFAULT true,
  error_message text,
  created_at timestamp with time zone DEFAULT now(),
  updated_at timestamp with time zone DEFAULT now(),
  agent_response_at timestamp with time zone,
  CONSTRAINT agent_interaction_logs_pkey PRIMARY KEY (id),
  CONSTRAINT agent_interaction_logs_user_id_fkey FOREIGN KEY (user_id) REFERENCES auth.users(id),
  CONSTRAINT agent_interaction_logs_user_id_fkey1 FOREIGN KEY (user_id) REFERENCES public.users(id)
);
CREATE TABLE public.cad_clientes_sistema (
  id integer NOT NULL DEFAULT nextval('cad_clientes_sistema_id_seq'::regclass),
  nome_cliente text NOT NULL,
  cnpjs ARRAY NOT NULL DEFAULT '{}'::text[],
  logo_url text,
  ativo boolean NOT NULL DEFAULT true,
  created_at timestamp with time zone NOT NULL DEFAULT now(),
  updated_at timestamp with time zone NOT NULL DEFAULT now(),
  CONSTRAINT cad_clientes_sistema_pkey PRIMARY KEY (id)
);
CREATE TABLE public.cad_materiais (
  id bigint NOT NULL DEFAULT nextval('materiais_id_seq'::regclass),
  nome_normalizado text NOT NULL UNIQUE,
  icone_url text,
  created_at timestamp with time zone NOT NULL DEFAULT now(),
  CONSTRAINT cad_materiais_pkey PRIMARY KEY (id)
);
CREATE TABLE public.chats_new (
  id bigint GENERATED ALWAYS AS IDENTITY NOT NULL,
  created_at timestamp with time zone NOT NULL DEFAULT now(),
  remotejID text,
  chatID text,
  status text,
  ultimaAtividade text,
  ultimaMensagem text,
  CONSTRAINT chats_new_pkey PRIMARY KEY (id)
);
CREATE TABLE public.clientes_agentes (
  id bigint GENERATED ALWAYS AS IDENTITY NOT NULL,
  created_at timestamp with time zone NOT NULL DEFAULT now(),
  empresa ARRAY,
  aceite_termos boolean,
  user_id uuid,
  usuario_ativo boolean,
  nome text,
  numero ARRAY,
  updated_at timestamp with time zone,
  CONSTRAINT clientes_agentes_pkey PRIMARY KEY (id),
  CONSTRAINT clientes_agentes_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id)
);
CREATE TABLE public.conferencia_jobs (
  id uuid NOT NULL,
  created_at timestamp with time zone DEFAULT now(),
  file_name text,
  duration_ms integer,
  lexoid_mode text,
  invoice_number text,
  incoterm text,
  status text,
  total_items_sum_norm numeric,
  invoice_total_declared_norm numeric,
  difference_norm numeric,
  total_erros_criticos integer,
  total_alertas integer,
  llm_error text,
  raw_json text,
  year_month text,
  user_Id text,
  CONSTRAINT conferencia_jobs_pkey PRIMARY KEY (id)
);
CREATE TABLE public.conferencia_prompt (
  id bigint GENERATED ALWAYS AS IDENTITY NOT NULL,
  created_at timestamp with time zone NOT NULL DEFAULT now(),
  prompt text,
  tipo text,
  CONSTRAINT conferencia_prompt_pkey PRIMARY KEY (id)
);
CREATE TABLE public.documentos_processos (
  id uuid NOT NULL DEFAULT gen_random_uuid(),
  ref_unique character varying NOT NULL,
  nome_original character varying NOT NULL,
  nome_exibicao character varying NOT NULL,
  extensao character varying NOT NULL,
  tamanho_bytes bigint NOT NULL,
  mime_type character varying NOT NULL,
  storage_path text NOT NULL UNIQUE,
  storage_bucket character varying NOT NULL DEFAULT 'processos-documentos'::character varying,
  usuario_upload_id uuid,
  usuario_upload_email character varying NOT NULL,
  data_upload timestamp with time zone DEFAULT now(),
  data_atualizacao timestamp with time zone DEFAULT now(),
  visivel_cliente boolean DEFAULT true,
  ativo boolean DEFAULT true,
  descricao text,
  tags ARRAY,
  versao integer DEFAULT 1,
  CONSTRAINT documentos_processos_pkey PRIMARY KEY (id),
  CONSTRAINT fk_documentos_ref_unique FOREIGN KEY (ref_unique) REFERENCES public.importacoes_processos_aberta(ref_unique)
);
CREATE TABLE public.estrutura_empresa_controladora (
  id uuid NOT NULL DEFAULT gen_random_uuid(),
  nome character varying NOT NULL,
  CONSTRAINT estrutura_empresa_controladora_pkey PRIMARY KEY (id)
);
CREATE TABLE public.fin_clientes_mapeamento (
  nome_original text NOT NULL,
  nome_padronizado text,
  created_at timestamp with time zone DEFAULT now(),
  updated_at timestamp with time zone DEFAULT now(),
  CONSTRAINT fin_clientes_mapeamento_pkey PRIMARY KEY (nome_original)
);
CREATE TABLE public.fin_conciliacao_movimentos (
  id bigint GENERATED ALWAYS AS IDENTITY NOT NULL,
  data_lancamento date NOT NULL,
  nome_banco text,
  numero_conta text,
  tipo_lancamento USER-DEFINED,
  valor numeric,
  descricao text,
  ref_unique text,
  status USER-DEFINED NOT NULL DEFAULT 'PENDENTE'::status_conciliacao,
  id_conciliacao uuid,
  data_extracao timestamp with time zone NOT NULL DEFAULT now(),
  id_usuario_conciliou uuid,
  data_conciliacao timestamp with time zone,
  empresa text,
  CONSTRAINT fin_conciliacao_movimentos_pkey PRIMARY KEY (id),
  CONSTRAINT fin_conciliacao_movimentos_id_usuario_conciliou_fkey FOREIGN KEY (id_usuario_conciliou) REFERENCES auth.users(id)
);
CREATE TABLE public.fin_despesa_anual (
  id bigint NOT NULL DEFAULT nextval('fin_despesa_anual_id_seq'::regclass),
  data date NOT NULL,
  categoria text,
  classe text,
  codigo text,
  descricao text,
  valor numeric,
  origem_dados text DEFAULT 'firebird_sync'::text,
  data_sincronizacao timestamp with time zone DEFAULT now(),
  created_at timestamp with time zone DEFAULT now(),
  updated_at timestamp with time zone DEFAULT now(),
  centro_resultado text,
  CONSTRAINT fin_despesa_anual_pkey PRIMARY KEY (id)
);
CREATE TABLE public.fin_faturamento_anual (
  id bigint NOT NULL DEFAULT nextval('fin_faturamento_anual_id_seq'::regclass),
  data date,
  categoria text,
  classe text,
  cliente text,
  fatura text,
  operacao text,
  valor numeric,
  origem_dados text DEFAULT 'firebird_sync'::text,
  data_sincronizacao timestamp with time zone DEFAULT now(),
  created_at timestamp with time zone DEFAULT now(),
  updated_at timestamp with time zone DEFAULT now(),
  centro_resultado text,
  empresa text,
  CONSTRAINT fin_faturamento_anual_pkey PRIMARY KEY (id)
);
CREATE TABLE public.fin_metas_projecoes (
  id bigint GENERATED ALWAYS AS IDENTITY NOT NULL,
  created_at timestamp with time zone NOT NULL DEFAULT now(),
  ano text,
  meta integer,
  mes text,
  tipo text,
  CONSTRAINT fin_metas_projecoes_pkey PRIMARY KEY (id)
);
CREATE TABLE public.fin_resultado_anual (
  id bigint NOT NULL DEFAULT nextval('fin_resultado_anual_id_seq'::regclass),
  data date,
  categoria text,
  classe text,
  codigo text,
  descricao text,
  valor numeric,
  tipo text,
  origem_dados text DEFAULT ''::text,
  data_sincronizacao timestamp with time zone DEFAULT now(),
  created_at timestamp with time zone DEFAULT now(),
  updated_at timestamp with time zone DEFAULT now(),
  centro_resultado text,
  CONSTRAINT fin_resultado_anual_pkey PRIMARY KEY (id)
);
CREATE TABLE public.importacoes_despesas (
  id bigint NOT NULL DEFAULT nextval('importacoes_despesas_id_seq'::regclass),
  created_at timestamp with time zone DEFAULT now(),
  updated_at timestamp with time zone DEFAULT now(),
  ref_unique text NOT NULL,
  descricao_custo text NOT NULL,
  valor_custo numeric NOT NULL DEFAULT 0,
  unique_id text DEFAULT 'Identificador único para evitar duplicações (formato: hash MD5 de ref_unique+operacao+valor)'::text,
  CONSTRAINT importacoes_despesas_pkey PRIMARY KEY (id)
);
CREATE TABLE public.importacoes_processos_aberta (
  id bigint NOT NULL DEFAULT nextval('importacoes_processos_aberta_id_seq'::regclass),
  created_at timestamp with time zone DEFAULT now(),
  updated_at timestamp with time zone DEFAULT now(),
  ref_unique text NOT NULL UNIQUE,
  ref_importador text,
  cnpj_importador text,
  importador text,
  data_abertura text,
  modal text,
  pais_procedencia text,
  container text,
  data_embarque text,
  data_chegada text,
  transit_time_real integer,
  urf_despacho text,
  exportador_fornecedor text,
  fabricante text,
  numero_di text,
  data_registro text,
  canal text,
  data_desembaraco text,
  peso_bruto numeric,
  valor_fob_real numeric,
  valor_cif_real numeric,
  material text,
  status_sistema text,
  data_fechamento text,
  firebird_di_codigo integer,
  firebird_fat_codigo text,
  mercadoria text,
  presenca_carga text,
  mercadoria_normalizado text,
  urf_entrada_normalizado text,
  urf_despacho_normalizado text,
  CONSTRAINT importacoes_processos_aberta_pkey PRIMARY KEY (id)
);
CREATE TABLE public.importacoes_processos_armazenagem_kingspan (
  id uuid NOT NULL DEFAULT gen_random_uuid(),
  ref_unique text NOT NULL UNIQUE,
  data_desova date,
  limite_primeiro_periodo date,
  limite_segundo_periodo date,
  dias_extras_armazenagem integer,
  valor_despesas_extras numeric,
  created_at timestamp with time zone DEFAULT now(),
  updated_at timestamp with time zone DEFAULT now(),
  CONSTRAINT importacoes_processos_armazenagem_kingspan_pkey PRIMARY KEY (id),
  CONSTRAINT fk_importacoes_processos_aberta FOREIGN KEY (ref_unique) REFERENCES public.importacoes_processos_aberta(ref_unique)
);
CREATE TABLE public.importacoes_processos_operacional (
  id_processo integer NOT NULL,
  ref_unique text,
  cliente text,
  analista text,
  canal text,
  modal text,
  data_registro date,
  data_fechamento timestamp without time zone,
  sla_dias integer,
  desempenho integer,
  ultima_atualizacao timestamp with time zone DEFAULT now(),
  CONSTRAINT importacoes_processos_operacional_pkey PRIMARY KEY (id_processo)
);
CREATE TABLE public.importacoes_produtos_detalhados (
  id uuid NOT NULL DEFAULT gen_random_uuid(),
  ref_unique text NOT NULL,
  ncm character varying,
  quantidade numeric,
  unidade_medida character varying,
  valor_unitario numeric,
  created_at timestamp with time zone DEFAULT now(),
  descricao text,
  CONSTRAINT importacoes_produtos_detalhados_pkey PRIMARY KEY (id),
  CONSTRAINT fk_processo_ref_unique FOREIGN KEY (ref_unique) REFERENCES public.importacoes_processos_aberta(ref_unique)
);
CREATE TABLE public.importacoes_status_timeline_mapping (
  status_sistema text NOT NULL,
  timeline_order integer NOT NULL,
  status_timeline text NOT NULL,
  created_at timestamp with time zone DEFAULT now(),
  updated_at timestamp with time zone DEFAULT now(),
  CONSTRAINT importacoes_status_timeline_mapping_pkey PRIMARY KEY (status_sistema)
);
CREATE TABLE public.module_pages (
  id integer NOT NULL DEFAULT nextval('module_pages_id_seq'::regclass),
  module_id text NOT NULL,
  page_code character varying NOT NULL,
  page_name character varying NOT NULL,
  description text,
  route_path character varying NOT NULL,
  icon_class character varying,
  sort_order integer DEFAULT 0,
  is_active boolean NOT NULL DEFAULT true,
  requires_special_permission boolean DEFAULT false,
  created_at timestamp with time zone NOT NULL DEFAULT now(),
  updated_at timestamp with time zone NOT NULL DEFAULT now(),
  CONSTRAINT module_pages_pkey PRIMARY KEY (id)
);
CREATE TABLE public.n8n_chat_histories (
  id integer NOT NULL DEFAULT nextval('n8n_chat_histories_id_seq'::regclass),
  session_id character varying NOT NULL,
  message jsonb NOT NULL,
  CONSTRAINT n8n_chat_histories_pkey PRIMARY KEY (id)
);
CREATE TABLE public.n8n_sem_cadastro (
  id integer NOT NULL DEFAULT nextval('n8n_sem_cadastro_id_seq'::regclass),
  session_id character varying NOT NULL,
  message jsonb NOT NULL,
  CONSTRAINT n8n_sem_cadastro_pkey PRIMARY KEY (id)
);
CREATE TABLE public.paises (
  codigo text NOT NULL,
  descricao text,
  sigla text,
  url_bandeira text,
  CONSTRAINT paises_pkey PRIMARY KEY (codigo)
);
CREATE TABLE public.rh_acesso_contabilidade (
  id uuid NOT NULL DEFAULT gen_random_uuid(),
  senha_hash text NOT NULL,
  descricao text,
  is_active boolean NOT NULL DEFAULT true,
  created_at timestamp with time zone NOT NULL DEFAULT now(),
  updated_at timestamp with time zone NOT NULL DEFAULT now(),
  nome_usuario text,
  empresa_controladora_id uuid NOT NULL,
  CONSTRAINT rh_acesso_contabilidade_pkey PRIMARY KEY (id),
  CONSTRAINT fk_rh_acesso_empresa_control FOREIGN KEY (empresa_controladora_id) REFERENCES public.estrutura_empresa_controladora(id)
);
CREATE TABLE public.rh_candidatos (
  id uuid NOT NULL DEFAULT gen_random_uuid(),
  vaga_id uuid NOT NULL,
  nome_completo character varying NOT NULL,
  email character varying NOT NULL,
  telefone character varying,
  status_processo character varying NOT NULL DEFAULT 'Triagem'::character varying CHECK (status_processo::text = ANY (ARRAY['Triagem'::character varying, 'Contato/Agendamento'::character varying, 'Entrevista RH'::character varying, 'Entrevista Técnica'::character varying, 'Aprovado'::character varying, 'Reprovado'::character varying, 'Contratado'::character varying, 'Refutado'::character varying]::text[])),
  fonte_candidatura character varying CHECK (fonte_candidatura::text = ANY (ARRAY['Portal de Vagas'::character varying, 'LinkedIn'::character varying, 'Indeed'::character varying, 'Indicação'::character varying, 'Site Empresa'::character varying, 'Redes Sociais'::character varying, 'E-mail Direto'::character varying, 'Outro'::character varying]::text[])),
  curriculo_path text,
  linkedin_url character varying,
  portfolio_url character varying,
  observacoes text,
  data_candidatura timestamp with time zone NOT NULL DEFAULT now(),
  data_ultima_interacao timestamp with time zone,
  created_at timestamp with time zone NOT NULL DEFAULT now(),
  updated_at timestamp with time zone NOT NULL DEFAULT now(),
  ai_status character varying NOT NULL DEFAULT 'Pendente'::character varying CHECK (ai_status::text = ANY (ARRAY['Pendente'::character varying, 'Em Processamento'::character varying, 'Concluído'::character varying, 'Erro'::character varying]::text[])),
  ai_match_score integer CHECK (ai_match_score >= 0 AND ai_match_score <= 100),
  ai_pre_filter_status character varying DEFAULT 'Aprovado'::character varying,
  ai_extracted_data text,
  sexo character varying,
  foi_indicacao boolean DEFAULT false,
  idade integer,
  estado_civil character varying,
  trabalha_atualmente boolean,
  cidade_estado character varying,
  experiencia_na_area boolean,
  data_nascimento date,
  indicado_por character varying,
  area_objetivo character varying,
  formacao_academica character varying,
  curso_especifico character varying,
  realizou_entrevista boolean DEFAULT false,
  data_entrevista date,
  foi_contratado boolean DEFAULT false,
  data_contratacao date,
  colaborador_id uuid,
  empresa_controladora_id uuid NOT NULL,
  CONSTRAINT rh_candidatos_pkey PRIMARY KEY (id),
  CONSTRAINT fk_rh_cand_empresa_control FOREIGN KEY (empresa_controladora_id) REFERENCES public.estrutura_empresa_controladora(id),
  CONSTRAINT rh_candidatos_colaborador_id_fkey FOREIGN KEY (colaborador_id) REFERENCES public.rh_colaboradores(id),
  CONSTRAINT rh_candidatos_vaga_id_fkey FOREIGN KEY (vaga_id) REFERENCES public.rh_vagas(id)
);
CREATE TABLE public.rh_cargos (
  id uuid NOT NULL DEFAULT gen_random_uuid(),
  nome_cargo character varying NOT NULL,
  descricao text,
  grupo_cargo character varying,
  created_at timestamp with time zone NOT NULL DEFAULT now(),
  updated_at timestamp with time zone NOT NULL DEFAULT now(),
  empresa_controladora_id uuid NOT NULL,
  CONSTRAINT rh_cargos_pkey PRIMARY KEY (id),
  CONSTRAINT fk_rh_cargo_empresa_control FOREIGN KEY (empresa_controladora_id) REFERENCES public.estrutura_empresa_controladora(id)
);
CREATE TABLE public.rh_colaborador_contatos_emergencia (
  id uuid NOT NULL DEFAULT gen_random_uuid(),
  colaborador_id uuid NOT NULL,
  nome_contato character varying NOT NULL,
  telefone_contato character varying NOT NULL,
  parentesco character varying,
  created_at timestamp with time zone NOT NULL DEFAULT now(),
  updated_at timestamp with time zone NOT NULL DEFAULT now(),
  CONSTRAINT rh_colaborador_contatos_emergencia_pkey PRIMARY KEY (id),
  CONSTRAINT rh_colaborador_contatos_emergencia_colaborador_id_fkey FOREIGN KEY (colaborador_id) REFERENCES public.rh_colaboradores(id)
);
CREATE TABLE public.rh_colaborador_dependentes (
  id uuid NOT NULL DEFAULT gen_random_uuid(),
  colaborador_id uuid NOT NULL,
  nome_completo character varying NOT NULL,
  data_nascimento date NOT NULL,
  parentesco character varying NOT NULL,
  created_at timestamp with time zone NOT NULL DEFAULT now(),
  updated_at timestamp with time zone NOT NULL DEFAULT now(),
  CONSTRAINT rh_colaborador_dependentes_pkey PRIMARY KEY (id),
  CONSTRAINT rh_colaborador_dependentes_colaborador_id_fkey FOREIGN KEY (colaborador_id) REFERENCES public.rh_colaboradores(id)
);
CREATE TABLE public.rh_colaboradores (
  id uuid NOT NULL DEFAULT gen_random_uuid(),
  matricula character varying,
  email_corporativo character varying,
  nome_completo character varying NOT NULL,
  cpf character varying NOT NULL UNIQUE,
  data_nascimento date NOT NULL,
  genero character varying,
  raca_cor character varying,
  nacionalidade character varying DEFAULT 'Brasileira'::character varying,
  pis_pasep character varying UNIQUE,
  ctps_numero character varying,
  ctps_serie character varying,
  cnh_numero character varying,
  tel_contato text,
  endereco_completo text,
  status character varying NOT NULL DEFAULT 'Ativo'::character varying CHECK (status::text = ANY (ARRAY['Ativo'::character varying, 'Inativo'::character varying, 'Férias'::character varying, 'Afastado'::character varying]::text[])),
  data_admissao date NOT NULL,
  data_desligamento date,
  created_at timestamp with time zone NOT NULL DEFAULT now(),
  updated_at timestamp with time zone NOT NULL DEFAULT now(),
  escolaridade character varying,
  foto_colab text,
  empresa_controladora_id uuid NOT NULL,
  CONSTRAINT rh_colaboradores_pkey PRIMARY KEY (id),
  CONSTRAINT fk_rh_colab_empresa_control FOREIGN KEY (empresa_controladora_id) REFERENCES public.estrutura_empresa_controladora(id)
);
CREATE TABLE public.rh_departamentos (
  id uuid NOT NULL DEFAULT gen_random_uuid(),
  nome_departamento character varying NOT NULL,
  codigo_centro_custo character varying,
  created_at timestamp with time zone NOT NULL DEFAULT now(),
  updated_at timestamp with time zone NOT NULL DEFAULT now(),
  descricao text,
  empresa_controladora_id uuid NOT NULL,
  CONSTRAINT rh_departamentos_pkey PRIMARY KEY (id),
  CONSTRAINT fk_rh_depto_empresa_control FOREIGN KEY (empresa_controladora_id) REFERENCES public.estrutura_empresa_controladora(id)
);
CREATE TABLE public.rh_eventos_colaborador (
  id uuid NOT NULL DEFAULT gen_random_uuid(),
  colaborador_id uuid NOT NULL,
  tipo_evento character varying NOT NULL CHECK (tipo_evento::text = ANY (ARRAY['Exame Admissional'::character varying, 'Exame Periódico'::character varying, 'Exame Demissional'::character varying, 'Férias'::character varying, 'Licença Médica'::character varying, 'Folga'::character varying]::text[])),
  data_inicio date NOT NULL,
  data_fim date,
  status character varying NOT NULL DEFAULT 'Realizado'::character varying CHECK (status::text = ANY (ARRAY['Solicitado'::character varying, 'Aprovado'::character varying, 'Reprovado'::character varying, 'Realizado'::character varying, 'Em Andamento'::character varying]::text[])),
  descricao text,
  dados_adicionais_jsonb jsonb,
  created_at timestamp with time zone NOT NULL DEFAULT now(),
  updated_at timestamp with time zone NOT NULL DEFAULT now(),
  CONSTRAINT rh_eventos_colaborador_pkey PRIMARY KEY (id),
  CONSTRAINT rh_eventos_colaborador_colaborador_id_fkey FOREIGN KEY (colaborador_id) REFERENCES public.rh_colaboradores(id)
);
CREATE TABLE public.rh_historico_colaborador (
  id uuid NOT NULL DEFAULT gen_random_uuid(),
  colaborador_id uuid NOT NULL,
  data_evento date NOT NULL,
  tipo_evento character varying NOT NULL CHECK (tipo_evento::text = ANY (ARRAY['Admissão'::character varying::text, 'Alteração Salarial'::character varying::text, 'Promoção'::character varying::text, 'Alteração de Cargo'::character varying::text, 'Férias'::character varying::text, 'Afastamento'::character varying::text, 'Alteração Estrutural'::character varying::text, 'Alteração de Benefícios'::character varying::text, 'Reajuste'::character varying::text, 'Feedback'::character varying::text, 'Demissão'::character varying::text])),
  empresa_id uuid,
  departamento_id uuid,
  cargo_id uuid,
  gestor_id uuid,
  salario_mensal numeric,
  tipo_contrato character varying,
  modelo_trabalho character varying,
  descricao_e_motivos text,
  dados_adicionais_jsonb jsonb,
  responsavel_id uuid,
  created_at timestamp with time zone NOT NULL DEFAULT now(),
  status_contabilidade character varying NOT NULL DEFAULT 'Pendente'::character varying CHECK (status_contabilidade::text = ANY (ARRAY['Pendente'::character varying, 'Concluído'::character varying, 'Com Erro'::character varying]::text[])),
  contabilidade_usuario character varying,
  data_contabilidade_check timestamp with time zone,
  obs_contabilidade text,
  beneficios_jsonb jsonb,
  CONSTRAINT rh_historico_colaborador_pkey PRIMARY KEY (id),
  CONSTRAINT rh_historico_colaborador_cargo_id_fkey FOREIGN KEY (cargo_id) REFERENCES public.rh_cargos(id),
  CONSTRAINT rh_historico_colaborador_colaborador_id_fkey FOREIGN KEY (colaborador_id) REFERENCES public.rh_colaboradores(id),
  CONSTRAINT rh_historico_colaborador_departamento_id_fkey FOREIGN KEY (departamento_id) REFERENCES public.rh_departamentos(id),
  CONSTRAINT rh_historico_colaborador_empresa_id_fkey FOREIGN KEY (empresa_id) REFERENCES public.estrutura_empresa_controladora(id),
  CONSTRAINT rh_historico_colaborador_gestor_id_fkey FOREIGN KEY (gestor_id) REFERENCES public.rh_colaboradores(id),
  CONSTRAINT rh_historico_colaborador_responsavel_id_fkey FOREIGN KEY (responsavel_id) REFERENCES auth.users(id)
);
CREATE TABLE public.rh_vagas (
  id uuid NOT NULL DEFAULT gen_random_uuid(),
  titulo character varying NOT NULL,
  descricao text NOT NULL,
  requisitos_obrigatorios text NOT NULL,
  status character varying NOT NULL DEFAULT 'Aberta'::character varying CHECK (status::text = ANY (ARRAY['Aberta'::character varying, 'Pausada'::character varying, 'Fechada'::character varying, 'Cancelada'::character varying]::text[])),
  cargo_id uuid,
  localizacao character varying,
  tipo_contratacao character varying CHECK (tipo_contratacao::text = ANY (ARRAY['CLT'::character varying, 'PJ'::character varying, 'Estágio'::character varying]::text[])),
  data_abertura timestamp with time zone NOT NULL DEFAULT now(),
  data_fechamento timestamp with time zone,
  created_at timestamp with time zone NOT NULL DEFAULT now(),
  updated_at timestamp with time zone NOT NULL DEFAULT now(),
  beneficios text,
  nivel_senioridade character varying,
  quantidade_vagas integer DEFAULT 1,
  regime_trabalho character varying CHECK ((regime_trabalho::text = ANY (ARRAY['Presencial'::character varying, 'Híbrido'::character varying, 'Remoto'::character varying]::text[])) OR regime_trabalho IS NULL),
  carga_horaria character varying,
  requisitos_desejaveis text,
  diferenciais text,
  faixa_salarial_min numeric,
  faixa_salarial_max numeric,
  empresa_controladora_id uuid NOT NULL,
  CONSTRAINT rh_vagas_pkey PRIMARY KEY (id),
  CONSTRAINT fk_rh_vaga_empresa_control FOREIGN KEY (empresa_controladora_id) REFERENCES public.estrutura_empresa_controladora(id),
  CONSTRAINT rh_vagas_cargo_id_fkey FOREIGN KEY (cargo_id) REFERENCES public.rh_cargos(id)
);
CREATE TABLE public.sync_logs (
  id bigint NOT NULL DEFAULT nextval('sync_logs_id_seq'::regclass),
  created_at timestamp with time zone DEFAULT now(),
  tabela text NOT NULL,
  modulo text NOT NULL,
  total_registros integer DEFAULT 0,
  sucessos integer DEFAULT 0,
  falhas integer DEFAULT 0,
  tempo_execucao_segundos numeric,
  status text DEFAULT 'em_andamento'::text,
  detalhes jsonb,
  erro text,
  CONSTRAINT sync_logs_pkey PRIMARY KEY (id)
);
CREATE TABLE public.total_usuarios_origem (
  count bigint
);
CREATE TABLE public.user_empresas (
  id integer NOT NULL DEFAULT nextval('user_empresas_id_seq'::regclass),
  user_id uuid NOT NULL,
  cliente_sistema_id integer NOT NULL,
  ativo boolean NOT NULL DEFAULT true,
  data_vinculo date NOT NULL DEFAULT CURRENT_DATE,
  observacoes text,
  created_at timestamp with time zone NOT NULL DEFAULT now(),
  updated_at timestamp with time zone NOT NULL DEFAULT now(),
  CONSTRAINT user_empresas_pkey PRIMARY KEY (id),
  CONSTRAINT fk_user_empresas_cliente FOREIGN KEY (cliente_sistema_id) REFERENCES public.cad_clientes_sistema(id),
  CONSTRAINT fk_user_empresas_user FOREIGN KEY (user_id) REFERENCES public.users(id)
);
CREATE TABLE public.user_whatsapp (
  id integer NOT NULL DEFAULT nextval('user_whatsapp_id_seq'::regclass),
  user_id uuid NOT NULL,
  numero character varying,
  nome character varying,
  tipo character varying DEFAULT 'pessoal'::character varying CHECK (tipo::text = ANY (ARRAY['pessoal'::character varying::text, 'empresarial'::character varying::text, 'suporte'::character varying::text])),
  principal boolean DEFAULT false,
  ativo boolean DEFAULT true,
  created_at timestamp with time zone DEFAULT now(),
  updated_at timestamp with time zone DEFAULT now(),
  CONSTRAINT user_whatsapp_pkey PRIMARY KEY (id),
  CONSTRAINT user_whatsapp_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id)
);
CREATE TABLE public.users (
  id uuid NOT NULL,
  name text,
  email text NOT NULL UNIQUE,
  role text CHECK (role = ANY (ARRAY['admin'::text, 'interno_unique'::text, 'cliente_unique'::text])),
  created_at timestamp with time zone NOT NULL DEFAULT timezone('utc'::text, now()),
  updated_at timestamp with time zone NOT NULL DEFAULT timezone('utc'::text, now()),
  is_active boolean CHECK (is_active = ANY (ARRAY[true, false])),
  perfis_json jsonb,
  perfil_principal text,
  empresa_controladora_id uuid,
  CONSTRAINT users_pkey PRIMARY KEY (id),
  CONSTRAINT fk_users_empresa_controladora FOREIGN KEY (empresa_controladora_id) REFERENCES public.estrutura_empresa_controladora(id),
  CONSTRAINT users_id_fkey FOREIGN KEY (id) REFERENCES auth.users(id)
);
CREATE TABLE public.users_perfis (
  id integer NOT NULL DEFAULT nextval('users_perfis_id_seq'::regclass),
  perfil_nome character varying NOT NULL,
  modulo_codigo character varying NOT NULL,
  modulo_nome character varying NOT NULL,
  paginas_modulo jsonb NOT NULL DEFAULT '[]'::jsonb,
  is_active boolean NOT NULL DEFAULT true,
  created_at timestamp with time zone NOT NULL DEFAULT now(),
  updated_at timestamp with time zone NOT NULL DEFAULT now(),
  is_admin_profile boolean DEFAULT false,
  descricao text,
  CONSTRAINT users_perfis_pkey PRIMARY KEY (id)
);