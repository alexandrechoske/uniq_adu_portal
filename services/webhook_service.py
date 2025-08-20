"""
Serviço centralizado para webhooks do sistema UniSystem Portal
Responsável por notificar sistemas externos sobre eventos importantes

Eventos suportados:
- Cadastro de números WhatsApp (usuários e sistema de login)
- Atualizações de dados de usuários
- Outros eventos do sistema

Configuração via .env:
- N8N_WEBHOOK_TRIGGER_NEW_PRD: URL de produção para novos números WhatsApp
- N8N_WEBHOOK_TRIGGER_NEW_DEV: URL de desenvolvimento (opcional)
- WEBHOOK_TIMEOUT: Timeout para requisições (padrão: 10 segundos)
"""

import os
import re
import requests
import json
from datetime import datetime
from typing import Dict, Any, Optional, List


class WebhookService:
    """Serviço centralizado para webhooks"""
    
    def __init__(self):
        self.timeout = int(os.getenv('WEBHOOK_TIMEOUT', '10'))
        self.default_headers = {'Content-Type': 'application/json'}
        
        # URLs configuráveis
        self.n8n_new_whatsapp_prd = os.getenv('N8N_WEBHOOK_TRIGGER_NEW_PRD', 
                                             'https://n8n.portalunique.com.br/webhook-test/trigger_new')
        self.n8n_new_whatsapp_dev = os.getenv('N8N_WEBHOOK_TRIGGER_NEW_DEV')
        
        # Ambiente
        self.flask_env = os.getenv('FLASK_ENV', '').lower()
        self.is_development = self.flask_env == 'development'
    
    def _get_webhook_url(self, webhook_type: str = 'new_whatsapp') -> str:
        """Retorna a URL do webhook baseada no ambiente e tipo"""
        if webhook_type == 'new_whatsapp':
            if self.is_development and self.n8n_new_whatsapp_dev:
                return self.n8n_new_whatsapp_dev
            return self.n8n_new_whatsapp_prd
        
        raise ValueError(f"Tipo de webhook não suportado: {webhook_type}")
    
    def _normalize_phone_number(self, numero: str) -> Dict[str, str]:
        """
        Normaliza número de telefone para diferentes formatos
        Retorna dict com números originais e normalizados
        """
        numero = str(numero or '')
        
        # Remover formatação
        numero_limpo = re.sub(r'\D', '', numero)
        
        # Remover código do país se presente (+55)
        if numero_limpo.startswith('55') and len(numero_limpo) > 11:
            numero_limpo = numero_limpo[2:]
        
        # Formato EVO: remover '9' após DDD quando aplicável (ex.: 41996650141 -> 4196650141)
        numero_evo = numero_limpo
        if len(numero_limpo) == 11 and numero_limpo[2] == '9':
            numero_evo = numero_limpo[:2] + numero_limpo[3:]
        
        return {
            'original': numero,
            'clean': numero_limpo,
            'evo': numero_evo,
            'e164': f"+55{numero_limpo}" if numero_limpo else ""
        }
    
    def _make_webhook_request(self, url: str, payload: Dict[str, Any], 
                            context: str = "") -> bool:
        """Executa requisição webhook com tratamento de erros"""
        try:
            print(f"[WEBHOOK] {context} - Enviando para: {url}")
            print(f"[WEBHOOK] Payload: {json.dumps(payload, indent=2)}")
            
            response = requests.post(
                url, 
                json=payload, 
                headers=self.default_headers, 
                timeout=self.timeout
            )
            
            if response.status_code == 200:
                print(f"[WEBHOOK] {context} - Sucesso! Status: {response.status_code}")
                return True
            else:
                print(f"[WEBHOOK] {context} - Falha! Status: {response.status_code}")
                print(f"[WEBHOOK] Resposta: {response.text[:500]}")  # Limitar log
                return False
                
        except requests.exceptions.Timeout:
            print(f"[WEBHOOK] {context} - Timeout após {self.timeout}s")
            return False
        except requests.exceptions.ConnectionError:
            print(f"[WEBHOOK] {context} - Erro de conexão")
            return False
        except Exception as e:
            print(f"[WEBHOOK] {context} - Erro inesperado: {str(e)}")
            return False
    
    def notify_new_whatsapp(self, numero: str, user_data: Optional[Dict] = None, 
                           source: str = "system", test_mode: bool = False) -> bool:
        """
        Notifica N8N sobre novo número WhatsApp cadastrado
        
        Args:
            numero: Número WhatsApp (qualquer formato)
            user_data: Dados do usuário (opcional)
            source: Origem do cadastro ('usuarios_module', 'agente_module', 'login_system')
            test_mode: Se True, apenas valida mas não envia webhook
        
        Returns:
            bool: True se webhook foi enviado com sucesso (ou simulado em test_mode)
        """
        try:
            url = self._get_webhook_url('new_whatsapp')
            
            # Normalizar número
            phone_numbers = self._normalize_phone_number(numero)
            
            # Montar payload
            payload = {
                'event': 'new_whatsapp_number',
                'timestamp': datetime.now().isoformat(),
                'source': source,
                'phone_numbers': phone_numbers,
                'numero_zap_evo': phone_numbers['evo'],  # Compatibilidade
                'environment': 'development' if self.is_development else 'production'
            }
            
            # Adicionar dados do usuário se disponível
            if user_data:
                payload['user'] = {
                    'id': user_data.get('id'),
                    'name': user_data.get('name'),
                    'email': user_data.get('email'),
                    'role': user_data.get('role')
                }
            
            # Se é test_mode, apenas retornar validação
            if test_mode:
                print(f"[WEBHOOK] Modo teste - payload preparado: {json.dumps(payload, indent=2)}")
                return True
            
            # Enviar webhook
            context = f"Novo WhatsApp ({source})"
            return self._make_webhook_request(url, payload, context)
            
        except Exception as e:
            print(f"[WEBHOOK] Erro ao notificar novo WhatsApp: {str(e)}")
            return False
    
    def notify_whatsapp_updated(self, numero: str, changes: Dict, 
                               user_data: Optional[Dict] = None) -> bool:
        """
        Notifica sobre atualização de número WhatsApp
        
        Args:
            numero: Número WhatsApp
            changes: Dicionário com as mudanças
            user_data: Dados do usuário
        
        Returns:
            bool: True se webhook foi enviado com sucesso
        """
        try:
            url = self._get_webhook_url('new_whatsapp')  # Mesmo endpoint por enquanto
            
            phone_numbers = self._normalize_phone_number(numero)
            
            payload = {
                'event': 'whatsapp_updated',
                'timestamp': datetime.now().isoformat(),
                'phone_numbers': phone_numbers,
                'changes': changes,
                'environment': 'development' if self.is_development else 'production'
            }
            
            if user_data:
                payload['user'] = {
                    'id': user_data.get('id'),
                    'name': user_data.get('name'),
                    'email': user_data.get('email'),
                    'role': user_data.get('role')
                }
            
            context = "Atualização WhatsApp"
            return self._make_webhook_request(url, payload, context)
            
        except Exception as e:
            print(f"[WEBHOOK] Erro ao notificar atualização WhatsApp: {str(e)}")
            return False
    
    def notify_whatsapp_removed(self, numero: str, user_data: Optional[Dict] = None) -> bool:
        """
        Notifica sobre remoção de número WhatsApp
        
        Args:
            numero: Número WhatsApp removido
            user_data: Dados do usuário
            
        Returns:
            bool: True se webhook foi enviado com sucesso
        """
        try:
            url = self._get_webhook_url('new_whatsapp')  # Mesmo endpoint por enquanto
            
            phone_numbers = self._normalize_phone_number(numero)
            
            payload = {
                'event': 'whatsapp_removed',
                'timestamp': datetime.now().isoformat(),
                'phone_numbers': phone_numbers,
                'environment': 'development' if self.is_development else 'production'
            }
            
            if user_data:
                payload['user'] = {
                    'id': user_data.get('id'),
                    'name': user_data.get('name'),
                    'email': user_data.get('email'),
                    'role': user_data.get('role')
                }
            
            context = "Remoção WhatsApp"
            return self._make_webhook_request(url, payload, context)
            
        except Exception as e:
            print(f"[WEBHOOK] Erro ao notificar remoção WhatsApp: {str(e)}")
            return False
    
    def test_webhook_connectivity(self, webhook_type: str = 'new_whatsapp') -> Dict[str, Any]:
        """
        Testa conectividade com webhook
        
        Args:
            webhook_type: Tipo do webhook a testar
            
        Returns:
            Dict com resultado do teste
        """
        try:
            url = self._get_webhook_url(webhook_type)
            
            test_payload = {
                'event': 'connectivity_test',
                'timestamp': datetime.now().isoformat(),
                'test': True,
                'environment': 'development' if self.is_development else 'production'
            }
            
            success = self._make_webhook_request(url, test_payload, "Teste de conectividade")
            
            return {
                'success': success,
                'url': url,
                'environment': 'development' if self.is_development else 'production',
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }


# Instância global do serviço
webhook_service = WebhookService()


# Funções de conveniência para compatibilidade
def notify_new_whatsapp_number(numero: str, user_data: Optional[Dict] = None, 
                              source: str = "system", test_mode: bool = False) -> bool:
    """Função de conveniência para notificar novo número WhatsApp"""
    return webhook_service.notify_new_whatsapp(numero, user_data, source, test_mode)


def test_n8n_webhook() -> Dict[str, Any]:
    """Função de conveniência para testar webhook N8N"""
    return webhook_service.test_webhook_connectivity('new_whatsapp')
