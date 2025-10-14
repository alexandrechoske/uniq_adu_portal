"""Serviço simples para envio de e-mails via SMTP."""

import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formataddr
from typing import Iterable, List, Optional


class EmailService:
    """Gerencia o envio de e-mails usando configurações de ambiente."""

    def __init__(self) -> None:
        self.host = os.getenv("SMTP_HOST", "smtp.gmail.com")
        self.port = int(os.getenv("SMTP_PORT", "587"))
        self.username = os.getenv("SMTP_USER")
        self.password = os.getenv("SMTP_PASSWORD")
        self.use_tls = os.getenv("SMTP_USE_TLS", "true").lower() == "true"
        self.enabled = os.getenv("SMTP_ENABLED", "true").lower() == "true"
        self.default_sender = os.getenv("SMTP_DEFAULT_SENDER", self.username or "")
        self.from_name = os.getenv("SMTP_FROM_NAME", "UniSystem Portal")
        self.timeout = int(os.getenv("SMTP_TIMEOUT", "30"))

    @property
    def is_configured(self) -> bool:
        return bool(self.enabled and self.host and self.username and self.password)

    def _normalize_recipients(self, recipients: Iterable[str] | str) -> List[str]:
        if isinstance(recipients, str):
            recipients = [recipients]
        return [email.strip() for email in recipients if email and email.strip()]

    def send_email(
        self,
        recipients: Iterable[str] | str,
        subject: str,
        html_body: str,
        text_body: Optional[str] = None,
    ) -> bool:
        if not self.is_configured:
            print("[EMAIL] Configuração SMTP ausente ou desabilitada. Notificação ignorada.")
            return False

        destinatarios = self._normalize_recipients(recipients)
        if not destinatarios:
            print("[EMAIL] Nenhum destinatário informado. Notificação ignorada.")
            return False

        print(
            "[EMAIL] Preparando envio",
            {
                "host": self.host,
                "port": self.port,
                "use_tls": self.use_tls,
                "from": self.default_sender or self.username,
                "to": destinatarios,
                "subject": subject,
            }
        )

        mensagem = MIMEMultipart("alternative")
        mensagem["Subject"] = subject
        mensagem["From"] = formataddr((self.from_name, self.default_sender or self.username))
        mensagem["To"] = ", ".join(destinatarios)

        if text_body:
            mensagem.attach(MIMEText(text_body, "plain", "utf-8"))
        mensagem.attach(MIMEText(html_body, "html", "utf-8"))

        try:
            with smtplib.SMTP(self.host, self.port, timeout=self.timeout) as server:
                print("[EMAIL] Conexão SMTP estabelecida, iniciando handshake.")
                if self.use_tls:
                    print("[EMAIL] Iniciando STARTTLS.")
                    server.starttls()
                    print("[EMAIL] Canal TLS ativo.")
                print("[EMAIL] Efetuando autenticação SMTP.")
                server.login(self.username, self.password)
                print("[EMAIL] Autenticação concluída, enviando mensagem.")
                server.sendmail(mensagem["From"], destinatarios, mensagem.as_string())
            print(f"[EMAIL] Notificação enviada para {destinatarios} - Assunto: {subject}")
            return True
        except Exception as exc:
            print(f"[EMAIL] Falha ao enviar notificação: {exc}")
            return False
