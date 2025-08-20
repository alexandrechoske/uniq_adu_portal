# Página de Fluxo de Caixa - Sistema UniqueAduaneira

## Visão Geral

A página de Fluxo de Caixa é um módulo completo de análise financeira que oferece insights estratégicos sobre o desempenho financeiro da empresa. Foi desenvolvida seguindo o padrão visual e arquitetural da aplicação, utilizando Chart.js para visualizações e um design minimalista e profissional.

## Funcionalidades Implementadas

### 1. KPIs Principais
- **Resultado Líquido**: Diferença entre entradas e saídas com comparação ao período anterior
- **Total de Entradas**: Soma de todas as receitas no período
- **Total de Saídas**: Soma de todas as despesas no período  
- **Saldo Final do Período**: Saldo acumulado no final do período selecionado

### 2. KPIs Estratégicos
- **Burn Rate Mensal**: Média dos gastos líquidos em meses com resultado negativo
- **Runway**: Quantos meses a empresa pode operar com o saldo atual

### 3. Gráficos Analíticos

#### Despesas por Categoria (Donut Chart)
- Visualização das despesas agrupadas por categoria
- **Drill-down**: Clique em uma categoria para ver as classes que a compõem
- Percentuais e valores absolutos
- Interativo com tooltip detalhado

#### Fluxo de Caixa Mês a Mês (Gráfico de Cascata)
- Resultado líquido mensal (barras verdes/vermelhas)
- Linha de saldo acumulado sobreposta
- Cores baseadas no resultado (positivo = verde, negativo = vermelho)

#### Análise Estrutural (FCO, FCI, FCF)
- **FCO**: Fluxo de Caixa Operacional (core business)
- **FCI**: Fluxo de Caixa de Investimento (ativos)
- **FCF**: Fluxo de Caixa de Financiamento (empréstimos/rendimentos)
- Gráfico de barras empilhadas por mês

#### Projeção de Fluxo de Caixa
- Linha sólida: dados históricos
- Linha tracejada: projeção baseada na média dos últimos 6 meses
- Permite antecipação de problemas de liquidez

### 4. Filtros de Período
- Mês atual, último mês, trimestre atual, ano atual, último ano
- Período personalizado com seleção de datas
- Aplicação global em todos os componentes

### 5. Tabela de Dados
- Listagem completa dos registros financeiros
- Paginação inteligente
- Busca em tempo real
- Exportação de dados (em desenvolvimento)

## Arquitetura Técnica

### Backend (Flask)
- **Blueprint**: `fin_fluxo_de_caixa` registrado no módulo financeiro
- **Rotas de API**:
  - `/api/kpis`: KPIs principais e estratégicos
  - `/api/despesas-categoria`: Dados para gráfico de despesas (com drill-down)
  - `/api/fluxo-mensal`: Dados para gráfico de cascata
  - `/api/fluxo-estrutural`: Dados para análise FCO/FCI/FCF
  - `/api/projecao`: Dados para gráfico de projeção
  - `/api/tabela-dados`: Dados paginados para tabela

### Frontend (JavaScript)
- **Classe**: `FluxoCaixaController` gerencia toda a interação
- **Chart.js**: Configurações padronizadas seguindo o design system
- **AJAX**: Carregamento assíncrono de dados
- **Responsivo**: Design adaptável para mobile

### Fonte de Dados
- **Tabela principal**: `fin_base_resultado`
- **Campos**: data, categoria, classe, codigo, descricao, valor, tipo
- **Tipos**: 'Receita' e 'Despesa'

## Estrutura de Arquivos

```
modules/financeiro/fluxo_de_caixa/
├── routes.py                 # Blueprint e APIs
├── templates/
│   └── fluxo_de_caixa/
│       └── fluxo_de_caixa.html   # Template principal
├── static/
│   ├── css/
│   │   └── fluxo_de_caixa.css    # Estilos específicos
│   └── js/
│       └── fluxo_de_caixa.js     # Lógica JavaScript
├── fin_data_resultados.sql       # DDL da tabela base
└── fin_fluxo_caixa_functions.sql # Views e funções auxiliares
```

## Como Usar

### Acesso
1. Login com usuário `admin` ou `interno_unique`
2. Menu lateral > Financeiro > Fluxo de Caixa
3. URL direta: `/financeiro/fluxo-de-caixa/`

### Navegação
1. **Filtros**: Use o botão "Filtros" para selecionar o período de análise
2. **Drill-down**: Clique nas categorias do gráfico de despesas para ver detalhes
3. **KPIs**: Observe as variações percentuais em relação ao período anterior
4. **Projeção**: Analise a tendência futura para planejamento estratégico

### Interpretação dos Dados

#### KPIs Estratégicos
- **Burn Rate alto**: Empresa está queimando muito caixa
- **Runway baixo**: Necessidade urgente de aumento de receita ou redução de custos
- **FCO negativo**: Operação não está gerando caixa

#### Alertas Visuais
- Cards vermelhos: resultados negativos
- Cards verdes: resultados positivos
- Variações com setas: comparação temporal

## Configurações do Chart.js

### Padrões Visuais
- **Sem grades de fundo**: design limpo
- **Tooltips customizados**: valores em moeda brasileira
- **Cores consistentes**: paleta definida da aplicação
- **Formatação K/M**: valores grandes em milhares/milhões
- **Linhas suaves**: tension 0.4 para curvas

### Responsividade
- **Mobile first**: layouts se adaptam automaticamente
- **Touch friendly**: interações adequadas para touch
- **Performance otimizada**: lazy loading e cache

## Segurança

### Controle de Acesso
- Apenas usuários `admin` e `interno_unique`
- Verificação em todas as rotas de API
- Session-based authentication

### Validação de Dados
- Sanitização de parâmetros de entrada
- Tratamento de erros robusto
- Logs de auditoria (via middleware da aplicação)

## Possíveis Melhorias Futuras

1. **Exportação completa**: Excel, PDF, CSV
2. **Alertas automáticos**: notificações de runway baixo
3. **Metas financeiras**: comparação com objetivos
4. **Drill-down avançado**: até nível de código/descrição
5. **Análise de tendências**: ML para previsões mais precisas
6. **Dashboard executivo**: resumo para C-level
7. **Integração contábil**: sincronização automática

## Manutenção

### Logs e Debug
- Rota de teste: `/api/test-data` para verificar conectividade
- Logs detalhados no console do navegador
- Middleware de logging captura todas as requisições

### Performance
- Cache inteligente para dados pesados
- Paginação para tabelas grandes
- Lazy loading de gráficos

### Atualizações
- Estrutura modular permite fácil extensão
- APIs RESTful para integração com outros sistemas
- Código documentado e padronizado

---

**Desenvolvido seguindo os padrões da aplicação UniqueAduaneira**  
**Data**: Agosto 2025  
**Versão**: 1.0.0
