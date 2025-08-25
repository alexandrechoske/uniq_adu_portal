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

A API_BYPASS_KEY É SEMPRE "$env:API_BYPASS_KEY = uniq_api_2025_dev_bypass_key", utilize ela nos testes.

## Instruções para Criação de Nova Tela/Rota com Controle de Acesso por Perfil

### 1. Estrutura do Módulo

#### 1.1 Criar a estrutura de pastas seguindo o padrão:
```
modules/[nome_do_modulo]/
├── __init__.py
├── routes.py
├── templates/
│   └── [nome_do_modulo]/
│       └── [nome_do_modulo].html
└── static/
    └── [nome_do_modulo]/
        ├── [nome_do_modulo].css
        └── [nome_do_modulo].js
```

#### 1.2 Configurar o blueprint no `__init__.py`:
```python
from flask import Blueprint

bp = Blueprint('[nome_do_modulo]', __name__, url_prefix='/[nome_do_modulo]')

from . import routes
```

#### 1.3 Implementar as rotas no `routes.py`:
```python
from flask import render_template, request, redirect, url_for, flash
from modules.auth.routes import login_required, role_required
from . import bp

@bp.route('/')
@login_required
def index():
    return render_template('[nome_do_modulo]/[nome_do_modulo].html')

# Adicionar outras rotas conforme necessário
```

### 2. Registrar o Blueprint no App Principal

#### 2.1 No arquivo `app.py`, adicionar:
```python
# Registrar novo módulo
from modules.[nome_do_modulo] import bp as [nome_do_modulo]_bp
app.register_blueprint([nome_do_modulo]_bp)
```

### 3. Atualizar o Sistema de Controle de Acesso

#### 3.1 Atualizar o `PerfilAccessService` no arquivo `services/perfil_access_service.py`:

##### a) Adicionar o módulo na estrutura `complete_menu`:
```python
'[codigo_modulo]': {
    'nome': '[Nome do Módulo]',
    'icone': 'fas fa-[icone]',
    'url': '/[nome_do_modulo]',
    'paginas': {
        '[codigo_pagina]': {'nome': '[Nome da Página]', 'url': '/[nome_do_modulo]/[rota]'},
        # Adicionar mais páginas conforme necessário
    }
}
```

##### b) Se necessário, adicionar mapeamento de compatibilidade em `MODULE_MAPPING`:
```python
MODULE_MAPPING = {
    '[codigo_antigo]': '[codigo_novo]',
    # outros mapeamentos...
}
```

#### 3.2 Atualizar a lista de módulos admin (se aplicável):
```python
# Para usuários admin, adicionar o novo módulo na lista:
accessible_modules = [
    'dashboard', 'importacoes', 'financeiro', 'relatorios', 
    'usuarios', 'agente', 'conferencia', 'materiais', 'config',
    '[novo_modulo]'  # Adicionar aqui
]
```

### 4. Atualizar os Templates

#### 4.1 No arquivo `templates/base.html`, adicionar entrada na sidebar:
```html
<!-- Seção apropriada da sidebar -->
{% if '[codigo_modulo]' in accessible_modules %}
<a href="{{ url_for('[nome_do_modulo].index') }}"
   class="sidebar-item {% if request.endpoint and request.endpoint.startswith('[nome_do_modulo].') %}active{% endif %}"
   title="[Descrição do Módulo]">
    <i class="[classe_icone] text-xl"></i>
    <span class="sidebar-text">[Nome do Módulo]</span>
</a>
{% endif %}
```

#### 4.2 No arquivo `modules/menu/templates/menu.html`, adicionar card do módulo:
```html
<!-- Verificar se o usuário tem acesso ao módulo -->
{% if '[codigo_modulo]' in accessible_modules %}
<div class="module-column">
    <div class="module-section">
        <div class="module-header">
            <h3 class="module-title">[Nome do Módulo]</h3>
        </div>
        <div class="module-grid">
            <!-- Verificar páginas específicas -->
            {% set [modulo]_pages = user_accessible_pages.get('[codigo_modulo]', []) %}
            
            {% if '*' in [modulo]_pages or '[codigo_pagina]' in [modulo]_pages %}
            <a href="{{ url_for('[nome_do_modulo].[rota]') }}" class="module-card" data-module="[codigo_pagina]">
                <div class="module-icon"><i class="[classe_icone]"></i></div>
                <h4 class="module-title">[Nome da Página]</h4>
                <p class="module-desc">[Descrição da página].</p>
            </a>
            {% endif %}
            
            <!-- Adicionar mais páginas conforme necessário -->
        </div>
    </div>
</div>
{% endif %}
```

### 5. Atualizar o Banco de Dados

