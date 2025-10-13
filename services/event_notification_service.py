"""Orquestra notificações por e-mail relacionadas aos eventos de colaboradores."""

import os
from datetime import datetime
from typing import Any, Dict, Optional

from extensions import supabase_admin

from .email_service import EmailService


class EventNotificationService:
    """Centraliza o envio de e-mails para contabilidade e RH."""

    def __init__(self) -> None:
        self.email_service = EmailService()
        self.accounting_email = os.getenv(
            "EMAIL_NOTIF_CONTABILIDADE",
            "alexandre.choski@gmail.com",
        )
        self.rh_email = os.getenv(
            "EMAIL_NOTIF_RH_UNIQUE",
            "system@uniqueaduaneira.com.br",
        )
        self.portal_url = os.getenv(
            "PORTAL_PUBLIC_URL",
            os.getenv("BASE_URL", "http://192.168.0.75:5000"),
        )

    def _carregar_evento(self, evento_id: str) -> Optional[Dict[str, Any]]:
        try:
            response = (
                supabase_admin.table("rh_historico_colaborador")
                .select(
                    "id, colaborador_id, data_evento, tipo_evento, status_contabilidade, "
                    "descricao_e_motivos, obs_contabilidade, salario_mensal, dados_adicionais_jsonb, "
                    "colaborador:rh_colaboradores!rh_historico_colaborador_colaborador_id_fkey("
                    "nome_completo, cpf, matricula, email_corporativo"
                    "), "
                    "cargo:rh_cargos(nome_cargo), "
                    "departamento:rh_departamentos(nome_departamento), "
                    "empresa:rh_empresas(razao_social)"
                )
                .eq("id", evento_id)
                .single()
                .execute()
            )
            return response.data if response and response.data else None
        except Exception as exc:
            print(f"[NOTIFY] Falha ao carregar evento {evento_id}: {exc}")
            return None

    @staticmethod
    def _formatar_data(data_iso: Optional[str]) -> str:
        if not data_iso:
            return "-"
        try:
            if len(data_iso) == 10:
                return datetime.strptime(data_iso, "%Y-%m-%d").strftime("%d/%m/%Y")
            return datetime.fromisoformat(data_iso).strftime("%d/%m/%Y")
        except ValueError:
            return data_iso

    @staticmethod
    def _formatar_moeda(valor: Optional[float]) -> str:
        if valor in (None, "", 0):
            return "-"
        try:
            return f"R$ {float(valor):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
        except (TypeError, ValueError):
            return str(valor)

    def _montar_link_evento(self, evento_id: str) -> str:
        base_url = (self.portal_url or "").rstrip("/")
        return f"{base_url}/contabilidade"

    def notify_accounting_new_event(self, evento_id: str) -> bool:
        if not self.email_service.is_configured:
            return False
        if not self.accounting_email:
            print("[NOTIFY] E-mail de contabilidade não configurado. Notificação ignorada.")
            return False

        evento = self._carregar_evento(evento_id)
        if not evento:
            return False

        colaborador = evento.get("colaborador") or {}
        subject = (
            f"[UniSystem] Novo evento RH: {evento.get('tipo_evento', 'Evento')} - "
            f"{colaborador.get('nome_completo', 'Colaborador')}"
        )

        data_evento = self._formatar_data(evento.get("data_evento"))
        salario = self._formatar_moeda(evento.get("salario_mensal"))
        descricao = evento.get("descricao_e_motivos") or "Sem observações"

        html_body = f"""
            <h3>Nova pendência para contabilidade</h3>
            <p>Um novo evento de RH foi registrado e precisa de validação contábil.</p>
            <ul>
                <li><strong>Colaborador:</strong> {colaborador.get('nome_completo', '-')}</li>
                <li><strong>CPF:</strong> {colaborador.get('cpf', '-')}</li>
                <li><strong>Matrícula:</strong> {colaborador.get('matricula', '-')}</li>
                <li><strong>Tipo de evento:</strong> {evento.get('tipo_evento', '-')}</li>
                <li><strong>Data do evento:</strong> {data_evento}</li>
                <li><strong>Salário atual:</strong> {salario}</li>
                <li><strong>Observações do RH:</strong> {descricao}</li>
            </ul>
            <p>Acesse o portal para registrar a baixa: <a href="{self._montar_link_evento(evento_id)}">Portal Contabilidade</a></p>
        """

        text_body = (
            "Nova pendência para contabilidade\n"
            f"Colaborador: {colaborador.get('nome_completo', '-')}\n"
            f"CPF: {colaborador.get('cpf', '-')}\n"
            f"Matrícula: {colaborador.get('matricula', '-')}\n"
            f"Tipo de evento: {evento.get('tipo_evento', '-')}\n"
            f"Data do evento: {data_evento}\n"
            f"Salário atual: {salario}\n"
            f"Observações do RH: {descricao}\n"
            f"Portal: {self._montar_link_evento(evento_id)}"
        )

        return self.email_service.send_email(self.accounting_email, subject, html_body, text_body)

    def notify_rh_event_closed(self, evento_id: str) -> bool:
        if not self.email_service.is_configured:
            return False
        if not self.rh_email:
            print("[NOTIFY] E-mail do RH não configurado. Notificação ignorada.")
            return False

        evento = self._carregar_evento(evento_id)
        if not evento:
            return False

        colaborador = evento.get("colaborador") or {}
        subject = (
            f"[UniSystem] Evento concluído pela contabilidade: {evento.get('tipo_evento', 'Evento')}"
        )

        data_evento = self._formatar_data(evento.get("data_evento"))
        observacoes = evento.get("obs_contabilidade") or "Sem observações contábeis"

        html_body = f"""
            <h3>Evento concluído pela contabilidade</h3>
            <p>A contabilidade registrou a baixa de um evento.</p>
            <ul>
                <li><strong>Colaborador:</strong> {colaborador.get('nome_completo', '-')}</li>
                <li><strong>Tipo de evento:</strong> {evento.get('tipo_evento', '-')}</li>
                <li><strong>Data do evento:</strong> {data_evento}</li>
                <li><strong>Status contábil:</strong> {evento.get('status_contabilidade', '-')}</li>
                <li><strong>Observações contabilidade:</strong> {observacoes}</li>
            </ul>
        """

        text_body = (
            "Evento concluído pela contabilidade\n"
            f"Colaborador: {colaborador.get('nome_completo', '-')}\n"
            f"Tipo de evento: {evento.get('tipo_evento', '-')}\n"
            f"Data do evento: {data_evento}\n"
            f"Status contábil: {evento.get('status_contabilidade', '-')}\n"
            f"Observações contabilidade: {observacoes}"
        )

        return self.email_service.send_email(self.rh_email, subject, html_body, text_body)
