# 2. INTEGRAÇÃO COM O SISTEMA UNISYSTEM - MÓDULO RH

## Complemento ao Plano de Desenvolvimento

Este documento complementa o `1_plano_desenvolvimento.md` com aspectos específicos de integração com a arquitetura existente do UniSystem Portal.

---

## 4. Integração com Sistema de Autenticação e Permissões

### 4.1. Row Level Security (RLS) - CRÍTICO

O módulo RH lida com dados extremamente sensíveis. **TODAS as tabelas** devem ter RLS habilitado:

```sql
-- =====================================================================
-- ROW LEVEL SECURITY (RLS) PARA MÓDULO RH
-- =====================================================================

-- 4.1.1. HABILITAR RLS EM TODAS AS TABELAS
ALTER TABLE rh_colaboradores ENABLE ROW LEVEL SECURITY;
ALTER TABLE rh_historico_colaborador ENABLE ROW LEVEL SECURITY;
ALTER TABLE rh_cargos ENABLE ROW LEVEL SECURITY;
ALTER TABLE rh_departamentos ENABLE ROW LEVEL SECURITY;
ALTER TABLE rh_empresas ENABLE ROW LEVEL SECURITY;

-- 4.1.2. POLÍTICAS PARA ADMINS - ACESSO TOTAL
CREATE POLICY "admin_full_access_colaboradores" ON rh_colaboradores
    FOR ALL
    TO authenticated
    USING (
        EXISTS (
            SELECT 1 FROM users_dev 
            WHERE users_dev.id = auth.uid() 
            AND users_dev.role = 'admin'
        )
    );

-- Replicar política admin para todas as tabelas do RH
CREATE POLICY "admin_full_access_historico" ON rh_historico_colaborador
    FOR ALL TO authenticated
    USING (
        EXISTS (
            SELECT 1 FROM users_dev 
            WHERE users_dev.id = auth.uid() 
            AND users_dev.role = 'admin'
        )
    );

-- 4.1.3. POLÍTICAS PARA USUÁRIOS INTERNO_UNIQUE COM PERFIL RH
CREATE POLICY "interno_rh_access_colaboradores" ON rh_colaboradores
    FOR SELECT
    TO authenticated
    USING (
        EXISTS (
            SELECT 1 FROM users_dev 
            WHERE users_dev.id = auth.uid() 
            AND users_dev.role = 'interno_unique'
            AND (
                -- Usuário tem perfil RH no campo perfis_json
                users_dev.perfis_json::text ILIKE '%rh%'
                OR 
                -- Ou está associado a perfil que permite RH
                EXISTS (
                    SELECT 1 FROM users_perfis up
                    WHERE up.perfil_nome = ANY(
                        SELECT jsonb_array_elements_text(users_dev.perfis_json::jsonb)
                    )
                    AND up.modulo_codigo IN ('rh', 'recursos_humanos')
                    AND up.is_active = true
                )
            )
        )
    );

-- 4.1.4. POLÍTICAS PARA COLABORADORES - ACESSO AOS PRÓPRIOS DADOS
-- Colaboradores podem ver apenas seus próprios dados
CREATE POLICY "colaborador_self_access" ON rh_colaboradores
    FOR SELECT
    TO authenticated
    USING (
        user_id = auth.uid() -- Permite que o colaborador veja apenas seu próprio registro
    );

-- Colaboradores podem ver seu próprio histórico
CREATE POLICY "colaborador_self_historico" ON rh_historico_colaborador
    FOR SELECT
    TO authenticated
    USING (
        colaborador_id IN (
            SELECT id FROM rh_colaboradores WHERE user_id = auth.uid()
        )
    );

-- 4.1.5. POLÍTICAS PARA GESTORES - ACESSO AOS DADOS DA EQUIPE
-- Gestores podem ver dados dos colaboradores que reportam a eles
CREATE POLICY "gestor_team_access" ON rh_colaboradores
    FOR SELECT
    TO authenticated
    USING (
        -- Verifica se o usuário logado é gestor do colaborador no último registro do histórico
        id IN (
            SELECT DISTINCT h.colaborador_id 
            FROM rh_historico_colaborador h
            WHERE h.gestor_id IN (
                SELECT id FROM rh_colaboradores WHERE user_id = auth.uid()
            )
            AND h.data_evento = (
                SELECT MAX(data_evento) 
                FROM rh_historico_colaborador 
                WHERE colaborador_id = h.colaborador_id
            )
        )
    );

-- 4.1.6. POLÍTICAS PARA DADOS MESTRES (Cargos, Departamentos)
-- Todos os usuários autenticados podem VISUALIZAR dados mestres
CREATE POLICY "authenticated_read_cargos" ON rh_cargos
    FOR SELECT
    TO authenticated
    USING (true);

CREATE POLICY "authenticated_read_departamentos" ON rh_departamentos
    FOR SELECT
    TO authenticated
    USING (true);

-- Apenas admins e RH podem MODIFICAR dados mestres
CREATE POLICY "rh_admin_modify_cargos" ON rh_cargos
    FOR ALL
    TO authenticated
    USING (
        EXISTS (
            SELECT 1 FROM users_dev 
            WHERE users_dev.id = auth.uid() 
            AND (
                users_dev.role = 'admin'
                OR (
                    users_dev.role = 'interno_unique'
                    AND users_dev.perfis_json::text ILIKE '%rh%'
                )
            )
        )
    );

-- 4.1.7. TABELA DE LOG DE ACESSOS AO RH (Auditoria)
CREATE TABLE IF NOT EXISTS rh_access_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES auth.users(id),
    user_email TEXT,
    user_role TEXT,
    colaborador_acessado_id UUID REFERENCES rh_colaboradores(id),
    table_accessed TEXT,
    action_type TEXT, -- SELECT, INSERT, UPDATE, DELETE
    access_granted BOOLEAN,
    denial_reason TEXT,
    ip_address INET,
    user_agent TEXT,
    perfis_json TEXT,
    accessed_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    session_info JSONB
);

-- RLS para tabela de logs - apenas admins podem ver
ALTER TABLE rh_access_logs ENABLE ROW LEVEL SECURITY;

CREATE POLICY "admin_only_access_logs" ON rh_access_logs
    FOR ALL
    TO authenticated
    USING (
        EXISTS (
            SELECT 1 FROM users_dev 
            WHERE users_dev.id = auth.uid() 
            AND users_dev.role = 'admin'
        )
    );
```

