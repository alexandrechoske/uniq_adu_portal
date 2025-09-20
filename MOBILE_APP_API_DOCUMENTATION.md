# Documentação API - Aplicativo Mobile UniSystem Portal
## Especificação para Dashboard Executivo de Importações

---

## 📱 **RESUMO EXECUTIVO**

### Objetivo
Desenvolver um aplicativo mobile minimalista com foco em UX/UI otimizada para clientes visualizarem seus dados de importações, baseado no Dashboard Executivo do portal web.

### Público-Alvo
- **Clientes (role: `cliente_unique`)**: Visualizam apenas dados das empresas vinculadas à sua conta
- Interface mobile responsiva e intuitiva
- Foco em KPIs essenciais e operações recentes

---

## 🏗️ **ARQUITETURA DO SISTEMA**

### Tecnologias Base
- **Backend**: Flask (Python) com blueprints modulares
- **Banco de Dados**: Supabase (PostgreSQL) com Row Level Security (RLS)
- **Cache**: Sistema híbrido (sessão + servidor) com DataCacheService
- **Autenticação**: JWT com roles e perfis granulares

### Padrão Cache-First
```python
# Fluxo de dados otimizado
1. Login → Preload de 30-365 dias de dados
2. Armazenamento: session['cached_data'] + DataCacheService
3. APIs usam cache primeiro, DB como fallback
4. Refresh manual via /api/force-refresh
```

---

## 🔐 **SISTEMA DE AUTENTICAÇÃO**

### Endpoints de Autenticação

#### **POST /auth/login**
```json
// Request
{
  "email": "cliente@empresa.com", 
  "password": "senha123"
}

// Response Success
{
  "success": true,
  "user": {
    "id": "user_uuid",
    "email": "cliente@empresa.com",
    "name": "Nome Cliente",
    "role": "cliente_unique",
    "perfil_principal": "cliente_basico",
    "user_companies": ["12345678000199", "98765432000188"],
    "user_companies_info": [
      {
        "id": "cliente_sistema_uuid",
        "nome": "Empresa Exemplo LTDA",
        "cnpjs": ["12345678000199"],
        "quantidade_cnpjs": 1
      }
    ],
    "user_perfis": ["cliente_importacoes"],
    "user_perfis_info": [
      {
        "perfil_nome": "cliente_importacoes",
        "modulos": [
          {
            "codigo": "importacoes",
            "nome": "Importações",
            "paginas": ["dashboard_executivo", "relatorios"]
          }
        ]
      }
    ]
  }
}
```

#### **GET /auth/api/session-info**
```json
// Response
{
  "authenticated": true,
  "user": { /* dados do usuário */ },
  "session_age": 3600,
  "expires_in": 39600
}
```

#### **POST /auth/logout**
```json
// Response
{
  "success": true,
  "message": "Logout realizado com sucesso"
}
```

### Roles e Permissões
- **`cliente_unique`**: Acesso apenas às suas empresas vinculadas
- **`interno_unique`**: Acesso ampliado por perfil
- **`admin`**: Acesso total

### API Bypass (Para Testes)
```bash
# Header para testes sem autenticação
X-API-Key: uniq_api_2025_dev_bypass_key
```

---

## 📊 **DASHBOARD EXECUTIVO - APIs CORE**

### **GET /dashboard-executivo/api/load-data**
Carrega dados base de importações

```json
// Response
{
  "success": true,
  "data": [
    {
      "ref_unique": "BR_2024_001234",
      "importador": "Empresa Exemplo LTDA",
      "cnpj_importador": "12345678000199",
      "mercadoria": "Componentes Eletrônicos",
      "modal": "AEREA",
      "canal": "Verde",
      "status_processo": "Processo em Trânsito",
      "status_timeline": "2 - Agd Chegada",
      "data_abertura": "15/01/2024",
      "data_embarque": "20/01/2024",
      "data_chegada": "25/01/2024",
      "custo_total": 15750.50,
      "timeline_number": 2,
      "despesas_processo": "[{\"categoria\":\"Frete\",\"valor_custo\":12000}]"
    }
  ],
  "total_records": 150
}
```

### **GET /dashboard-executivo/api/kpis**
KPIs executivos principais

```json
// Response
{
  "success": true,
  "kpis": {
    "total_processos": 150,
    "processos_abertos": 120,
    "processos_fechados": 30,
    "total_despesas": 2875350.75,
    "ticket_medio": 19168.67,
    "agd_embarque": 25,      // Timeline 1
    "agd_chegada": 35,       // Timeline 2  
    "agd_liberacao": 40,     // Timeline 3
    "agd_fechamento": 20,    // Timeline 4
    "chegando_mes": 18,
    "chegando_mes_custo": 285750.30,
    "chegando_semana": 5,
    "chegando_semana_custo": 75250.80
  }
}
```

### **GET /dashboard-executivo/api/charts**
Dados para gráficos

