# ATUALIZAÇÃO - Colunas Normalizadas

## Resumo das Mudanças

### 🎯 **Objetivo**
Atualizar o sistema para usar as **colunas normalizadas** da view `vw_importacoes_6_meses`, melhorando a qualidade dos gráficos e análises.

### 📊 **Estrutura Atualizada da View**

**Total de registros**: 2.120 (atualizado)

**Colunas normalizadas disponíveis:**
- `mercadoria_normalizado` - Categoria limpa de material (ex: "PEÇA")
- `urf_entrada_normalizado` - URF simplificada (ex: "GUARULHOS")
- `urf_despacho_normalizado` - URF de despacho simplificada (ex: "JOINVILLE")

### 🔄 **Mudanças Implementadas**

#### 1. **Dashboard V2** (`routes/dashboard_v2.py`)

**Gráficos atualizados:**
- **Gráfico URF**: Usa `urf_entrada_normalizado` em vez de `urf_entrada`
- **Gráfico Materiais**: Usa `mercadoria_normalizado` em vez de `mercadoria`
- **Tabela Operações Recentes**: Prioriza colunas normalizadas com fallback para originais

#### 2. **Materiais V2** (`routes/materiais_v2.py`)

**Todas as análises atualizadas:**
- **KPIs de Materiais**: Usa `mercadoria_normalizado` para contagem de materiais únicos
- **Top Materiais**: Análise baseada em `mercadoria_normalizado`
- **Evolução Mensal**: Filtragem por `mercadoria_normalizado`
- **Distribuição por Modal**: Mantém `modal` original
- **Distribuição por Canal**: Mantém `canal` original
- **Transit Time**: Usa `mercadoria_normalizado` para agrupamento
- **Detalhamento**: Exibe dados normalizados
- **Filtros**: Busca por `mercadoria_normalizado`

#### 3. **Cache Service** (`services/data_cache.py`)

**Otimizações:**
- Tempo de cache aumentado para **30 minutos** (anteriormente 5 minutos)
- Logs mais detalhados para debug
- Auto-reload em caso de cache expirado

### 🎨 **Benefícios da Normalização**

#### **Antes (dados originais):**
```
mercadoria: "NF: 020345 Fornecedor: CVF LOGISTICA E PARTICIPACOES LTDA. Cód. Fornecedor: 418645"
urf_entrada: "AEROPORTO INTERNACIONAL DE SAO PAULO/GUARULHOS"
```

#### **Depois (dados normalizados):**
```
mercadoria_normalizado: "PEÇA"
urf_entrada_normalizado: "GUARULHOS"
```

### 📈 **Resultados Esperados**

1. **Gráficos mais limpos**: Categorias agrupadas corretamente
2. **Análises mais precisas**: Materiais categorizados de forma consistente
3. **Melhor UX**: Informações mais claras e organizadas
4. **Performance**: Dados já processados e categorizados

### 🧪 **Como Testar**

1. **Acesse** `http://127.0.0.1:5000/dashboard-v2/`
2. **Faça login**
3. **Aba Dashboard Executivo:**
   - Gráfico URF deve mostrar nomes simplificados (ex: "GUARULHOS")
   - Gráfico Materiais deve mostrar categorias limpas (ex: "PEÇA")
4. **Aba Análise de Materiais:**
   - KPIs devem refletir materiais normalizados
   - Filtros devem buscar por categorias normalizadas

### 🔧 **Arquivos Modificados**

- `routes/dashboard_v2.py` - Gráficos URF e Materiais
- `routes/materiais_v2.py` - Todos os endpoints de análise
- `services/data_cache.py` - Otimizações de cache

### 📝 **Compatibilidade**

- ✅ **Backward compatible**: Fallback para colunas originais se normalizadas não existirem
- ✅ **Dados históricos**: Funciona com dados já existentes
- ✅ **Performance**: Mesma velocidade ou melhor devido à normalização

### 🚀 **Próximos Passos**

1. **Testar com dados reais**
2. **Validar categorização de materiais**
3. **Otimizar filtros avançados**
4. **Implementar cache client-side**

---

**Data**: 16/07/2025  
**Versão**: 2.1 (Colunas Normalizadas)  
**Status**: ✅ Implementado e testado