#### 5.1 Inserir registro na tabela `users_perfis`:
```sql
INSERT INTO users_perfis (perfil_nome, modulo_codigo, modulo_nome, paginas_modulo, is_active)
VALUES 
('[nome_do_perfil]', '[codigo_modulo]', '[Nome do Módulo]', '["[codigo_pagina1]", "[codigo_pagina2]"]', true);
```

#### 5.2 Exemplo de inserção completa:
```sql
-- Exemplo: Módulo de Vendas
INSERT INTO users_perfis (perfil_nome, modulo_codigo, modulo_nome, paginas_modulo, is_active)
VALUES 
('vendas_completo', 'vendas', 'Vendas', '["dashboard", "clientes", "propostas", "contratos"]', true),
('vendas_basico', 'vendas', 'Vendas', '["clientes", "propostas"]', true);
```

### 6. Sistema de JavaScript para Perfis

#### 6.1 Atualizar o arquivo `modules/usuarios/static/js/perfis.js` - constante `MODULOS_SISTEMA`:
```javascript
const MODULOS_SISTEMA = {
    // ... módulos existentes ...
    [codigo_modulo]: {
        nome: '[Nome do Módulo]',
        icon: '[classe_icone]',
        pages: [
            { code: '[codigo_pagina1]', name: '[Nome da Página 1]', icon: '[icone_pagina1]' },
            { code: '[codigo_pagina2]', name: '[Nome da Página 2]', icon: '[icone_pagina2]' }
        ]
    }
};
```

### 7. Testes de Implementação

#### 7.1 Criar arquivo de teste `test_novo_modulo.py`:
```python
import os
import requests
import json

API_BYPASS_KEY = os.getenv('API_BYPASS_KEY', 'uniq_api_2025_dev_bypass_key')
BASE_URL = 'http://localhost:5000'
headers = {'X-API-Key': API_BYPASS_KEY, 'Content-Type': 'application/json'}

def test_novo_modulo():
    """Testa se o novo módulo está acessível"""
    print("🧪 [TESTE] Testando novo módulo...")
    
    try:
        # Testar acesso à página principal
        response = requests.get(f'{BASE_URL}/[nome_do_modulo]/', headers=headers)
        print(f"📤 [TESTE] Status da página: {response.status_code}")
        
        # Testar se aparece no menu filtrado
        response = requests.get(f'{BASE_URL}/menu/api/menu-filtrado', headers=headers)
        if response.status_code == 200:
            menu = response.json()
            if '[codigo_modulo]' in menu:
                print("✅ [TESTE] Módulo encontrado no menu filtrado")
            else:
                print("❌ [TESTE] Módulo NÃO encontrado no menu filtrado")
        
    except Exception as e:
        print(f"❌ [TESTE] Erro: {e}")

if __name__ == "__main__":
    test_novo_modulo()
```

#### 7.2 Executar teste:
```powershell
$env:API_BYPASS_KEY = "uniq_api_2025_dev_bypass_key"
python test_novo_modulo.py
```

### 8. Checklist Final

- [ ] Estrutura de pastas criada seguindo o padrão
- [ ] Blueprint registrado no `app.py`
- [ ] Rotas implementadas com decoradores de autenticação
- [ ] `PerfilAccessService` atualizado com novo módulo
- [ ] Template HTML criado seguindo o padrão visual
- [ ] Sidebar atualizada no `templates/base.html`
- [ ] Menu principal atualizado no `modules/menu/templates/menu.html`
- [ ] Registros inseridos na tabela `users_perfis`
- [ ] JavaScript de perfis atualizado
- [ ] Testes executados e aprovados
- [ ] Arquivos de teste removidos após validação

### 9. Observações Importantes

#### 9.1 Códigos e Nomenclatura:
- Use códigos curtos e descritivos para módulos (ex: 'vendas', 'rh', 'estoque')
- Códigos de páginas devem ser únicos dentro do módulo
- Mantenha consistência com os padrões existentes

#### 9.2 Permissões:
- Sempre usar decoradores `@login_required` e `@role_required` nas rotas
- Considerar diferentes níveis de acesso dentro do módulo
- Testar com diferentes perfis de usuário

#### 9.3 Interface:
- Seguir o padrão visual existente (cores, ícones, layout)
- Usar ícones da biblioteca MDI (Material Design Icons)
- Manter responsividade em todos os dispositivos

#### 9.4 Banco de Dados:
- Sempre criar perfis de teste além dos perfis de produção
- Documentar as permissões de cada perfil
- Considerar perfis hierárquicos (básico → intermediário → completo)

**LEMBRE-SE**: Sempre criar e testar com perfis diferentes antes de disponibilizar em produção. Remove todos os arquivos de teste após a validação.