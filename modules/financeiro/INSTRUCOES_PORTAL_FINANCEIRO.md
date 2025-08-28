# 📊 INSTRUÇÕES PARA DESENVOLVIMENTO DO PORTAL FINANCEIRO
**Data**: 28/08/2025  
**Sistema**: Portal Financeiro - Unique Aduaneira  
**Fonte de Dados**: Supabase (3 tabelas + 1 view consolidada)

---

## 🎯 **VISÃO GERAL DA ARQUITETURA**

### **Fontes de Dados Disponíveis:**
1. **`fin_faturamento_anual`** - Faturamento baseado em FAT_FECHAMENTO
2. **`fin_despesa_anual`** - Despesas operacionais e administrativas  
3. **`fin_resultado_anual`** - Receitas e despesas baseadas em REC_DATA (recebimentos efetivos)
4. **`vw_fin_resultado_consolidado`** - View unificada com saldo inicial e acumulado

### **Princípio Fundamental:**
- **Faturamento**: Base FAT_FECHAMENTO (controle interno)
- **Fluxo de Caixa**: Base REC_DATA (recebimentos efetivos) - **MESMA BASE DO POWERBI**
- **Despesas**: Despesas operacionais e administrativas

---

## 🏗️ **ESPECIFICAÇÕES POR TELA**

### 1. **TELA: FLUXO DE CAIXA** 💰
**Objetivo**: Mostrar fluxo de caixa real baseado em recebimentos efetivos

#### **Base de Dados Principal:**
```sql
-- USE: vw_fin_resultado_consolidado
-- Esta view já inclui saldo inicial e saldo acumulado
```

#### **Estrutura da View:**
- `data` - Data do recebimento/pagamento
- `tipo` - 'Receita' ou 'Despesa'  
- `categoria` - Categoria da operação
- `classe` - Classe da operação
- `codigo` - Código de referência
- `descricao` - Descrição da operação
- `valor` - Valor (receitas positivas, despesas negativas)
- `saldo_acumulado` - Saldo corrente acumulado

#### **Componentes Sugeridos:**
1. **Gráfico de Linha**: Saldo acumulado ao longo do tempo
2. **Gráfico de Barras**: Receitas vs Despesas por mês
3. **Cards de Resumo**: 
   - Saldo atual
   - Receitas do mês
   - Despesas do mês
   - Resultado do mês
4. **Tabela Detalhada**: Movimentações do período

#### **Queries de Exemplo:**

**Query Mensal (como a que você testou):**
```sql
WITH dados_mensais AS (
  SELECT 
    EXTRACT(YEAR FROM data) as ano,
    EXTRACT(MONTH FROM data) as mes,
    tipo,
    SUM(valor) as valor_total
  FROM vw_fin_resultado_consolidado 
  WHERE EXTRACT(YEAR FROM data) = 2025
  GROUP BY 
    EXTRACT(YEAR FROM data),
    EXTRACT(MONTH FROM data),
    tipo
),
pivot_dados AS (
  SELECT 
    ano,
    mes,
    COALESCE(SUM(CASE WHEN tipo = 'Receita' THEN valor_total END), 0) as receita,
    COALESCE(SUM(CASE WHEN tipo = 'Despesa' THEN valor_total END), 0) as despesa
  FROM dados_mensais
  GROUP BY ano, mes
)
SELECT 
  ano,
  mes,
  receita,
  ABS(despesa) as despesa,
  (receita + despesa) as resultado
FROM pivot_dados
ORDER BY ano DESC, mes DESC;
```

**Saldo Atual:**
```sql
SELECT saldo_acumulado 
FROM vw_fin_resultado_consolidado 
ORDER BY data DESC, id DESC 
LIMIT 1;
```

---

### 2. **TELA: DESPESAS** 💸
**Objetivo**: Análise detalhada de despesas operacionais e administrativas

#### **Base de Dados Principal:**
```sql
-- USE: fin_despesa_anual
```

#### **Estrutura da Tabela:**
- `data` - Data da despesa
- `categoria` - Categoria (Despesas Comerciais, Administrativas, etc.)
- `classe` - Classe da despesa
- `codigo` - Código de referência
- `descricao` - Descrição da despesa
- `valor` - Valor da despesa

#### **Componentes Sugeridos:**
1. **Gráfico de Pizza**: Despesas por categoria
2. **Gráfico de Barras**: Evolução mensal das despesas
3. **Gráfico de Barras Empilhadas**: Despesas por categoria ao longo do tempo
4. **Cards de Resumo**:
   - Total do mês
   - Maior categoria
   - Comparativo mês anterior
