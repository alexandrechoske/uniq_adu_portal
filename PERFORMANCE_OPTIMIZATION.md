# Otimizações de Performance - Login e Dashboard

## Resumo das Otimizações Implementadas

### 1. **Remoção da Função de Atualização de Importações do Login**
- **Problema**: A função `update_importacoes_processos()` estava sendo executada a cada login, causando delay significativo
- **Solução**: Movida para endpoint separado `/background/update-importacoes` que pode ser chamado via cron job ou manualmente
- **Impacto**: Redução de ~2-5 segundos no tempo de login

### 2. **Implementação de Cache Inteligente de Permissões**
- **Problema**: Consultas repetidas ao banco para verificar permissões do usuário
- **Solução**: Cache em sessão com TTL de 30 minutos e invalidação automática
- **Impacto**: Redução de consultas DB de ~3-5 por request para ~1 a cada 30 minutos

### 3. **Otimização de Consultas ao Banco**
- **Problema**: Múltiplas consultas separadas para dados do usuário e agente
- **Solução**: Consultas únicas otimizadas com todos os campos necessários
- **Impacto**: Redução do número de queries por ~50%

### 4. **Redução de Logs em Produção**
- **Problema**: Logs excessivos causando I/O desnecessário
- **Solução**: Logs condicionais baseados na variável `DEBUG_SESSION`
- **Impacto**: Melhoria de performance geral e redução de noise nos logs

## Configurações Adicionadas

### Variáveis de Ambiente (.env)
```
DEBUG_SESSION=false                 # Controla logs detalhados de sessão
BACKGROUND_API_KEY=your-key-here   # Chave para endpoints de background
```

## Novos Endpoints

### Background Tasks
- `POST /background/update-importacoes` - Atualiza importações em background
- `GET /background/health` - Health check do serviço

## Estrutura de Cache de Permissões

```python
session['permissions_cache'] = {
    'permissions_user_id': {
        'data': {...},           # Dados das permissões
        'cached_at': timestamp   # Timestamp do cache
    }
}
```

## Como Usar

### Para Atualizar Importações Manualmente
```bash
curl -X POST http://your-server/background/update-importacoes \
  -H "X-API-Key: your-secure-api-key" \
  -H "Content-Type: application/json"
```

### Para Configurar Cron Job (Linux/Mac)
```bash
# Adicionar ao crontab (crontab -e)
# Executar a cada 30 minutos
*/30 * * * * curl -X POST http://your-server/background/update-importacoes -H "X-API-Key: your-key"
```

### Para Windows Task Scheduler
- Criar tarefa para executar PowerShell script que chama o endpoint
- Agendar para executar periodicamente

## Métricas Esperadas

- **Tempo de Login**: Redução de 60-80%
- **Tempo de Carregamento Dashboard**: Redução de 40-60% na primeira visita, 80%+ nas seguintes
- **Consultas DB**: Redução de ~50% por sessão de usuário
- **Uso de CPU**: Redução de ~20-30% devido a menos logs e I/O

## Monitoramento

### Logs Importantes
- `[SESSION]` - Logs de sessão (apenas com DEBUG_SESSION=true)
- `[BACKGROUND]` - Logs de tarefas em background
- `[CACHE]` - Logs de cache de permissões (apenas em debug)

### Health Checks
- `/background/health` - Status do serviço de background tasks
- `/test-connection` - Status da conexão com Supabase

## Próximos Passos (Opcional)

1. **Implementar Redis para Cache Distribuído**
   - Para ambientes com múltiplas instâncias
   - Cache compartilhado entre instâncias

2. **Database Connection Pooling**
   - Otimizar conexões com Supabase
   - Reduzir latência de queries

3. **Lazy Loading de Dados**
   - Carregar dados do dashboard sob demanda
   - Paginação inteligente

4. **CDN para Assets Estáticos**
   - Acelerar carregamento de CSS/JS
   - Reduzir carga no servidor principal

## Rollback (Se Necessário)

Para reverter as mudanças:
1. Restaurar função `update_importacoes_processos()` no `auth.py`
2. Remover cache de permissões
3. Restaurar logs originais
4. Remover blueprint de background tasks

**Arquivos Modificados:**
- `routes/auth.py`
- `permissions.py` 
- `session_handler.py`
- `app.py`
- `.env`
- **Novo:** `routes/background_tasks.py`