### 4.2. Integração com Sistema de Perfis

O módulo RH deve respeitar o sistema de perfis existente (`user_perfis`, `perfil_access_service`).

**Perfis necessários para o módulo RH:**

```sql
-- Inserir perfis do módulo RH na tabela users_perfis
INSERT INTO users_perfis (perfil_nome, modulo_codigo, descricao, is_active) VALUES
('RH Administrador', 'rh', 'Acesso total ao módulo de RH - pode gerenciar colaboradores, realizar contratações, demissões e alterações', true),
('RH Analista', 'rh', 'Pode visualizar dados dos colaboradores e realizar operações básicas, mas não pode fazer demissões', true),
('RH Recrutamento', 'rh', 'Acesso focado em recrutamento - pode gerenciar vagas e candidatos', true),
('Gestor', 'rh', 'Pode visualizar dados da própria equipe e realizar avaliações de desempenho', true),
('Colaborador', 'rh', 'Acesso aos próprios dados e histórico - portal do colaborador', true);
```

**No código Python (`permissions.py` ou `decorators/perfil_decorators.py`):**

```python
def verificar_acesso_rh(nivel_acesso='visualizar'):
    """
    Decorator para verificar se o usuário tem permissão de acesso ao módulo RH
    
    Args:
        nivel_acesso: 'visualizar', 'editar', 'gerenciar', 'admin'
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            user_role = session.get('user', {}).get('role')
            user_perfis = session.get('user', {}).get('perfis_json', [])
            
            # Admins têm acesso total
            if user_role == 'admin':
                return f(*args, **kwargs)
            
            # Verificar se usuário tem perfil RH adequado
            perfis_rh = ['RH Administrador', 'RH Analista', 'RH Recrutamento']
            
            if nivel_acesso == 'admin':
                if 'RH Administrador' not in user_perfis:
                    abort(403)
            elif nivel_acesso == 'gerenciar':
                if not any(p in user_perfis for p in ['RH Administrador', 'RH Analista']):
                    abort(403)
            elif nivel_acesso == 'editar':
                if not any(p in user_perfis for p in perfis_rh):
                    abort(403)
            else:  # visualizar
                # Gestores e colaboradores podem visualizar dados específicos
                if not any(p in user_perfis for p in perfis_rh + ['Gestor', 'Colaborador']):
                    abort(403)
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator
```

