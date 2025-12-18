# UniSystem Portal — Guia Único (FastAPI + Next.js)


Cores Oficiais da Aplicação ( utilizar elas e variantes )
#165672
#2d6b92
#e2ba0a

## Stack & Arquitetura
- **Backend**: FastAPI + Supabase (client e service role). JWT e dependências para auth/role. Cache-first (Redis/memória) antes de bater no banco.
- **Frontend**: Next.js 14 (App Router) + Tailwind. Estado global via Context API. Data fetching com TanStack Query.
- **Design System**: Seguir fielmente o layout `nimbusai.html`/`nimbusai.tsx`: elegante, compacto, minimalista, com modo claro/escuro, sidebar fixa, header fino, cards densos.
- **Responsividade**: Mobile-first, breakpoints bem testados; sidebar colapsável em mobile; tabelas/grids com scroll horizontal quando necessário.

## UI/UX Padrões
- **Temas**: Sempre oferecer toggle de tema. Garantir contraste AA, ícones `lucide-react`, tokens de cor baseados no layout Nimbus (azul profundo no claro, cinzas/pretos sutis no escuro).
- **Tipografia**: Fonte `Inter` (ou compatível). Tamanhos compactos, espaçamento enxuto. Evitar poluição visual.
- **Componentes**: KPI cards clicáveis, gráficos (Recharts/Apex) minimalistas, tabelas com linhas finas e hover. Skeletons para carregamento.
- **Acessibilidade**: Semântica HTML, `aria-*`, foco visível, navegação por teclado.
- **Consistência**: Não criar novas paletas ou estilos fora do padrão Nimbus. Reusar classes utilitárias Tailwind. Layouts claros e escuros devem ter mesma hierarquia visual.

## Backend (FastAPI) Boas Práticas
- **Auth**: Validar JWT Supabase em dependência. Diferenciar `supabase` (RLS) vs `supabase_admin` (service). Rota de login retorna token + contexto (empresas, perfis, role).
- **RBAC**: `cliente_unique` sempre filtrado por CNPJs vinculados; `interno_unique` filtra salvo `admin_operacao/master_admin`; `admin` vê tudo. Toda rota protegida deve aplicar esse filtro.
- **Cache-First**: Antes de query, buscar cache por `user_id` + chave. Invalidate on refresh endpoints.
- **Datas**: Banco usa DD/MM/YYYY; filtros em ISO. Converter sempre via helpers.
- **Observabilidade**: Logging estruturado; timeouts coerentes; retries onde já existentes (ex.: enrichers).
- **Segurança**: Sanitizar input, validar schemas Pydantic, evitar secrets em código. CORS apenas domínios necessários.

## Frontend (Next.js) Boas Práticas
- **App Router** com server components para layout/slots; client components só onde houver interação.
- **Estado**: Context API para sessão/tema; TanStack Query para dados; evitar prop drilling.
- **Temas**: `class`-based (ex.: `dark` no `<html>`). Guardar preferência em `localStorage`.
- **Reatividade**: Mobile: sidebar off-canvas; header sempre acessível. Use `flex/grid` responsivos.
- **Dados**: Nunca confiar em dados não filtrados; aplicar company filters também no client ao consumir APIs.

## Regras de Negócio Essenciais
- **Cache e pré-carga**: Manter padrão cache-first herdado do Flask (30-365 dias) até migração completa.
- **Module Pages**: Qualquer nova rota/página deve ser inserida em `module_pages` no Supabase para controle de perfis.
- **Kingspan/Ciser**: Permissões de materiais e aba Armazenagem dependem do vínculo da empresa; preservar flags `has_kingspan_access` etc.

## ⚠️ CONTROLE DE ACESSO POR MÓDULO (CRÍTICO)

### Módulos Sensíveis — Acesso Restrito Máximo
**RH e Financeiro** são módulos **extremamente sensíveis** que contêm dados confidenciais (salários, dados pessoais, informações financeiras).

**Requisitos de Segurança**:
1. **Autenticação Obrigatória**: Todas as rotas devem exigir JWT válido.
2. **Autorização em Múltiplos Níveis**:
   - Verificar `role` do usuário (apenas `admin` ou perfis específicos como `rh_admin`, `financeiro_admin`).
   - Verificar perfis detalhados em `users_perfis` (ex.: `master_admin`, `admin_operacao`).
   - Implementar permissões granulares por página (via `module_pages`).
