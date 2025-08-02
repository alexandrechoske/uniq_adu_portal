# Dashboard Importações Resumido - Documentação

## Visão Geral

O módulo `dash_importacoes_resumido` é uma implementação em Flask que replica a funcionalidade da tela Streamlit de dashboard de importações, apresentando uma interface escura similar ao design original com tabela resumida e indicadores em tempo real.

## Estrutura do Módulo

```
modules/dash_importacoes_resumido/
├── __init__.py                           # Exportação do blueprint
├── routes.py                            # Rotas e lógica de negócio
├── static/dash_importacoes_resumido/
│   ├── dashboard.css                    # Estilos visuais
│   └── dashboard.js                     # Lógica frontend
└── templates/dash_importacoes_resumido/
    └── dash_importacoes_resumido.html   # Template principal
```

## Características Implementadas

### 1. Interface Visual
- **Tema escuro** inspirado no design original Streamlit
- **Layout responsivo** com 3 seções principais:
  - Cabeçalho com métricas e informações
  - Tabela de dados paginada
  - Rodapé com copyright e cotações de moedas

### 2. Funcionalidades do Cabeçalho
- **Título do Dashboard** em destaque
- **Informações de paginação** (Página X / Y)
- **Total de processos** com contagem por modal de transporte:
  - 🚤 Marítimo (modal "1")
  - ✈️ Aéreo (modal "4") 
  - 🚚 Terrestre (modal "7")
- **Logo da empresa** centralizado
- **Horário e data** atualizados em tempo real

### 3. Tabela de Dados
Colunas implementadas:
- **MODAL**: Ícone do tipo de transporte
- **NUM**: Número sequencial
- **REF UNIQUE**: Referência única do processo
- **REF IMPORTADOR**: Referência do importador
- **ORIGEM**: Local de origem
- **DATA EMBARQUE**: Data de embarque (com coloração condicional)
- **DATA CHEGADA**: Data de chegada
- **REGISTRO DI**: Data de registro da DI
- **CANAL**: Indicador circular colorido (Verde/Amarelo/Vermelho)
- **DATA ENTREGA**: Data de entrega

### 4. Funcionalidades Interativas
- **Paginação**: Navegação entre páginas de dados
- **Filtro por data de embarque**: Checkbox para mostrar apenas registros com data preenchida
- **Auto-refresh**: Atualização automática a cada 30 segundos
- **Refresh manual**: Botão para atualização sob demanda

### 5. Rodapé
- **Copyright** e logo da Unique
- **Cotações de moedas**: Dólar e Euro em tempo real (via API Banco Central)

## Endpoints

### `GET /dash-importacoes-resumido/`
Página principal do dashboard.
- **Autenticação**: Obrigatória
- **Permissão**: `dashboard_executivo.visualizar`
- **Retorno**: Template HTML da página

### `GET /dash-importacoes-resumido/api/data`
API para obter dados do dashboard.
- **Autenticação**: Obrigatória
- **Parâmetros**:
  - `page`: Número da página (default: 1)
  - `per_page`: Registros por página (default: 10)
  - `filtro_embarque`: 'preenchida' para filtrar por data de embarque
- **Retorno**: JSON com dados e metadados

### `GET /dash-importacoes-resumido/test`
Endpoint de teste para validação do módulo.
- **Retorno**: JSON com status e timestamp

## Estrutura de Dados

### Resposta da API `/api/data`:
```json
{
  "success": true,
  "header": {
    "total_processos": 128,
    "count_maritimo": 88,
    "count_aereo": 40,
    "count_terrestre": 0,
    "current_time": "23:39",
    "current_date": "2 AGOSTO",
    "exchange_rates": {
      "dolar": 5.5428,
      "euro": 6.4039
    }
  },
  "data": [
    {
      "modal": "1",
      "modal_icon": "mdi-ship",
      "numero": 1,
      "ref_unique": "UN25/5724",
      "ref_importador": "AZ8128/25/MP",
      "origem": "GENOVA",
      "data_embarque": "15/07/2025",
      "data_chegada": "02/08/2025",
      "registro_di": "01/08/2025",
      "canal": "Verde",
      "canal_color": "#4CAF50",
      "data_entrega": "03/08/2025"
    }
  ],
  "pagination": {
    "total": 128,
    "pages": 13,
    "current_page": 1,
    "per_page": 10
  }
}
```

## Configuração e Deploy

### 1. Registro no App Principal
O módulo é registrado automaticamente no `app.py`:

```python
# Import
from modules.dash_importacoes_resumido import dash_importacoes_resumido_bp

# Registration
app.register_blueprint(dash_importacoes_resumido_bp)
```

### 2. Dependências
- Flask
- Supabase (via extensions)
- Pandas
- Requests (para cotações)
- DataCacheService

### 3. Permissões Necessárias
- `dashboard_executivo.visualizar` (reutiliza permissão existente)

## Testes

Arquivo de teste: `test_dash_importacoes_resumido.py`

### Executar testes:
```bash
python test_dash_importacoes_resumido.py
```

### Validações realizadas:
- ✅ Endpoint de teste básico
- ✅ Acesso à página principal
- ✅ API de dados (com tratamento de cache vazio)
- ✅ Existência de arquivos estáticos
- ✅ Existência de templates

## Notas de Implementação

### Compatibilidade com Streamlit
O módulo foi projetado para replicar a funcionalidade e aparência da aplicação Streamlit original, mantendo:
- Mesma estrutura visual (cabeçalho, tabela, rodapé)
- Mesmas cores e tipografia
- Mesmo comportamento de paginação
- Mesmas funcionalidades de filtro

### Performance
- **Cache de dados**: Utiliza DataCacheService para evitar consultas desnecessárias
- **Auto-refresh inteligente**: Pausa quando usuário está interagindo
- **Paginação eficiente**: Carrega apenas dados da página atual

### Responsividade
- Design adaptável para diferentes tamanhos de tela
- Layout em grid responsivo
- Elementos colapsáveis em dispositivos móveis

## URLs de Acesso

- **Dashboard**: `/dash-importacoes-resumido/`
- **API de dados**: `/dash-importacoes-resumido/api/data`
- **Teste**: `/dash-importacoes-resumido/test`

## Status do Desenvolvimento

✅ **Completo**: Estrutura base, rotas, templates, estilos, JavaScript
✅ **Testado**: Módulo validado e funcionando
✅ **Integrado**: Registrado no app principal
⏳ **Próximos passos**: Integração com menu principal, testes com dados reais