---

## 5. Registro de Blueprints no app.py

### 5.1. Atualizar `modules/rh/__init__.py`

Seguir o padrão do módulo de importações:

```python
"""
Módulo de RH - UniSystem Portal
Gerencia todas as funcionalidades de Recursos Humanos
"""

from flask import Blueprint

__version__ = '1.0.0'
__author__ = 'UniSystem Team'

def register_rh_blueprints(app):
    """
    Registra todos os blueprints relacionados ao módulo de RH
    
    Args:
        app: Instância do Flask app
    """
    
    # Import blueprints (imports aqui para evitar circular imports)
    from modules.rh.recrutamento.routes import recrutamento_bp
    from modules.rh.colaboradores.routes import colaboradores_bp
    from modules.rh.desempenho.routes import desempenho_bp
    from modules.rh.estrutura_org.routes import estrutura_org_bp
    
    # Registrar blueprints
    app.register_blueprint(recrutamento_bp)
    app.register_blueprint(colaboradores_bp)
    app.register_blueprint(desempenho_bp)
    app.register_blueprint(estrutura_org_bp)
    
    print("✅ Módulo de RH registrado com sucesso")
```

### 5.2. Atualizar `app.py`

Adicionar após o registro do módulo financeiro:

```python
# Import RH blueprint and registration function
from modules.rh import register_rh_blueprints

# ... (outros registros)

# Register RH module
register_rh_blueprints(app)
```

---

## 6. API Endpoints REST

Criar endpoints REST seguindo o padrão da aplicação para permitir integração via API:

```python
# modules/rh/api.py

from flask import Blueprint, jsonify, request, session
from extensions import supabase_admin
from decorators.perfil_decorators import verificar_acesso_rh
import os

rh_api_bp = Blueprint('rh_api', __name__, url_prefix='/api/rh')

# API Bypass para testes
API_BYPASS_KEY = os.getenv('API_BYPASS_KEY')

def check_api_bypass():
    """Verifica se a requisição usa a chave de bypass para testes"""
    api_key = request.headers.get('X-API-Key')
    return api_key == API_BYPASS_KEY

@rh_api_bp.route('/colaboradores', methods=['GET'])
@verificar_acesso_rh('visualizar')
def get_colaboradores():
    """
    GET /api/rh/colaboradores
    Retorna lista de colaboradores com filtros
    
    Query Params:
        - status: 'Ativo', 'Inativo', 'Férias', 'Afastado'
        - departamento_id: UUID do departamento
        - cargo_id: UUID do cargo
        - gestor_id: UUID do gestor
    """
    if not check_api_bypass() and 'user' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    try:
        # Construir query com filtros
        query = supabase_admin.table('rh_colaboradores').select('*')
        
        # Aplicar filtros
        status = request.args.get('status')
        if status:
            query = query.eq('status', status)
        
        # Executar query
        response = query.execute()
        
        return jsonify({
            'success': True,
            'data': response.data,
            'count': len(response.data)
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@rh_api_bp.route('/colaboradores/<colaborador_id>', methods=['GET'])
@verificar_acesso_rh('visualizar')
def get_colaborador_detail(colaborador_id):
    """
    GET /api/rh/colaboradores/{id}
    Retorna detalhes completos de um colaborador incluindo histórico
    """
    if not check_api_bypass() and 'user' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    try:
        # Buscar colaborador
        colab_response = supabase_admin.table('rh_colaboradores')\
            .select('*')\
            .eq('id', colaborador_id)\
            .single()\
            .execute()
        
        # Buscar histórico
        hist_response = supabase_admin.table('rh_historico_colaborador')\
            .select('*, cargo:rh_cargos(nome_cargo), departamento:rh_departamentos(nome_departamento)')\
            .eq('colaborador_id', colaborador_id)\
            .order('data_evento', desc=True)\
            .execute()
        
        return jsonify({
            'success': True,
            'colaborador': colab_response.data,
            'historico': hist_response.data
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@rh_api_bp.route('/colaboradores', methods=['POST'])
@verificar_acesso_rh('gerenciar')
def create_colaborador():
    """
    POST /api/rh/colaboradores
    Cria um novo colaborador
    
    Body (JSON):
    {
        "nome_completo": "...",
        "cpf": "...",
        "data_nascimento": "YYYY-MM-DD",
        "data_admissao": "YYYY-MM-DD",
        "cargo_id": "uuid",
        "departamento_id": "uuid",
        "salario_mensal": 5000.00,
        ...
    }
    """
    if not check_api_bypass() and 'user' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    try:
        data = request.get_json()
        
        # Validar campos obrigatórios
        required_fields = ['nome_completo', 'cpf', 'data_nascimento', 'data_admissao']
        for field in required_fields:
            if field not in data:
                return jsonify({'error': f'Campo obrigatório: {field}'}), 400
        
        # Verificar se CPF já existe
        existing = supabase_admin.table('rh_colaboradores')\
            .select('id')\
            .eq('cpf', data['cpf'])\
            .execute()
        
        if existing.data:
            return jsonify({'error': 'CPF já cadastrado'}), 409
        
        # Inserir colaborador
        colab_response = supabase_admin.table('rh_colaboradores')\
            .insert({
                'nome_completo': data['nome_completo'],
                'cpf': data['cpf'],
                'data_nascimento': data['data_nascimento'],
                'data_admissao': data['data_admissao'],
                'status': 'Ativo'
            })\
            .execute()
        
        colaborador_id = colab_response.data[0]['id']
        
        # Criar registro de admissão no histórico
        supabase_admin.table('rh_historico_colaborador').insert({
            'colaborador_id': colaborador_id,
            'data_evento': data['data_admissao'],
            'tipo_evento': 'Admissão',
            'cargo_id': data.get('cargo_id'),
            'departamento_id': data.get('departamento_id'),
            'salario_mensal': data.get('salario_mensal'),
            'responsavel_id': session.get('user', {}).get('id')
        }).execute()
        
        return jsonify({
            'success': True,
            'colaborador_id': colaborador_id,
            'message': 'Colaborador criado com sucesso'
        }), 201
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Adicionar mais endpoints: UPDATE, DELETE, etc.
```

