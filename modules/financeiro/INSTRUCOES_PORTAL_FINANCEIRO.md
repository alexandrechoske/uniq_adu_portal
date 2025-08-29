# 📊 GUIA DE TABELAS PARA APLICAÇÃO FINAL

## 🎯 **PÁGINAS E SUAS RESPECTIVAS TABELAS**

### 📈 **1. DASHBOARD EXECUTIVO**
```sql
-- Tabelas principais para métricas gerais
PRIMARY: vw_fluxo_caixa
SUPPORT: fin_resultado_anual, fin_despesa_anual, fin_faturamento_anual

### 💰 **2. FLUXO DE CAIXA**  
```sql
-- Tabela principal (já implementada com 99.99% precisão)
PRIMARY: vw_fluxo_caixa

-- Filtros recomendados:
-- Por período: WHERE data BETWEEN '2024-01-01' AND '2024-12-31'
-- Por categoria: WHERE categoria = 'CATEGORIA_DESEJADA'
-- Excluir sem data: WHERE data IS NOT NULL
```

### 💸 **3. DESPESAS**
```sql
-- Tabelas para análise completa de despesas
PRIMARY: fin_despesa_anual (30.759 registros - incluindo NULL dates)

### 📋 **4. FATURAMENTO**
```sql
-- Tabelas para análise de faturamento
PRIMARY: fin_faturamento_anual (24.828 registros esperados)
ALTERNATIVE: fin_resultado_anual WHERE tipo = 'Receita'
DETAIL: vw_fluxo_caixa WHERE tipo_movto = 'Receita'


## 🎯 **RESUMO TÉCNICO POR PÁGINA:**

### **Fluxo de Caixa:**
- **Foco:** Movimentação completa com saldo acumulado
- **Tabela principal:** `vw_fluxo_caixa` (99.99% precisão)
- **Dados:** Receitas (+), Despesas (-), Saldo acumulado

### **Despesas:**
- **Foco:** Análise detalhada de gastos
- **Tabela principal:** `fin_despesa_anual` (30.759 registros)
- **Dados:** Todos os tipos de despesas, incluindo registros sem data

### **Faturamento:**
- **Foco:** Análise de receitas e vendas
- **Tabela principal:** `fin_faturamento_anual` (24.828 registros esperados)
- **Dados:** Todas as receitas e faturamentos
