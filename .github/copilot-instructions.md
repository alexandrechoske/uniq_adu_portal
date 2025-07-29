# AI Coding Agent Instructions - UniSystem Portal

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
SUPABASE_KEY=your_anon_key
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

API_BYPASS_KEY = os.getenv('API_BYPASS_KEY')
BASE_URL = 'http://localhost:5000'
headers = {'X-API-Key': API_BYPASS_KEY, 'Content-Type': 'application/json'}

SEMPRE QUE FOI CRIAR UM NOVO MÓDULO, A ESTRUTURA DA PASTA DEVE SER A SEGUINTE:
```
modules/[nome_do_modulo]/__init__.py
modules/[nome_do_modulo]/routes.py
modules/[nome_do_modulo]/templates/[nome_do_modulo]/[nome_do_modulo].html
modules/[nome_do_modulo]/static/[nome_do_modulo]/[arquivos_estaticos].css
modules/[nome_do_modulo]/static/[nome_do_modulo]/[arquivos_estaticos].js
``` 