---

## 7. Integração com Serviços Existentes

### 7.1. Cache Service

Colaboradores ativos devem ser cacheados para performance:

```python
# Em modules/rh/colaboradores/routes.py

from services.data_cache import data_cache

@colaboradores_bp.route('/lista')
@verificar_acesso_rh('visualizar')
def lista_colaboradores():
    """Lista de colaboradores com cache"""
    user_id = session.get('user', {}).get('id')
    
    # Tentar obter do cache
    cached_colaboradores = data_cache.get_cache(user_id, 'rh_colaboradores_ativos')
    
    if cached_colaboradores:
        colaboradores = cached_colaboradores
    else:
        # Buscar do banco
        response = supabase_admin.table('rh_colaboradores')\
            .select('*')\
            .eq('status', 'Ativo')\
            .order('nome_completo')\
            .execute()
        
        colaboradores = response.data
        
        # Cachear por 1 hora (dados mestres mudam pouco)
        data_cache.set_cache(user_id, 'rh_colaboradores_ativos', colaboradores, expiry=3600)
    
    return render_template('colaboradores/lista_colaboradores.html', 
                         colaboradores=colaboradores)
```

### 7.2. Logging e Auditoria

Integrar com `services/access_logger.py`:

```python
from services.access_logger import log_access

@colaboradores_bp.route('/perfil/<colaborador_id>')
@verificar_acesso_rh('visualizar')
def perfil_colaborador(colaborador_id):
    """Perfil completo do colaborador com logging de acesso"""
    
    # Registrar acesso para auditoria
    log_access(
        module='rh',
        action='view_colaborador',
        resource_id=colaborador_id,
        details={'section': 'perfil_completo'}
    )
    
    # ... resto do código
```

### 7.3. Navigation Service

Adicionar itens de menu para o RH no `services/navigation_service.py`:

