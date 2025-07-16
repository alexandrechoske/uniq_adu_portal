# DOCUMENTAÇÃO - Dashboard V2 e Materiais V2

## Resumo das Mudanças

### 1. **Nova Arquitetura Unificada**
- **Dashboard V2**: Página unificada com abas (Dashboard Executivo + Análise de Materiais)
- **Fonte de Dados**: Nova view `vw_importacoes_6_meses` (dados dos últimos 6 meses)
- **Carregamento Único**: Um único carregamento inicial para ambas as abas
- **Interface Simplificada**: CSS e JS mínimos para funcionalidade básica

### 2. **Arquivos Criados**

#### Backend (Routes)
- `routes/dashboard_v2.py` - Novo controller unificado
- `routes/materiais_v2.py` - Controller para análise de materiais

#### Frontend (Templates)
- `templates/dashboard_v2/index.html` - Template unificado com abas

#### Utilitários
- `test_view_6_meses.py` - Script para testar a nova view

### 3. **Estrutura da Nova View**

A view `vw_importacoes_6_meses` contém as seguintes colunas principais:
- `ref_unique` - Referência única do processo
- `importador` - Nome do importador/cliente
- `data_abertura` - Data de abertura do processo
- `modal` - Modal de transporte (AÉREA, MARÍTIMA, RODOVIÁRIA)
- `mercadoria` - Descrição da mercadoria
- `valor_cif_real` - Valor CIF real
- `custo_total` - Custo total do processo
- `status_processo` - Status atual do processo
- `canal` - Canal de desembaraço
- `urf_entrada` - URF de entrada
- `data_embarque` - Data de embarque
- `data_chegada` - Data de chegada
- `exportador_fornecedor` - Exportador/fornecedor

### 4. **Fluxo de Funcionamento**

1. **Login** → Tela de carregamento
2. **Carregamento Inicial** → Busca dados da `vw_importacoes_6_meses`
3. **Armazenamento** → Dados ficam na sessão para reutilização
4. **Dashboard Executivo** → Mostra KPIs e gráficos gerais
5. **Análise de Materiais** → Permite filtros e análises detalhadas

### 5. **Endpoints da API**

#### Dashboard V2
- `GET /dashboard-v2/` - Página principal
- `GET /dashboard-v2/api/load-data` - Carrega dados da view
- `GET /dashboard-v2/api/dashboard-kpis` - KPIs do dashboard
- `GET /dashboard-v2/api/dashboard-charts` - Dados para gráficos
- `GET /dashboard-v2/api/recent-operations` - Operações recentes

#### Materiais V2
- `GET /materiais-v2/api/materiais-kpis` - KPIs de materiais
- `GET /materiais-v2/api/top-materiais` - Top 10 materiais
- `GET /materiais-v2/api/evolucao-mensal` - Evolução mensal
- `GET /materiais-v2/api/modal-distribution` - Distribuição por modal
- `GET /materiais-v2/api/canal-distribution` - Distribuição por canal
- `GET /materiais-v2/api/transit-time-por-material` - Transit time
- `GET /materiais-v2/api/detalhamento-processos` - Detalhamento
- `GET /materiais-v2/api/filter-options` - Opções de filtro

### 6. **Funcionalidades Implementadas**

#### Dashboard Executivo
- **KPIs**: Total de processos, despesas, modais, status
- **Gráficos**: Evolução mensal, distribuição por modal, URF, materiais
- **Tabela**: Operações recentes

#### Análise de Materiais
- **KPIs**: Processos, tipos de materiais, valores, custos, transit time
- **Filtros**: Data, material, cliente, modal, canal
- **Gráficos**: Top materiais, evolução mensal, distribuições
- **Tabela**: Detalhamento dos processos

### 7. **Melhorias Implementadas**

1. **Performance**: Carregamento único dos dados
2. **Usabilidade**: Interface em abas na mesma página
3. **Escalabilidade**: Uso de view otimizada para 6 meses
4. **Manutenibilidade**: Código separado em arquivos V2
5. **Flexibilidade**: Filtros dinâmicos na análise de materiais

### 8. **Mudanças na Navegação**

- **Menu lateral**: Removido link separado "Análise de Materiais"
- **Link principal**: "Dashboard Executivo" leva para página unificada
- **Rota padrão**: `/` agora redireciona para `/dashboard-v2/`

### 9. **Tecnologias Utilizadas**

- **Backend**: Flask, Pandas, Supabase
- **Frontend**: HTML, CSS, JavaScript (vanilla)
- **Gráficos**: Chart.js
- **Dados**: PostgreSQL (view `vw_importacoes_6_meses`)

### 10. **Como Testar**

1. Execute o teste da view:
   ```bash
   python test_view_6_meses.py
   ```

2. Inicie a aplicação:
   ```bash
   python app.py
   ```

3. Acesse: `http://127.0.0.1:5000`

4. Faça login e navegue pelas abas

### 11. **Próximos Passos**

1. **Estilização**: Aplicar CSS avançado
2. **Otimizações**: Implementar cache client-side
3. **Filtros Avançados**: Adicionar mais opções de filtro
4. **Exportação**: Implementar export para Excel/PDF
5. **Responsividade**: Melhorar layout mobile

### 12. **Arquivos Modificados**

- `app.py` - Registrados novos blueprints
- `templates/base.html` - Atualizado menu lateral
- Criados arquivos V2 mantendo compatibilidade com versão anterior

### 13. **Estrutura de Dados**

A aplicação agora trabalha com dados padronizados da view, garantindo:
- Consistência entre as duas abas
- Performance melhorada
- Facilidade de manutenção
- Dados sempre atualizados (últimos 6 meses)

---

**Autor**: GitHub Copilot  
**Data**: 16/07/2025  
**Versão**: 2.0