3. **Filtros de Empresa**: Mesmo para admins, aplicar filtros de empresa quando aplicável para evitar exposição acidental de dados.
4. **Auditoria**: Logar todos os acessos a rotas sensíveis (quem, quando, o quê).
5. **Rate Limiting**: Implementar limites de requisições para prevenir scraping.
6. **Frontend**: Ocultar completamente módulos/páginas para usuários sem permissão (não apenas desabilitar botões).

### Módulo Aberto — Importações
**Importações** é o módulo **público** da aplicação (dentro do sistema autenticado).

**Regras de Acesso**:
- Todos os usuários autenticados (`cliente_unique`, `interno_unique`, `admin`) podem acessar.
- Aplicar **filtros de empresa** conforme o role:
  - `cliente_unique`: Vê apenas suas empresas vinculadas.
  - `interno_unique` (não admin): Vê apenas empresas associadas.
  - `admin_operacao` e `master_admin`: Veem todas as empresas.
- **Prioridade de Desenvolvimento**: Importações é o módulo **core** e deve ser migrado primeiro.

### Estrutura dos 3 Módulos Principais
1. **Importações** (Core, público, primeira prioridade de migração)
2. **Financeiro** (Sensível, acesso restrito, segunda prioridade)
3. **RH** (Sensível, acesso restrito, terceira prioridade)

**+ Páginas de Configuração**: Acessíveis apenas para `admin` e perfis específicos.

## Testes
- Prefixar testes com `test_`. Remover arquivos de teste após uso temporário.
- Priorizar Playwright/Cypress para front; pytest para API. Cobrir filtros de empresa, temas e responsividade básica.
- Logs claros em cenários de teste; usar PowerShell para comandos (Windows).

## Estrutura de Módulo (próximos serviços)
- **Backend**: `app/routers/<feature>.py` com prefixo claro; schemas em `app/schemas`; serviços em `app/services`.
- **Frontend**: `app/<feature>/page.tsx` + componentes internos; estilos via Tailwind; sem CSS solto fora do padrão.

## Processo ao criar/alterar páginas
1) Respeitar layout Nimbus (claro/escuro). 2) Garantir filtros de empresa/role em backend e, se exibido, também no frontend. 3) Incluir página em `module_pages` quando aplicável. 4) Adicionar skeleton/loading states. 5) Validar mobile.

## Não esquecer
- Nunca criar novas paletas; reutilizar tokens Nimbus. Evitar assets pesados. Manter respostas concisas e código limpo.# AI Coding Agent Instructions - UniSystem Portal

## Architecture Overview

This is a Flask-based customs management portal with a **cache-first architecture** designed for performance optimization. The system serves customs operations data through multiple specialized modules with role-based access control.

### Core Components

- **Flask App**: Modular blueprint-based structure with 12+ specialized modules
- **Database**: Supabase (PostgreSQL) with dual client setup (`supabase` for regular ops, `supabase_admin` for privileged operations)
- **Caching**: Hybrid caching system - session-based memory cache + server-side `DataCacheService` for performance optimization
- **Authentication**: Role-based access (`admin`, `interno_unique`, `cliente_unique`) with company filtering and API bypass capability
- **Material Processing**: Intelligent categorization system via `MaterialCleaner` class with 15+ predefined categories

## Critical Architectural Patterns

### 1. Cache-First Data Flow
```python
# ALWAYS check session cache first before database queries
cached_data = session.get('cached_data')
if not cached_data:
    # Fallback to server-side DataCacheService
    cached_data = data_cache.get_cache(user_id, 'raw_data')
    if not cached_data:
        # Last resort: direct database query
```

The system preloads 30-365 days of data during login and stores in both `session['cached_data']` and server-side cache. All data-heavy operations (dashboard, materials analytics) use this cache, not direct DB queries.

### 2. Dual Client Authentication Pattern
```python
# Regular client (RLS-enabled) for user operations
from extensions import supabase
# Admin client (service key) for privileged operations and data preloading
from extensions import supabase_admin
```

### 3. API Bypass for Testing
```python
# Test APIs without authentication using X-API-Key header
api_bypass_key = os.getenv('API_BYPASS_KEY')
if request.headers.get('X-API-Key') == api_bypass_key:
    # Bypass authentication for testing
```

### 4. Role-Based Data Filtering
```python
# Client users see only their company data
if user_role == 'cliente_unique':
    query = query.in_('cnpj_importador', user_companies)
```