```python
# Adicionar ao dicionário de módulos
'rh': {
    'nome': 'Recursos Humanos',
    'icone': 'fa-users',
    'cor': '#6f42c1',  # Roxo
    'submenus': [
        {
            'nome': 'Colaboradores',
            'url': '/rh/colaboradores',
            'perfis': ['RH Administrador', 'RH Analista', 'Gestor']
        },
        {
            'nome': 'Recrutamento',
            'url': '/rh/recrutamento',
            'perfis': ['RH Administrador', 'RH Recrutamento']
        },
        {
            'nome': 'Avaliações',
            'url': '/rh/desempenho',
            'perfis': ['RH Administrador', 'RH Analista', 'Gestor']
        },
        {
            'nome': 'Estrutura Organizacional',
            'url': '/rh/estrutura',
            'perfis': ['RH Administrador']
        },
        {
            'nome': 'Meu Portal',
            'url': '/rh/colaboradores/portal',
            'perfis': ['Colaborador']
        }
    ]
}
```

---

## 8. Tratamento de Datas (Formato Brasileiro)

**CRÍTICO**: O sistema usa formato brasileiro DD/MM/YYYY no banco, mas ISO YYYY-MM-DD para filtragem.

```python
from datetime import datetime

def parse_brazilian_date(date_str):
    """
    Converte data em formato brasileiro para objeto datetime
    
    Args:
        date_str: String no formato DD/MM/YYYY
    
    Returns:
        datetime object
    """
    if not date_str:
        return None
    
    try:
        return datetime.strptime(date_str, '%d/%m/%Y')
    except ValueError:
        try:
            # Tentar formato ISO também
            return datetime.strptime(date_str, '%Y-%m-%d')
        except ValueError:
            return None

def format_date_to_brazilian(date_obj):
    """
    Formata datetime para formato brasileiro
    
    Args:
        date_obj: datetime object
    
    Returns:
        String no formato DD/MM/YYYY
    """
    if not date_obj:
        return ''
    
    if isinstance(date_obj, str):
        date_obj = parse_brazilian_date(date_obj)
    
    return date_obj.strftime('%d/%m/%Y') if date_obj else ''

# Usar em filtros Jinja2
@app.template_filter('brazilian_date')
def brazilian_date_filter(date_value):
    """Filtro Jinja2 para formatar datas"""
    return format_date_to_brazilian(date_value)
```

**No template HTML:**

```html
<!-- templates/colaboradores/perfil_colaborador.html -->
<p><strong>Data de Admissão:</strong> {{ colaborador.data_admissao | brazilian_date }}</p>
```

---

## 9. Upload de Arquivos (Currículos, Documentos)

O módulo RH precisará gerenciar uploads:

```python
# modules/rh/recrutamento/routes.py

import os
from werkzeug.utils import secure_filename
from flask import current_app

ALLOWED_EXTENSIONS = {'pdf', 'doc', 'docx', 'jpg', 'jpeg', 'png'}

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@recrutamento_bp.route('/candidato/upload', methods=['POST'])
def upload_curriculo():
    """Upload de currículo do candidato"""
    
    if 'curriculo' not in request.files:
        return jsonify({'error': 'Nenhum arquivo enviado'}), 400
    
    file = request.files['curriculo']
    
    if file.filename == '':
        return jsonify({'error': 'Nenhum arquivo selecionado'}), 400
    
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        
        # Criar diretório se não existir
        upload_folder = os.path.join(current_app.root_path, 'static', 'uploads', 'rh', 'curriculos')
        os.makedirs(upload_folder, exist_ok=True)
        
        # Adicionar timestamp ao nome do arquivo para evitar conflitos
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"{timestamp}_{filename}"
        
        filepath = os.path.join(upload_folder, filename)
        file.save(filepath)
        
        # Retornar caminho relativo
        relative_path = f"/static/uploads/rh/curriculos/{filename}"
        
        return jsonify({
            'success': True,
            'file_path': relative_path
        }), 200
    
    return jsonify({'error': 'Tipo de arquivo não permitido'}), 400
```

---

## 10. Estratégia de Testes

Seguindo o padrão da aplicação (prefixo `test_*`):

