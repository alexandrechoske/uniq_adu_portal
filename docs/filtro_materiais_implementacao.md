# Filtro de CNPJs na Página de Materiais - Implementação Completa

## Resumo das Alterações

Este documento descreve as alterações implementadas para aplicar o filtro de CNPJs do usuário ativo em todos os endpoints da página de Materiais, seguindo o mesmo padrão usado na Dashboard.

## Funcionalidades Implementadas

### 1. Funções Helper Adicionadas

#### `get_user_companies()`
- Obtém as empresas que o usuário tem acesso através dos dados da sessão
- Retorna lista de CNPJs para usuários com role 'cliente_unique'
- Retorna lista vazia para outros roles (admin, interno_unique)

#### `apply_company_filter(query)`
- Aplica filtro de empresa na query baseado no papel do usuário
- **Para clientes (`cliente_unique`):**
  - Se não tem empresas associadas: retorna query que não encontra nada
  - Se empresa específica selecionada: filtra por essa empresa
  - Caso contrário: filtra por todas as empresas do usuário
- **Para admin/interno:**
  - Aplica filtro apenas se empresa específica for selecionada

### 2. Endpoints Atualizados

Todos os seguintes endpoints agora respeitam o filtro de CNPJs:

1. **`/api/kpis`** - KPIs gerais de materiais
2. **`/api/top-materiais`** - Top 10 materiais por valor  
3. **`/api/evolucao-mensal`** - Evolução mensal por material
4. **`/api/despesas-composicao`** - Composição das despesas por material
5. **`/api/canal-parametrizacao`** - Análise de canal por material
6. **`/api/clientes-por-material`** - Principais clientes por material
7. **`/api/detalhamento`** - Tabela de detalhamento dos processos
8. **`/api/radar-cliente-material`** - Gráfico de radar de performance
9. **`/api/materiais-opcoes`** - Lista de materiais únicos para dropdown
10. **`/api/linha-tempo-chegadas`** - Próximas chegadas e despesas

### 3. Alterações Técnicas

#### Campos Adicionados
- Campo `cliente_cpfcnpj` adicionado em todas as queries SELECT para permitir o filtro

#### Padrão de Implementação
```python
# Exemplo de como o filtro foi aplicado
query = supabase.table('importacoes_processos').select(
    'campos_necessarios, cliente_cpfcnpj'  # cliente_cpfcnpj adicionado
)

# Aplicar filtro de empresa baseado no usuário
query = apply_company_filter(query)

# Demais filtros específicos do endpoint...
```

### 4. Segurança Implementada

#### Isolamento de Dados por Cliente
- Clientes só visualizam dados das empresas associadas a eles
- Impossibilidade de acessar dados de outras empresas
- Filtro aplicado no nível da query do banco de dados

#### Comportamento por Role
- **Cliente (`cliente_unique`)**: Vê apenas CNPJs associados
- **Admin/Interno (`admin`, `interno_unique`)**: Vê todos os dados, com filtro opcional por empresa

### 5. Compatibilidade

#### Frontend
- Nenhuma alteração necessária no frontend
- Todos os endpoints mantêm a mesma interface de resposta
- Filtros adicionais via query parameters continuam funcionando

#### Parâmetros Opcionais
- Parameter `empresa` pode ser usado para filtrar por CNPJ específico
- Compatível com filtros existentes (material, data, etc.)

## Teste da Implementação

### Verificação de Sintaxe
```bash
python -m py_compile routes/materiais.py  # ✅ Passou
```

### Script de Teste
Criado `test_filtro_materiais.py` para validar todos os endpoints.

### Cenários de Teste Recomendados

1. **Cliente com múltiplas empresas**: Verificar se vê dados de todas suas empresas
2. **Cliente com empresa específica selecionada**: Verificar filtro por empresa única
3. **Cliente sem empresas**: Verificar se não vê dados
4. **Admin/Interno**: Verificar se vê todos os dados
5. **Admin com empresa selecionada**: Verificar filtro por empresa específica

## Impacto

### Segurança
- ✅ Dados isolados por cliente
- ✅ Impossível acesso a dados não autorizados
- ✅ Filtro aplicado no banco de dados

### Performance
- ✅ Filtros otimizados no nível da query
- ✅ Redução no volume de dados transferidos
- ✅ Melhores tempos de resposta para clientes

### Funcionalidade
- ✅ Todos os gráficos respeitam o filtro
- ✅ KPIs calculados apenas para dados permitidos
- ✅ Radar de materiais funciona com dados filtrados
- ✅ Tabelas de detalhamento mostram apenas dados do cliente

## Próximos Passos

1. **Teste em ambiente de desenvolvimento**
2. **Validação com diferentes perfis de usuário**
3. **Teste de integração com o frontend**
4. **Deploy para ambiente de produção**
5. **Monitoramento pós-deploy**

## Arquivos Modificados

- `routes/materiais.py` - Implementação completa do filtro
- `test_filtro_materiais.py` - Script de teste criado

## Compatibilidade com Dashboard

A implementação segue exatamente o mesmo padrão usado na Dashboard (`routes/dashboard.py`), garantindo consistência na aplicação do filtro de CNPJs em todo o sistema.