```json
// Response
{
  "success": true,
  "charts": {
    "modal_distribution": {
      "AEREA": 45,
      "MARITIMA": 85, 
      "TERRESTRE": 20
    },
    "status_timeline": {
      "1 - Agd Embarque": 25,
      "2 - Agd Chegada": 35,
      "3 - Agd Liberação": 40,
      "4 - Agd Fechamento": 20
    },
    "monthly_trend": [
      {"month": "Janeiro", "processos": 45, "custos": 675000},
      {"month": "Fevereiro", "processos": 52, "custos": 780000}
    ]
  }
}
```

### **GET /dashboard-executivo/api/recent-operations**
Operações recentes (últimas 10)

```json
// Response
{
  "success": true,
  "operations": [
    {
      "ref_unique": "BR_2024_001234",
      "importador": "Empresa Exemplo",
      "mercadoria": "Componentes Eletrônicos",
      "modal": "AEREA",
      "status_timeline": "2 - Agd Chegada",
      "data_abertura": "15/01/2024",
      "custo_total": 15750.50,
      "timeline_color": "#ff9800"
    }
  ]
}
```

### **GET /dashboard-executivo/api/filter-options**
Opções para filtros

```json
// Response
{
  "success": true,
  "filters": {
    "materiais": ["Componentes Eletrônicos", "Máquinas", "Produtos Químicos"],
    "clientes": ["Empresa A", "Empresa B", "Empresa C"],
    "modais": ["AEREA", "MARITIMA", "TERRESTRE"],
    "canais": ["Verde", "Amarelo", "Vermelho"],
    "status": ["aberto", "fechado"]
  }
}
```

### **POST /dashboard-executivo/api/force-refresh**
Força atualização do cache

```json
// Request
{
  "clear_cache": true
}

// Response  
{
  "success": true,
  "message": "Cache atualizado com sucesso",
  "records_loaded": 150
}
```

---

## 🔍 **SISTEMA DE FILTROS**

### Filtros Disponíveis (via Query Parameters)
```bash
GET /dashboard-executivo/api/kpis?data_inicio=2024-01-01&data_fim=2024-03-31&material=eletrônicos&cliente=empresa&modal=aerea&canal=verde&status_processo=aberto
```

### Parâmetros Suportados
- **`data_inicio`**: YYYY-MM-DD
- **`data_fim`**: YYYY-MM-DD  
- **`material`**: Busca por substring (case-insensitive)
- **`cliente`**: Busca por substring (case-insensitive)
- **`modal`**: AEREA|MARITIMA|TERRESTRE
- **`canal`**: Verde|Amarelo|Vermelho
- **`status_processo`**: aberto|fechado

---

## 📱 **ESTRUTURA MOBILE RECOMENDADA**

### Telas Principais

#### **1. Login**
- Email/Password simples
- Checkbox "Lembrar de mim"
- Link "Esqueci a senha"
- Branding dinâmico por cliente

#### **2. Dashboard Principal**
```
┌─────────────────────────────┐
│ 📊 Dashboard Importações    │
├─────────────────────────────┤
│ [🔍 Filtros] [📊 KPIs]      │
├─────────────────────────────┤
│ ┌─────────┐ ┌─────────┐     │
│ │150      │ │120      │     │
│ │Processos│ │Abertos  │     │
│ └─────────┘ └─────────┘     │
│ ┌─────────┐ ┌─────────┐     │  
│ │R$2.8M   │ │R$19K    │     │
│ │Total    │ │Ticket   │     │
│ └─────────┘ └─────────┘     │
├─────────────────────────────┤
│ 📈 Gráfico Modal/Status     │
├─────────────────────────────┤  
│ 📋 Operações Recentes       │
│ • BR_2024_001234 - Agd...   │
│ • BR_2024_001235 - Emb...   │
└─────────────────────────────┘
```

#### **3. Filtros (Modal/Drawer)**
- Date picker para período
- Multi-select para materiais/clientes
- Toggle para modais
- Chip para canal aduaneiro

#### **4. Detalhes do Processo**
- Timeline visual do status
- Informações da mercadoria
- Custos detalhados
- Documentos (se disponível)

### Navegação
- **Bottom Navigation**: Dashboard | Filtros | Notificações | Perfil
- **Pull-to-refresh** nas listas
- **Infinite scroll** se necessário
- **Offline mode** com cache local

---

## 🔄 **FLUXO DE DADOS MOBILE**

### 1. Inicialização do App
```python
# 1. Verificar token salvo
# 2. Validar sessão: GET /auth/api/session-info
# 3. Se válido, carregar dados: GET /dashboard-executivo/api/bootstrap
# 4. Se inválido, tela de login
```

### 2. Login
```python
# 1. POST /auth/login
# 2. Salvar token/sessão
# 3. Preload dados: GET /dashboard-executivo/api/load-data
# 4. Navegar para dashboard
```

### 3. Dashboard
```python
# 1. Carregar KPIs: GET /dashboard-executivo/api/kpis  
# 2. Carregar gráficos: GET /dashboard-executivo/api/charts
# 3. Carregar operações: GET /dashboard-executivo/api/recent-operations
# 4. Cache local para navegação offline
```