### 5. Blueprint Registration Order (Critical)
```python
# In app.py - import routes AFTER app initialization to avoid circular imports
from routes import auth, dashboard, relatorios, usuarios, agente, api, conferencia
from routes import conferencia_pdf, debug, paginas, materiais, background_tasks
```

## Essential Development Workflows

### Running the Application
```bash
python app.py  # Debug mode enabled by default
# OR use VS Code task: "Run Flask Development Server"
```

### Environment Setup
Create `.env` with:
```
SUPABASE_URL=your_supabase_url
SUPABASE_SERVICE_KEY=your_anon_key
SUPABASE_SERVICE_KEY=your_service_key
SECRET_KEY=your_secret_key
GEMINI_API_KEY=your_gemini_key  # For AI document processing
API_BYPASS_KEY=your_test_key    # For testing without authentication
```

### Testing Strategy (Project-Specific)
1. **Test APIs without authentication**: Use `X-API-Key` header with `API_BYPASS_KEY`
2. **Always prefix test files with `test_`** for easy identification and cleanup
3. **Use debug endpoints**: `/debug/`, `/materiais/debug-*`, `/materiais/test-*`
4. **Session testing**: `/debug/log-session` for session state inspection
5. **Cache testing**: `/materiais/test-cache` for cache validation

### Database Date Format Handling (Critical)
The system uses **Brazilian date format (DD/MM/YYYY)** in database but **ISO format (YYYY-MM-DD)** for filtering. Always use the `filter_by_date_python()` function in `routes/materiais.py` for date comparisons.

### Material Categorization
Use `MaterialCleaner` for intelligent material processing:
```python
from material_cleaner import MaterialCleaner
material_cleaner = MaterialCleaner()
material_info = material_cleaner.clean_material(raw_material_text)
```

## Module-Specific Patterns

### Dashboard Module (`routes/dashboard.py`)
- Uses 30-day default period for data queries
- Implements cache fallback with `dashboard_cache` compatibility layer
- Handles both dict (legacy) and list (new) cache formats

### Materials Module (`routes/materiais.py`)
- Cache-first architecture with session data
- Intelligent search using `MaterialCleaner` category mappings
- Python-based date filtering for Brazilian format compatibility

### Authentication Flow (`routes/auth.py`)
- Login triggers data preloading via `data_cache.preload_user_data()`
- Session management with 12-hour expiration
- Company association for `cliente_unique` users
- API bypass mode for testing: `X-API-Key` header bypasses authentication

### API Endpoints (`routes/api.py`)
- `/api/global-data`: Comprehensive data endpoint with role-based filtering
- `/api/force-refresh`: Manual cache invalidation and data refresh

## Common Gotchas

### Date Filtering Issues
- Database stores DD/MM/YYYY format
- Always convert to datetime objects for comparison
- Use 30-day periods instead of full year queries for performance

### Cache Format Evolution
- New modules expect `list` format in `session['cached_data']`
- Dashboard supports both `dict` (legacy) and `list` (current) formats
- Always check cache format: `isinstance(cached_data, list)`

### Blueprint URL Prefixes
- Materials: `/materiais/`
- API: `/api/`
- Conferencia: `/conferencia/`
- Debug: `/debug/`

### Performance Considerations
- Default query timeout: 15 seconds
- Gemini AI operations: 120 seconds timeout
- Dashboard limited to 1000 rows for performance
- Always use cache for data-heavy operations

## File Structure Navigation

- `app.py`: Main application entry with blueprint registration
- `config.py`: Environment configuration and timeout settings
- `extensions.py`: Supabase client initialization
- `material_cleaner.py`: Material categorization logic with 15+ categories
- `services/data_cache.py`: Cache service with preload functionality
- `routes/`: Modular blueprints for each feature area
- `templates/`: Jinja2 templates with base layout inheritance
- `static/`: CSS, JS, and media assets

## Testing Approach

- Use `/debug/` routes for system diagnostics
- Session debugging via `/debug/log-session`
- Database connectivity test via `/test-connection`
- Cache validation through manual login flow testing

When implementing new features, always consider the cache-first architecture, role-based filtering, and Brazilian date format handling patterns established in the existing codebase.

## Profile & Access Control System (Módulo de Usuários)

### Página de Perfis de Acesso
Located in: `modules/usuarios/templates/perfis.html`

The profile system controls user access to specific pages within modules. All available pages are stored in the `module_pages` table in Supabase.

### Adding New Routes to Profile System

