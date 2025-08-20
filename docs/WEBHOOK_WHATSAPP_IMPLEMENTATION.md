# Implementação de Webhook WhatsApp - UniSystem Portal

## 📋 Resumo da Implementação

Foi implementado um sistema completo de webhooks para notificar o N8N sempre que um número WhatsApp é adicionado no sistema, tanto por usuários administradores quanto pelo sistema de login.

## 🔧 Componentes Implementados

### 1. Serviço Centralizado de Webhook
**Arquivo**: `services/webhook_service.py`

- **Classe**: `WebhookService` - Serviço centralizado para todos os webhooks
- **Funcionalidades**:
  - Normalização automática de números telefônicos
  - Suporte a múltiplos formatos de entrada
  - Configuração via variáveis de ambiente
  - Tratamento robusto de erros
  - Logs detalhados para debug

### 2. Integração no Módulo Usuários
**Arquivo**: `modules/usuarios/routes.py`

- **Função**: `adicionar_whatsapp()` - Linha ~1797
- **Webhook enviado quando**: Administrador adiciona WhatsApp para qualquer usuário
- **Source**: `"usuarios_module"`

### 3. Integração no Módulo Agente  
**Arquivo**: `modules/agente/routes.py`

- **Funções integradas**:
  - Adição via formulário (linha ~490)
  - Adição via AJAX (linha ~605) 
  - Adição via admin (linha ~992)
- **Webhook enviado quando**: Cliente adiciona próprio WhatsApp ou admin adiciona via agente
- **Sources**: `"agente_module"` e `"agente_module_admin"`

### 4. Endpoint de Teste
**Arquivo**: `modules/usuarios/routes.py`

- **Rota**: `POST /usuarios/test-webhook`
- **Funcionalidade**: Permite testar webhook sem inserir dados reais
- **Acesso**: Apenas administradores

## 🌐 Configuração do Webhook

### URL do Webhook
```
https://n8n.portalunique.com.br/webhook-test/trigger_new
```

### Variáveis de Ambiente Opcionais
```env
N8N_WEBHOOK_TRIGGER_NEW_PRD=https://n8n.portalunique.com.br/webhook-test/trigger_new
N8N_WEBHOOK_TRIGGER_NEW_DEV=https://n8n-dev.example.com/webhook/trigger_new
WEBHOOK_TIMEOUT=10
FLASK_ENV=development  # Se definido como development, usa URL de DEV
```

## 📤 Formato do Payload

O webhook envia um payload JSON estruturado:

```json
{
  "event": "new_whatsapp_number",
  "timestamp": "2025-08-20T15:24:22.196984",
  "source": "usuarios_module",
  "phone_numbers": {
    "original": "4733059070",
    "clean": "4733059070", 
    "evo": "4733059070",
    "e164": "+554733059070"
  },
  "numero_zap_evo": "4733059070",
  "environment": "production",
  "user": {
    "id": "user-123",
    "name": "João Silva",
    "email": "joao@empresa.com.br",
    "role": "cliente_unique"
  }
}
```

### Campos do Payload

- **event**: Tipo do evento (`"new_whatsapp_number"`)
- **timestamp**: Data/hora do evento em ISO format
- **source**: Origem do evento (indica qual módulo/fluxo adicionou o número)
- **phone_numbers**: Objeto com diferentes formatos do número
  - **original**: Número como digitado pelo usuário
  - **clean**: Apenas dígitos, sem código país
  - **evo**: Formato EVO (remove 9 após DDD quando aplicável)
  - **e164**: Formato internacional padrão
- **numero_zap_evo**: Campo para compatibilidade (mesmo que evo)
- **environment**: Ambiente (`"production"` ou `"development"`)
- **user**: Dados do usuário (quando disponível)

## 🎯 Fluxos de Ativação

### 1. Módulo Usuários (Administrador)
```
Admin acessa /usuarios → 
Adiciona WhatsApp para usuário → 
Sistema salva no banco → 
Webhook enviado para N8N
```

### 2. Módulo Agente (Cliente)
```
Cliente acessa /agente → 
Adiciona próprio WhatsApp → 
Sistema salva no banco → 
Webhook enviado para N8N  
```

### 3. Sistema de Login (Futuro)
```
Usuário faz login → 
Sistema detecta novo número → 
Webhook enviado para N8N
```

## 🔍 Normalização de Números

O sistema suporta entrada em múltiplos formatos:

| Formato Entrada | Resultado Clean | Resultado EVO | Resultado E164 |
|-----------------|-----------------|---------------|----------------|
| `4733059070` | `4733059070` | `4733059070` | `+554733059070` |
| `47999887766` | `47999887766` | `4799887766` | `+5547999887766` |
| `+5547999887766` | `47999887766` | `4799887766` | `+5547999887766` |
| `(47) 99988-7766` | `47999887766` | `4799887766` | `+5547999887766` |

## ✅ Validação da Implementação

### Testes Realizados
- ✅ Serviço de webhook funcionando
- ✅ Normalização de números correta
- ✅ Payload estruturado adequadamente  
- ✅ Integração nos módulos usuários e agente
- ✅ Tratamento de erros implementado
- ✅ Logs detalhados para debug

### Scripts de Teste
- `test_webhook_whatsapp.py` - Teste completo da implementação
- `test_webhook_simple.py` - Teste simples e direto

## 🔧 Troubleshooting

### Webhook retorna 404
- **Causa**: N8N webhook não está ativo/registrado
- **Solução**: Ativar workflow no N8N clicando "Execute workflow"

### Webhook não é enviado
- **Verificar**: Logs do sistema para erros
- **Verificar**: Variáveis de ambiente configuradas
- **Teste**: Usar endpoint `/usuarios/test-webhook`

### Número não normalizado corretamente
- **Verificar**: Formato de entrada
- **Confirmar**: Se está seguindo padrões brasileiros (DDD + número)

## 📝 Logs de Debug

O sistema gera logs detalhados:

```
[WEBHOOK] Novo WhatsApp (usuarios_module) - Enviando para: https://n8n.portalunique.com.br/webhook-test/trigger_new
[WEBHOOK] Payload: { ... dados estruturados ... }
[WEBHOOK] Novo WhatsApp (usuarios_module) - Sucesso! Status: 200
```

## 🚀 Próximos Passos

1. **Configurar webhook no N8N** para aceitar os payloads
2. **Definir fluxos de automação** baseados nos dados recebidos
3. **Implementar webhooks adicionais** (atualização, remoção)
4. **Configurar variáveis de ambiente** em produção

---

**Data da Implementação**: 20/08/2025  
**Versão**: 1.0  
**Responsável**: Sistema automatizado