5. **Tabela com Filtros**: Por categoria, classe, período

#### **Queries de Exemplo:**

**Despesas por Categoria (Mês Atual):**
```sql
SELECT 
  categoria,
  SUM(valor) as total,
  COUNT(*) as quantidade
FROM fin_despesa_anual 
WHERE EXTRACT(YEAR FROM data) = 2025 
  AND EXTRACT(MONTH FROM data) = 8
GROUP BY categoria
ORDER BY total DESC;
```

**Evolução Mensal:**
```sql
SELECT 
  EXTRACT(YEAR FROM data) as ano,
  EXTRACT(MONTH FROM data) as mes,
  categoria,
  SUM(valor) as total
FROM fin_despesa_anual 
WHERE EXTRACT(YEAR FROM data) = 2025
GROUP BY 
  EXTRACT(YEAR FROM data),
  EXTRACT(MONTH FROM data),
  categoria
ORDER BY ano, mes, categoria;
```

---

### 3. **TELA: FATURAMENTO** 📈

#### **ABA 3.1: VISÃO GERAL**
**Objetivo**: Análise geral do faturamento interno

#### **Base de Dados:**
```sql
-- USE: fin_faturamento_anual
```

#### **Estrutura da Tabela:**
- `data` - Data do fechamento da fatura
- `categoria` - Categoria da operação
- `classe` - Classe da operação
- `cliente` - Cliente
- `fatura` - Número da fatura
- `operacao` - Código da operação
- `valor` - Valor faturado

#### **Componentes Sugeridos:**
1. **Gráfico de Linha**: Evolução do faturamento mensal
2. **Gráfico de Barras**: Faturamento por categoria
3. **Cards de Resumo**:
   - Faturamento total do mês
   - Número de faturas
   - Ticket médio
   - Comparativo com mês anterior
4. **Tabela de Top Clientes**

#### **Queries de Exemplo:**

**Faturamento Mensal:**
```sql
SELECT 
  EXTRACT(YEAR FROM data) as ano,
  EXTRACT(MONTH FROM data) as mes,
  SUM(valor) as total_faturado,
  COUNT(DISTINCT fatura) as total_faturas,
  AVG(valor) as ticket_medio
FROM fin_faturamento_anual 
WHERE EXTRACT(YEAR FROM data) = 2025
GROUP BY 
  EXTRACT(YEAR FROM data),
  EXTRACT(MONTH FROM data)
ORDER BY ano, mes;
```

**Top Clientes:**
```sql
SELECT 
  cliente,
  SUM(valor) as total_faturado,
  COUNT(DISTINCT fatura) as total_faturas
FROM fin_faturamento_anual 
WHERE EXTRACT(YEAR FROM data) = 2025 
  AND EXTRACT(MONTH FROM data) = 8
GROUP BY cliente
ORDER BY total_faturado DESC
LIMIT 10;
```

#### **ABA 3.2: POR SETOR**
**Objetivo**: Análise do faturamento segmentado por setores/categorias

#### **Base de Dados:**
```sql
-- USE: fin_faturamento_anual (mesmo que Visão Geral)
```

#### **Componentes Sugeridos:**
1. **Gráfico de Pizza**: Faturamento por categoria/setor
2. **Gráfico de Barras Empilhadas**: Evolução por setor ao longo do tempo
3. **Matriz de Performance**: Setor vs Mês
4. **Cards de Resumo por Setor**
5. **Tabela Comparativa**: Performance entre setores

#### **Queries de Exemplo:**

**Faturamento por Setor:**
```sql
SELECT 
  categoria as setor,
  SUM(valor) as total_faturado,
  COUNT(*) as total_operacoes,
  AVG(valor) as ticket_medio
FROM fin_faturamento_anual 
WHERE EXTRACT(YEAR FROM data) = 2025 
  AND EXTRACT(MONTH FROM data) = 8
GROUP BY categoria
ORDER BY total_faturado DESC;
```

**Evolução por Setor:**
```sql
SELECT 
  EXTRACT(MONTH FROM data) as mes,
  categoria as setor,
  SUM(valor) as total
FROM fin_faturamento_anual 
WHERE EXTRACT(YEAR FROM data) = 2025
GROUP BY 
  EXTRACT(MONTH FROM data),
  categoria
ORDER BY mes, setor;
```