**IMPORTANTE**: Whenever you create a new route/page, you MUST add it to the `module_pages` table so it appears in the profile creation UI.

**Steps to add a new page:**

1. **Create your route** in the appropriate module (e.g., `modules/financeiro/new_feature/routes.py`)
2. **Test the route** to ensure it works
3. **Generate SQL INSERT** using the template:
```sql
INSERT INTO "public"."module_pages" 
("id", "module_id", "page_code", "page_name", "description", "route_path", "icon_class", "sort_order", "is_active", "requires_special_permission", "created_at", "updated_at") 
VALUES (
  'UUID_v4_HERE', 
  'module_id', 
  'page_code_identifier', 
  'Display Name',
  'Brief description',
  '/module/route-path',
  'mdi-icon-class',
  N,  -- sort order number
  true,
  false,
  NOW(),
  NOW()
);
```
4. **Execute INSERT** in Supabase SQL Editor
5. **Verify** that the new page appears in "Usuários > Perfis > Novo Perfil" modal

### Current Pages (23 total)
- **Importação**: 7 pages (dashboard_executivo, dashboard_resumido, documentos, relatorio, agente, materiais, dashboard_operacional)
- **Financeiro**: 8 pages (fin_dashboard_executivo, fluxo_caixa, despesas, faturamento, **conciliacao**, categorizacao, projecoes, export_bases)
- **RH**: 8 pages (dashboard, colaboradores, estrutura_cargos, estrutura_departamentos, recrutamento, desempenho, carreiras, dashboard_analitico)

### Reference Guide
See `docs/GUIA_PAGINAS_PERFIS.md` for complete mapping and maintenance instructions.

Se for testar, utilize método via API pois a página exige login.
SEMPRE CRIE ARQUIVOS COM O PREFIXO `test_` PARA TESTES.
SEMPRE DELETE OS ARQUIVOS QUE CRIOU PARA TESTAR. ( delete os arquivos com o PREFIXO `test_` )
SEMPRE QUE FOR TESTAR, ADICIONE LOGS, E PEÇA PARA EU ENTRAR NA PÁGINA EM QUESTÃO, E VOCÊ VALIDA OS LOGS DE SAÍDA.
SEMPRE SIGA AS MELHORES PRÁTICAS DE DESENVOLVIMENTO, COMO NOMEAÇÃO DE ARQUIVOS, ESTRUTURA DE PASTAS, E PADRÕES DE CÓDIGO.
SEMPRE USAR A MESMA ESTILIZAÇÃO DA APLICAÇÃO INTEIRA COMO BASE PARA AS OUTRAS/NOVAS PÁGINAS.
NÃO CRIAR ESTILIZAÇÕES NOVAS, COM CORES DIFERENTES DAS ATUAIS.
SEMPRE QUE FOR INCLUIR ALGUMA ALTERAÇÃO, CRIE ARQUIVOS PARA TESTARMOS ANTES DE APLICAR AS MUDANÇAS.
SEMPRE QUE FOR EXECUTAR TESTES, FAÇA OS COMANDOS COM POWERSHELL E NÃO CMD!
SEMPRE QUE PRECISAR REALIZAR O BYPASS EM REQUISIÇÕES, FAZER ASSIM:
NUNCA DEIXE CHAVES PRIVADAS EM ARQUIVOS DE CÓDIGOS QUE NÃO SEJA O .ENV

API_BYPASS_KEY = os.getenv('API_BYPASS_KEY')
BASE_URL = 'http://192.168.0.75:5000'
headers = {'X-API-Key': API_BYPASS_KEY, 'Content-Type': 'application/json'}

SEMPRE QUE FOI CRIAR UM NOVO MÓDULO, A ESTRUTURA DA PASTA DEVE SER A SEGUINTE:
```
modules/[nome_do_modulo]/__init__.py
modules/[nome_do_modulo]/routes.py
modules/[nome_do_modulo]/templates/[nome_do_modulo]/[nome_do_modulo].html
modules/[nome_do_modulo]/static/[nome_do_modulo]/[arquivos_estaticos].css
modules/[nome_do_modulo]/static/[nome_do_modulo]/[arquivos_estaticos].js
``` 

A API_BYPASS_KEY É SEMPRE "$env:API_BYPASS_KEY = uniq_api_2025_dev_bypass_key", utilize ela nos testes.

SEMPRE QUE FOR TESTAR UTILIZE O IP: 
AO INVÉS DE LOCALHOST!