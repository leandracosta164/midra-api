"""Production-capable SMTP transport for explicitly authorized Engineering proposal delivery."""
from __future__ import annotations

from email.message import EmailMessage
from email.utils import make_msgid
import smtplib
from typing import Any


class SMTPProposalDeliveryTransport:
    def __init__(self, *, host: str, port: int, from_email: str, username: str | None = None,
                 password: str | None = None, use_tls: bool = True, use_ssl: bool = False, response_url: str | None = None):
        self.host = str(host or "").strip()
        self.port = int(port)
        self.from_email = str(from_email or "").strip()
        self.username = str(username or "").strip() or None
        self.password = password or None
        self.use_tls = bool(use_tls)
        self.use_ssl = bool(use_ssl)
        self.response_url = str(response_url or "").strip() or None
        if not self.host or not self.from_email:
            raise ValueError("proposal email transport is not configured")
        if self.use_ssl and self.use_tls:
            raise ValueError("proposal email transport cannot enable both SSL and STARTTLS")

    def send(self, *, recipient: str, subject: str, filename: str, mime_type: str, content: bytes) -> dict[str, Any]:
        msg = EmailMessage()
        msg["From"] = self.from_email
        msg["To"] = recipient
        msg["Subject"] = subject
        msg["Message-ID"] = make_msgid(domain=self.from_email.split("@")[-1] if "@" in self.from_email else None)
        body=(
            "Please find the attached MIDRA Engineering proposal. "
            "This email transmits the approved proposal document only; acceptance requires a separate explicit client response."
        )
        if self.response_url:
            body += f"\n\nView the exact proposal and respond securely: {self.response_url}"
        msg.set_content(body)
        maintype, subtype = (mime_type.split("/", 1) + ["octet-stream"])[:2]
        msg.add_attachment(content, maintype=maintype, subtype=subtype, filename=filename)
        smtp_cls = smtplib.SMTP_SSL if self.use_ssl else smtplib.SMTP
        with smtp_cls(self.host, self.port, timeout=30) as client:
            if self.use_tls:
                client.starttls()
            if self.username:
                client.login(self.username, self.password or "")
            refused = client.send_message(msg)
        if refused:
            raise RuntimeError("proposal email transport refused one or more recipients")
        return {"provider_message_id": str(msg["Message-ID"])}