### 4. Filtros
```python
# 1. Carregar opções: GET /dashboard-executivo/api/filter-options
# 2. Aplicar filtros via query params em todas as APIs
# 3. Atualizar dashboard com dados filtrados
```

---

## ⚡ **OTIMIZAÇÕES DE PERFORMANCE**

### Cache Strategy
- **Local**: AsyncStorage/SQLite para dados offline
- **Memoria**: Redux/Context para estado global
- **API**: Cache-first com invalidação manual

### Loading States
- **Skeleton screens** durante carregamento
- **Progressive loading** dos componentes
- **Error boundaries** para falhas de rede

### Data Sync
- **Pull-to-refresh** para atualização manual
- **Background sync** quando app voltar ao foreground
- **Delta sync** apenas de dados modificados

---

## 🎨 **GUIDELINES DE UI/UX**

### Design System
- **Cores**: Palette baseada no branding do cliente
- **Tipografia**: Sans-serif legível (16px mínimo)
- **Ícones**: Material Design Icons
- **Espaçamento**: Grid 8px

### Componentes Core
```javascript
// Card KPI
<KpiCard 
  title="Processos Abertos"
  value={120}
  icon="folder-open"
  color="primary"
  onPress={() => navigateToDetails('processos_abertos')}
/>

// Status Timeline
<StatusTimeline 
  current={2}
  steps={[
    {id: 1, title: "Agd Embarque", icon: "ship-wheel"},
    {id: 2, title: "Agd Chegada", icon: "map-marker"},
    {id: 3, title: "Agd Liberação", icon: "check-circle"},
    {id: 4, title: "Agd Fechamento", icon: "archive"}
  ]}
/>

// Process Card
<ProcessCard
  refUnique="BR_2024_001234"
  company="Empresa Exemplo"
  material="Componentes Eletrônicos"
  status="Agd Chegada"
  cost={15750.50}
  modal="AEREA"
  onPress={() => navigateToDetails(refUnique)}
/>
```

### Padrões de Interação
- **Tap**: Navegação/Seleção
- **Long press**: Menu contextual  
- **Swipe**: Ações rápidas (atualizar, arquivar)
- **Pull down**: Refresh
- **Pinch**: Zoom em gráficos

---

## 🧪 **AMBIENTE DE TESTES**

### API Bypass
```bash
# Headers para todas as requisições de teste
X-API-Key: uniq_api_2025_dev_bypass_key
Content-Type: application/json
```

### URLs Base
```bash
# Desenvolvimento
BASE_URL=http://localhost:5000

# Staging  
BASE_URL=https://staging.unisystem.com.br

# Produção
BASE_URL=https://portal.unisystem.com.br
```

### Dados de Teste
```json
// Usuário de teste
{
  "email": "cliente.teste@empresa.com",
  "password": "senha123",
  "role": "cliente_unique"
}
```

---

## 🔒 **SEGURANÇA E PRIVACIDADE**

### Headers de Segurança
```bash
X-Content-Type-Options: nosniff
X-Frame-Options: DENY  
X-XSS-Protection: 1; mode=block
Content-Security-Policy: default-src 'self'
```

### Controle de Acesso
- **RLS (Row Level Security)** no banco
- **Filtros por empresa** automáticos
- **Token refresh** a cada 12 horas
- **Logs de acesso** completos

### Dados Sensíveis
- **Não armazenar** senhas no app
- **Criptografar** tokens salvos localmente
- **Mascarar** CNPJs em logs
- **Timeout** automático da sessão

---

## 📋 **CHECKLIST DE DESENVOLVIMENTO**

### Backend (APIs)
- ✅ Autenticação JWT implementada
- ✅ Filtros por empresa funcionando
- ✅ Cache system otimizado
- ✅ APIs de KPIs prontas
- ✅ Sistema de permissões ativo

### Frontend Mobile
- [ ] Setup do projeto (React Native/Flutter)
- [ ] Implementar autenticação
- [ ] Telas principais (Login, Dashboard)
- [ ] Componentes KPI cards
- [ ] Sistema de filtros
- [ ] Cache local
- [ ] Testes automatizados

### QA & Deploy
- [ ] Testes de integração
- [ ] Validação de segurança
- [ ] Performance testing
- [ ] Deploy staging
- [ ] Homologação cliente
- [ ] Deploy produção

---

## 📞 **CONTATOS E SUPORTE**

### Desenvolvedores Backend
- **Sistema**: UniSystem Portal
- **API Base**: Flask + Supabase
- **Documentação**: Este documento

### Próximos Passos
1. **Definir stack mobile** (React Native vs Flutter)
2. **Setup ambiente desenvolvimento**
3. **Implementar MVP** (Login + Dashboard básico)
4. **Testes integração** com APIs existentes
5. **Iterações UX** baseadas em feedback

---

**Documento gerado em:** 18/09/2025  
**Versão:** 1.0  
**Status:** Análise Completa - Pronto para Desenvolvimento
