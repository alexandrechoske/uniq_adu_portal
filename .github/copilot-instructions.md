# AI Coding Agent Instructions - UniSystem Portal

## Architecture Overview

This is a Flask-based customs management portal with a **cache-first architecture** designed for performance optimization. The system serves customs operations data through multiple specialized modules with role-based access control.

### Core Components

- **Flask App**: Modular blueprint-based structure with 12+ specialized modules
- **Database**: Supabase (PostgreSQL) with dual client setup (`supabase` for regular ops, `supabase_admin` for privileged operations)
- **Caching**: Session-based memory cache with `DataCacheService` for performance optimization
- **Authentication**: Role-based access (`admin`, `interno_unique`, `cliente_unique`) with company filtering
- **Material Processing**: Intelligent categorization system via `MaterialCleaner` class

## Critical Architectural Patterns

### 1. Cache-First Data Flow
```python
# ALWAYS check session cache first before database queries
cached_data = session.get('cached_data')
if not cached_data:
    # Fallback to database only if cache miss
```

The system preloads 30 days of data during login and stores in `session['cached_data']`. All data-heavy operations (dashboard, materials analytics) use this cache, not direct DB queries.

### 2. Blueprint Registration Order
```python
# In app.py - import routes AFTER app initialization
from routes import auth, dashboard, relatorios, usuarios, agente, api, conferencia
from routes import conferencia_pdf, debug, paginas, materiais, background_tasks
```

### 3. Dual Supabase Client Pattern
- `supabase`: Regular client for user operations (RLS-enabled)
- `supabase_admin`: Service key client for admin operations, user management, data preloading

### 4. Role-Based Data Filtering
```python
# Client users see only their company data
if user_role == 'cliente_unique':
    query = query.in_('cnpj_importador', user_companies)
```

## Essential Development Workflows

### Running the Application
```bash
python app.py  # Debug mode enabled by default
```

### Environment Setup
Create `.env` with:
```
SUPABASE_URL=your_supabase_url
SUPABASE_KEY=your_anon_key
SUPABASE_SERVICE_KEY=your_service_key
SECRET_KEY=your_secret_key
GEMINI_API_KEY=your_gemini_key  # For AI document processing
```

### Database Date Format Handling
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