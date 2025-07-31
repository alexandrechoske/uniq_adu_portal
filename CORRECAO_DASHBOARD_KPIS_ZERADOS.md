# Correções Dashboard Executivo - KPIs com Valores Zerados

## Problema Identificado
Os KPIs do Dashboard Executivo estavam mostrando valores zerados para:
- Total Despesas
- Ticket Médio  
- Chegando Este Mês (valor R$0)
- Chegando Esta Semana (valor R$0)
- Gráficos de Evolução Mensal e Modal

## Causa Raiz
A função `calculate_custo_from_despesas_processo()` não estava calculando corretamente os custos baseados no campo JSON `despesas_processo` da view `vw_importacoes_6_meses`.

## Correções Implementadas

### 1. Função de Cálculo de Custo Aprimorada
```python
def calculate_custo_from_despesas_processo(despesas_processo):
    """
    Calcular custo total baseado no campo JSON despesas_processo
    Reproduz a lógica do frontend processExpensesByCategory()
    """
    try:
        if not despesas_processo:
            return 0.0
        
        # Se for string JSON, converter para lista
        if isinstance(despesas_processo, str):
            despesas_list = json.loads(despesas_processo)
        else:
            despesas_list = despesas_processo
        
        if not isinstance(despesas_list, list):
            return 0.0
        
        total_custo = 0.0
        for despesa in despesas_list:
            if isinstance(despesa, dict) and 'valor_custo' in despesa:
                valor = despesa.get('valor_custo', 0)
                if isinstance(valor, (int, float)) and not pd.isna(valor):
                    total_custo += float(valor)
        
        return total_custo
        
    except Exception as e:
        print(f"[CUSTO_CALCULATION] Erro ao calcular custo: {str(e)}")
        return 0.0
```

### 2. Correção da Função dashboard_kpis()
- ✅ Logs detalhados para debug dos cálculos
- ✅ Contabilização correta de registros com custo > 0
- ✅ Validação de tipos float para evitar problemas de serialização JSON
- ✅ Correção do cálculo de "Chegando Este Mês" e "Chegando Esta Semana"

### 3. Correção da Função dashboard_charts()
- ✅ Aplicação da mesma lógica de cálculo de custo nos gráficos
- ✅ Gráfico de Evolução Mensal usando custo calculado
- ✅ Gráfico de Modal usando custo calculado
- ✅ Logs de debug para validação

### 4. Correção da Função monthly_chart()
- ✅ Atualização para usar `custo_calculado` em vez de `custo_total`
- ✅ Garantia de consistência entre KPIs e gráficos

## Mudanças Principais

### Antes:
```python
# KPIs usavam custo_total (campo direto do banco)
total_despesas = df['custo_total'].sum()

# Valores sempre zerados porque custo_total não estava sendo populado corretamente
```

### Depois:
```python
# KPIs usam custo calculado baseado em despesas_processo
custos_calculados = []
for idx, row in df.iterrows():
    despesas = row.get('despesas_processo')
    custo_calculado = calculate_custo_from_despesas_processo(despesas)
    custos_calculados.append(custo_calculado)

df['custo_calculado'] = custos_calculados
total_despesas = df['custo_calculado'].sum()
```

## Logs de Debug Adicionados

```python
print(f"[DEBUG_KPI] Registros com custo > 0: {registros_com_custo}/{len(df)}")
print(f"[DEBUG_KPI] Total despesas calculado: {total_despesas_debug:,.2f}")
print(f"[DEBUG_KPI] KPIs Calculados:")
print(f"[DEBUG_KPI] - Total processos: {total_processos}")
print(f"[DEBUG_KPI] - Total despesas: {total_despesas:,.2f}")
print(f"[DEBUG_KPI] - Ticket médio: {ticket_medio:,.2f}")
```

## Validação Esperada

### KPIs que devem mostrar valores corretos:
1. ✅ **Total Despesas**: Soma de todos os `valor_custo` do JSON `despesas_processo`
2. ✅ **Ticket Médio**: Total Despesas / Total Processos
3. ✅ **Chegando Este Mês**: Custo calculado dos processos chegando no mês atual
4. ✅ **Chegando Esta Semana**: Custo calculado dos processos chegando na semana atual

### Gráficos que devem mostrar valores corretos:
1. ✅ **Evolução Mensal**: Barras de custo com valores calculados
2. ✅ **Processos e Custos por Modal**: Valores de custo por modal
3. ✅ **Principais Materiais**: Custos por material

## Como Testar

1. Acesse o Dashboard Executivo: `/dashboard-executivo/`
2. Verifique se os KPIs mostram valores não-zerados
3. Confira os logs no console do Flask para debug
4. Valide se os gráficos mostram dados de custo corretos

## Arquivos Modificados

- `modules/dashboard_executivo/routes.py`: Todas as correções principais
- Função `calculate_custo_from_despesas_processo()`: Nova implementação
- Função `dashboard_kpis()`: Cálculo baseado em despesas_processo
- Função `dashboard_charts()`: Gráficos usando custo calculado
- Função `monthly_chart()`: Evolução mensal com custo calculado

Data: 30/07/2025
Status: ✅ Implementado e pronto para teste