```python
# test_rh_api_colaboradores.py

import requests
import os

API_BYPASS_KEY = os.getenv('API_BYPASS_KEY', 'uniq_api_2025_dev_bypass_key')
BASE_URL = 'http://192.168.0.75:5000'
headers = {'X-API-Key': API_BYPASS_KEY, 'Content-Type': 'application/json'}

def test_get_colaboradores():
    """Testa endpoint de listagem de colaboradores"""
    response = requests.get(f'{BASE_URL}/api/rh/colaboradores', headers=headers)
    
    print(f"Status Code: {response.status_code}")
    print(f"Response: {response.json()}")
    
    assert response.status_code == 200
    assert 'data' in response.json()

def test_create_colaborador():
    """Testa criação de colaborador"""
    payload = {
        'nome_completo': 'João Teste Silva',
        'cpf': '123.456.789-00',
        'data_nascimento': '1990-01-15',
        'data_admissao': '2025-01-02',
        'email_corporativo': 'joao.teste@uniqueaduaneira.com.br'
    }
    
    response = requests.post(
        f'{BASE_URL}/api/rh/colaboradores',
        json=payload,
        headers=headers
    )
    
    print(f"Status Code: {response.status_code}")
    print(f"Response: {response.json()}")
    
    assert response.status_code == 201
    assert 'colaborador_id' in response.json()
    
    return response.json()['colaborador_id']

if __name__ == '__main__':
    print("=== Testando API RH ===")
    test_get_colaboradores()
    colaborador_id = test_create_colaborador()
    print(f"\n✅ Testes concluídos. Colaborador criado: {colaborador_id}")
```

**LEMBRETE**: Sempre deletar arquivos `test_*` após validação!

---

## 11. Estilização e UI

### 11.1. Cores do Módulo RH

Seguir o padrão de cores da aplicação. Sugestão para RH:

```css
/* static/rh/css/rh_global.css */

:root {
    --rh-primary: #6f42c1;      /* Roxo - representa pessoas/RH */
    --rh-secondary: #9b72d4;
    --rh-success: #28a745;
    --rh-warning: #ffc107;
    --rh-danger: #dc3545;
    --rh-info: #17a2b8;
    --rh-light: #f8f9fa;
    --rh-dark: #343a40;
}

.rh-card {
    border-left: 4px solid var(--rh-primary);
}

.rh-badge-ativo {
    background-color: var(--rh-success);
    color: white;
    padding: 4px 8px;
    border-radius: 4px;
}

.rh-badge-inativo {
    background-color: var(--rh-danger);
    color: white;
    padding: 4px 8px;
    border-radius: 4px;
}
```

### 11.2. Template Base

Extender sempre de `base.html`:

```html
<!-- templates/colaboradores/lista_colaboradores.html -->
{% extends "base.html" %}

{% block title %}Colaboradores - RH{% endblock %}

{% block styles %}
<link rel="stylesheet" href="{{ url_for('static', filename='rh/css/colaboradores.css') }}">
{% endblock %}

{% block content %}
<div class="container-fluid mt-4">
    <h2><i class="fas fa-users"></i> Gestão de Colaboradores</h2>
    
    <!-- Conteúdo -->
</div>
{% endblock %}

{% block scripts %}
<script src="{{ url_for('static', filename='rh/js/colaboradores.js') }}"></script>
{% endblock %}
```

---

## 12. Checklist de Implementação

Ao implementar cada submódulo, seguir este checklist:

- [ ] DDL criado e executado no banco
- [ ] RLS habilitado e políticas criadas
- [ ] Perfis de acesso configurados em `users_perfis`
- [ ] Blueprint criado em `routes.py`
- [ ] Blueprint registrado em `__init__.py` do módulo
- [ ] Função de registro adicionada ao `app.py`
- [ ] Endpoints REST criados com API bypass
- [ ] Decorators de permissão aplicados
- [ ] Cache implementado onde necessário
- [ ] Logging de acessos configurado
- [ ] Templates HTML criados extendendo `base.html`
- [ ] CSS com cores do módulo
- [ ] JavaScript para interatividade
- [ ] Formatação de datas brasileiras
- [ ] Arquivo de teste `test_*.py` criado
- [ ] Testes executados e validados
- [ ] Arquivo de teste deletado
- [ ] Documentação atualizada

---

## 13. Próximos Passos

1. **Revisar e aprovar este documento de integração**
2. **Executar DDL completo (tabelas + RLS)**
3. **Implementar submódulo por submódulo** na seguinte ordem:
   - Estrutura Organizacional (dados mestres)
   - Colaboradores (coração do sistema)
   - Recrutamento
   - Desempenho
4. **Criar arquivo de testes para cada submódulo**
5. **Validar integração com sistema existente**

---

**IMPORTANTE**: Este documento complementa o plano de desenvolvimento inicial e garante que o módulo RH esteja completamente integrado com a arquitetura existente do UniSystem Portal, seguindo todos os padrões estabelecidos.
