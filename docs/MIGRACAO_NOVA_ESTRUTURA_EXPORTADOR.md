# Migração para Nova Estrutura - Dashboard Executivo

## Resumo das Alterações

### Estrutura da Tabela
- **Antes**: Dados vindos da view `vw_importacoes_6_meses`
- **Agora**: Dados vindos da tabela `importacoes_processos_aberta`

### Campo Exportador
- **Antes**: Campo `exportador` (possivelmente derivado ou computed)
- **Agora**: Campo `exportador_fornecedor` direto da tabela

## Alterações Implementadas

### 1. Backend (routes.py)
- ✅ Adicionados imports necessários (`unicodedata`, `re`)
- ✅ Alterada query de `vw_importacoes_6_meses` para `importacoes_processos_aberta`
- ✅ Campo `exportador_fornecedor` já está sendo usado corretamente nos endpoints
- ✅ Filtros funcionando com a nova estrutura

### 2. Frontend (HTML)
- ✅ Coluna "Exportador" na tabela atualizada para usar `data-sort="exportador_fornecedor"`
- ✅ Modal de detalhes inclui campo para `detail-exportador`

### 3. JavaScript (dashboard.js)
- ✅ Tabela renderiza `operation.exportador_fornecedor`
- ✅ Modal atualiza `detail-exportador` com `operation.exportador_fornecedor`
- ✅ Campos de busca incluem `exportador_fornecedor`

## Estrutura da Nova Tabela

```sql
create table public.importacoes_processos_aberta (
  id bigserial not null,
  created_at timestamp with time zone null default now(),
  updated_at timestamp with time zone null default now(),
  ref_unique text not null,
  ref_importador text null,
  cnpj_importador text null,
  importador text null,
  modal text null,
  container text null,
  data_embarque text null,
  data_chegada text null,
  transit_time_real integer null,
  urf_entrada text null,
  urf_despacho text null,
  exportador_fornecedor text null,  -- ⭐ NOVO CAMPO
  fabricante text null,
  numero_di text null,
  presenca_carga text null,
  data_registro text null,
  canal text null,
  data_desembaraco text null,
  mercadoria text null,
  status_processo text null,
  peso_bruto numeric(15, 3) null,
  valor_fob_real numeric(15, 2) null,
  valor_cif_real numeric(15, 2) null,
  firebird_di_codigo integer null,
  firebird_fat_codigo text null,
  data_abertura text null,
  mercadoria_normalizado text null,
  urf_entrada_normalizado text null,
  urf_despacho_normalizado text null,
  status_macro text null,
  status_macro_sistema text null,
  status_timeline text null,
  data_fechamento text null,
  material text null,
  status_sistema text null,
  constraint uk_importacoes_ref_unique unique (ref_unique)
);
```

## Campos Relevantes para Dashboard

### Informações Básicas
- `ref_unique` - Referência única do processo
- `ref_importador` - Referência do importador
- `importador` - Nome do importador
- `exportador_fornecedor` - Nome do exportador/fornecedor ⭐
- `cnpj_importador` - CNPJ do importador

### Transporte e Logística
- `modal` - Modal de transporte
- `container` - Número do container
- `data_embarque` - Data de embarque
- `data_chegada` - Data de chegada
- `transit_time_real` - Tempo de trânsito real

### Aduaneira
- `urf_entrada` - URF de entrada
- `urf_despacho` - URF de despacho
- `numero_di` - Número da DI
- `canal` - Canal de conferência
- `data_registro` - Data de registro
- `data_desembaraco` - Data de desembaraço

### Status
- `status_processo` - Status do processo
- `status_macro` - Status macro
- `status_macro_sistema` - Status macro do sistema

### Financeiro
- `valor_fob_real` - Valor FOB
- `valor_cif_real` - Valor CIF
- `peso_bruto` - Peso bruto

## Validação

### Testes Implementados
1. **test_nova_estrutura_exportador.py** - Teste completo dos endpoints
2. **test_estrutura_simples.py** - Teste básico de carregamento

### Status dos Testes
- ✅ Dashboard carrega sem erros
- ✅ Estrutura HTML correta
- ✅ JavaScript processa `exportador_fornecedor`
- ✅ Modal exibe campo de exportador

## Próximos Passos

1. **Teste em Produção**: Validar com dados reais
2. **Monitoramento**: Verificar se todos os campos estão sendo populados
3. **Performance**: Avaliar se há impacto na performance com a nova tabela
4. **Backup**: Manter view anterior como fallback se necessário

## Notas Importantes

- ⚠️ **Quebra de Compatibilidade**: Se houver outros módulos usando a view antiga, eles precisarão ser atualizados
- ⚠️ **Cache**: Limpar cache do dashboard após deploy
- ⚠️ **Filtros**: Verificar se filtros por exportador funcionam corretamente
- ⚠️ **Relatórios**: Atualizar relatórios que possam depender da estrutura antiga

## Rollback Plan

Caso necessário, para reverter:
1. Alterar query em `routes.py` de volta para `vw_importacoes_6_meses`
2. Reverter `data-sort` para `exportador`
3. Ajustar JavaScript se necessário
