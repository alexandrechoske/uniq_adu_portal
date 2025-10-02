# 📦 Módulo de Importações - UniSystem Portal

## 📋 Visão Geral

Este módulo consolida todas as funcionalidades relacionadas a importações aduaneiras do UniSystem Portal. Ele foi organizado seguindo as melhores práticas de modularização e mantém consistência com o módulo `financeiro`.

## 🗂️ Estrutura do Módulo

```
importacoes/
├── __init__.py                    # Registra todos os blueprints do módulo
├── agente/                        # Gestão de agente de atendimento
│   ├── routes.py
│   ├── templates/
│   └── static/
├── analytics/                     # Analytics e estatísticas de acesso
│   ├── routes.py
│   ├── templates/
│   └── static/
├── conferencia/                   # Conferência de importações
│   ├── routes.py
│   ├── templates/
│   └── static/
├── dashboards/                    # Dashboards de visualização
│   ├── executivo/                 # Dashboard executivo
│   │   ├── routes.py
│   │   ├── templates/
│   │   └── static/
│   ├── operacional/               # Dashboard operacional
│   │   ├── routes.py
│   │   ├── templates/
│   │   └── static/
│   └── resumido/                  # Dashboard resumido de importações
│       ├── routes.py
│       ├── templates/
│       └── static/
├── export_relatorios/             # Exportação de relatórios
│   ├── routes.py
│   ├── templates/
│   └── static/
└── relatorios/                    # Geração de relatórios
    ├── routes.py
    ├── templates/
    └── static/
```

## 🔧 Como Usar

### Registrando o Módulo

No arquivo principal `app.py`:

```python
from modules.importacoes import register_importacoes_blueprints

# Registrar todos os blueprints do módulo
register_importacoes_blueprints(app)
```

Isso registrará automaticamente todos os sub-módulos:
- Agente
- Analytics
- Conferência
- Dashboard Executivo
- Dashboard Operacional
- Dashboard Resumido
- Relatórios
- Export Relatórios

## 📌 Sub-módulos

### 1. **Agente** (`/agente/`)
Gestão do agente de atendimento automatizado.

**Principais Rotas:**
- `GET /agente/` - Página principal do agente
- `POST /agente/ajax/add-numero` - Adicionar número de WhatsApp
- `GET /agente/admin` - Painel administrativo
- `GET /agente/api/admin/users-summary` - Resumo de usuários

**Funcionalidades:**
- Gerenciamento de números de WhatsApp
- Adesão ao sistema de agente
- Painel administrativo para gestão de usuários
- Analytics de interações

### 2. **Analytics** (`/analytics/`)
Sistema de estatísticas e análise de acessos.

**Principais Rotas:**
- `GET /analytics/` - Dashboard de analytics
- `GET /analytics/agente` - Analytics específico do agente
- `GET /analytics/api/stats` - API de estatísticas
- `GET /analytics/api/charts` - Dados para gráficos

**Funcionalidades:**
- Rastreamento de acessos
- Estatísticas de uso do sistema
- Análise de comportamento de usuários
- KPIs de engajamento

### 3. **Conferência** (`/conferencia/`)
Conferência e validação de documentos de importação.

**Principais Rotas:**
- `GET /conferencia/` - Página principal
- `GET /conferencia/simple` - Interface simplificada
- `POST /conferencia/simple/analyze` - Análise de documentos
- `GET /conferencia/simple/health` - Health check

**Funcionalidades:**
- Upload e análise de documentos
- Validação de dados de importação
- Integração com Gemini AI para processamento
- Geração de relatórios de conferência

### 4. **Dashboard Executivo** (`/dashboard-executivo/`)
Dashboard estratégico com visão consolidada.

**Principais Rotas:**
- `GET /dashboard-executivo/` - Dashboard principal
- `GET /dashboard-executivo/api/kpis` - KPIs executivos
- `GET /dashboard-executivo/api/charts` - Gráficos estratégicos
- `GET /dashboard-executivo/api/monthly-chart` - Gráfico mensal
- `POST /dashboard-executivo/api/force-refresh` - Forçar atualização de cache

**Funcionalidades:**
- KPIs estratégicos de importações
- Análise de tendências mensais
- Filtragem por empresa e período
- Permissões baseadas em perfil de usuário