---

### 4. **TELA: DASHBOARD EXECUTIVO** 📊
**Objetivo**: Resumo executivo combinando todas as bases

#### **Bases de Dados:**
```sql
-- COMBINE: vw_fin_resultado_consolidado + fin_faturamento_anual + fin_despesa_anual
```

#### **Componentes Sugeridos:**
1. **Cards de KPIs Principais**:
   - Saldo atual (vw_fin_resultado_consolidado)
   - Faturamento do mês (fin_faturamento_anual)
   - Despesas do mês (fin_despesa_anual)
   - Resultado do mês (vw_fin_resultado_consolidado)

2. **Gráfico Combinado**: Faturamento vs Resultado vs Despesas

3. **Mini Gráficos**:
   - Tendência do saldo (últimos 6 meses)
   - Top 5 categorias de despesa
   - Top 5 clientes no faturamento

---

## 🔧 **CONFIGURAÇÕES TÉCNICAS**

### **Conexão com Supabase:**
- **URL**: Usar variável de ambiente
- **API Key**: Usar chave anônima para leituras
- **Tabelas**: fin_faturamento_anual, fin_despesa_anual, fin_resultado_anual
- **View**: vw_fin_resultado_consolidado

### **Sincronização:**
- As tabelas são atualizadas automaticamente via sync
- Frequência: A cada 4 horas durante horário comercial
- API disponível para sync manual: `/api/financeiro/sync/individual`

### **Filtros Padrão Sugeridos:**
- **Período**: Último ano por padrão
- **Mês/Ano**: Seletores independentes
- **Categoria**: Multi-seleção
- **Valor Mínimo**: Para filtrar operações pequenas

---

## 📋 **CHECKLIST DE IMPLEMENTAÇÃO**

### **Para o Desenvolvedor do Portal:**

#### **☐ Tela: Fluxo de Caixa**
- [ ] Conectar com `vw_fin_resultado_consolidado`
- [ ] Implementar gráfico de saldo acumulado
- [ ] Criar cards de resumo mensal
- [ ] Implementar filtros de período

#### **☐ Tela: Despesas**  
- [ ] Conectar com `fin_despesa_anual`
- [ ] Implementar gráfico de pizza por categoria
- [ ] Criar evolução mensal
- [ ] Implementar filtros por categoria

#### **☐ Tela: Faturamento - Visão Geral**
- [ ] Conectar com `fin_faturamento_anual`
- [ ] Implementar evolução mensal
- [ ] Criar ranking de clientes
- [ ] Implementar métricas de performance

#### **☐ Tela: Faturamento - Por Setor**
- [ ] Usar mesma base `fin_faturamento_anual`
- [ ] Implementar análise por categoria
- [ ] Criar matriz de performance
- [ ] Implementar comparativos

#### **☐ Tela: Dashboard Executivo**
- [ ] Combinar dados das 3 bases
- [ ] Implementar KPIs consolidados
- [ ] Criar visualizações de resumo

---

## 🚀 **PRÓXIMOS PASSOS**

1. **Teste as Queries**: Execute as queries de exemplo no Supabase
2. **Valide os Dados**: Compare com resultados do PowerBI quando possível
3. **Implemente Gradualmente**: Comece pelo Fluxo de Caixa (dados mais próximos do PowerBI)
4. **Adicione Filtros**: Permita que usuários filtrem por período, categoria, etc.
5. **Otimize Performance**: Considere cache para consultas frequentes

---

## ⚠️ **OBSERVAÇÕES IMPORTANTES**

### **Diferenças entre Faturamento e Fluxo de Caixa:**
- **Faturamento** (fin_faturamento_anual): Data de fechamento da fatura
- **Fluxo de Caixa** (vw_fin_resultado_consolidado): Data de recebimento efetivo
- **Use Fluxo de Caixa** para análises que precisam coincidir com PowerBI

### **Tratamento de Valores:**
- **Receitas**: Valores positivos
- **Despesas**: Valores negativos na view consolidada
- **Saldo Acumulado**: Já calculado na view

### **Performance:**
- Views são recalculadas em tempo real
- Para dados históricos extensos, considere cache
- Índices já criados nas tabelas para otimização

---

**🎯 RESUMO EXECUTIVO**: Use `vw_fin_resultado_consolidado` para Fluxo de Caixa, `fin_despesa_anual` para Despesas, e `fin_faturamento_anual` para Faturamento. Combine todas para Dashboard Executivo.