### 5. **Dashboard Operacional** (`/dashboard-operacional/`)
Dashboard operacional com foco em tarefas diárias.

**Principais Rotas:**
- `GET /dashboard-operacional/` - Dashboard principal
- `GET /dashboard-operacional/api/data` - Dados operacionais
- `GET /dashboard-operacional/api/client-modals` - Modais por cliente
- `GET /dashboard-operacional/api/client-processes` - Processos por cliente
- `GET /dashboard-operacional/api/analyst-clients` - Clientes por analista

**Funcionalidades:**
- Visualização de processos em andamento
- Agrupamento por cliente e analista
- Calendário de operações
- Detalhamento de processos por dia

### 6. **Dashboard Resumido** (`/dash-importacoes-resumido/`)
Dashboard simplificado com informações essenciais.

**Principais Rotas:**
- `GET /dash-importacoes-resumido/` - Dashboard resumido
- `GET /dash-importacoes-resumido/api/data` - Dados do dashboard
- `GET /dash-importacoes-resumido/api/companies` - Lista de empresas
- `GET /dash-importacoes-resumido/api/companies-info` - Informações detalhadas

**Funcionalidades:**
- Visão rápida de importações
- Filtros simplificados
- Dados agregados por empresa
- Interface otimizada para performance

### 7. **Relatórios** (`/relatorios/`)
Geração de relatórios customizados.

**Principais Rotas:**
- `GET /relatorios/` - Página de relatórios
- `POST /relatorios/pdf` - Gerar PDF

**Funcionalidades:**
- Geração de relatórios em PDF
- Customização de filtros
- Templates predefinidos
- Export de dados

### 8. **Export Relatórios** (`/export_relatorios/`)
Exportação de bases de dados e relatórios históricos.

**Principais Rotas:**
- `GET /export_relatorios/` - Página de exportação
- `GET /export_relatorios/api/processos_antigos` - Processos históricos
- `POST /export_relatorios/api/search` - Busca de processos
- `POST /export_relatorios/api/export_csv` - Exportar CSV

**Funcionalidades:**
- Busca de processos antigos
- Exportação em CSV
- Filtros avançados de busca
- Download de bases históricas

## 🔐 Controle de Acesso

Todos os sub-módulos respeitam o sistema de controle de acesso baseado em perfis:

- **`admin`**: Acesso completo a todos os módulos
- **`interno_unique`**: Acesso a todos os dados da empresa
- **`cliente_unique`**: Acesso filtrado por empresas associadas

## 🎨 Assets Estáticos

Cada sub-módulo tem sua própria pasta `static/` com:
- CSS específico do módulo
- JavaScript específico do módulo
- Imagens e ícones

Os assets são servidos através dos blueprints respectivos.

## 📊 Cache e Performance

- Usa cache baseado em sessão (`session['cached_data']`)
- Fallback para `DataCacheService` server-side
- Pré-carregamento de dados durante login (30-365 dias)
- Timeout configurável para operações pesadas

## 🧪 Testes

Para testar o módulo:

```bash
# Teste de importações
python test_reorganizacao_importacoes.py

# Iniciar aplicação em modo debug
python app.py
```

## 📝 Convenções de Código

- Blueprints registrados com prefixos de URL claros
- Templates organizados por módulo
- API endpoints sempre com prefixo `/api/`
- Rotas de debug/teste com prefixo apropriado

## 🔗 Integração com Outros Módulos

### Módulos Compartilhados:
- **Auth**: Autenticação e sessões
- **Menu**: Navegação principal
- **Config**: Configurações globais
- **Shared**: Assets e utilitários compartilhados

### Serviços Utilizados:
- `DataCacheService`: Cache de dados
- `PerfilAccessService`: Controle de acesso
- `AuthLoggingIntegration`: Logs de autenticação
- `MaterialCleaner`: Categorização de materiais (se aplicável)

## 📞 Suporte

Para dúvidas ou problemas relacionados ao módulo de importações, consulte:
- Documentação principal: `/docs/`
- Log de reorganização: `/docs/REORGANIZACAO_MODULO_IMPORTACOES.md`
- Instruções do Copilot: `.github/copilot-instructions.md`

---

**Última atualização**: 01/10/2025  
**Versão**: 1.0.0  
**Mantido por**: UniSystem Team
