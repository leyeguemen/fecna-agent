"""Envío de correos transaccionales con la API HTTP de Brevo.

Render (plan gratis) bloquea los puertos SMTP, por eso se usa HTTP. Variables:
  BREVO_API_KEY  clave de la API de Brevo (Settings → SMTP & API → API keys).
  MAIL_FROM      remitente verificado en Brevo (Senders), p. ej. tu Gmail.
  MAIL_FROM_NAME nombre que ve el destinatario (por defecto «NATIA»).
"""

import html
import logging
import os

import requests

logger = logging.getLogger("fecna.api")

_URL = "https://api.brevo.com/v3/smtp/email"


def configured() -> bool:
    return bool(os.environ.get("BREVO_API_KEY") and os.environ.get("MAIL_FROM"))


def send(to: str, subject: str, text: str, html_body: str) -> None:
    """Envía un correo. Lanza RuntimeError si falta configuración o Brevo lo rechaza."""
    if not configured():
        raise RuntimeError("El envío de correos no está configurado (BREVO_API_KEY, MAIL_FROM).")
    resp = requests.post(
        _URL,
        headers={"api-key": os.environ["BREVO_API_KEY"], "accept": "application/json"},
        json={
            "sender": {"email": os.environ["MAIL_FROM"],
                       "name": os.environ.get("MAIL_FROM_NAME") or "NATIA"},
            "to": [{"email": to}],
            "subject": subject,
            "textContent": text,
            "htmlContent": html_body,
        },
        timeout=15,
    )
    if resp.status_code >= 300:
        raise RuntimeError(f"Brevo respondió {resp.status_code}: {resp.text[:200]}")


def send_reset_code(to: str, code: str, minutes: int) -> None:
    """Correo con el código para crear una contraseña nueva. Los errores solo se registran:
    se llama en segundo plano y la respuesta al cliente no debe depender de si la cuenta existe."""
    text = (f"Tu código para crear una nueva contraseña en NATIA es {code}.\n\n"
            f"Vence en {minutes} minutos. Si no lo pediste, ignora este correo: "
            "tu contraseña sigue igual.")
    body = f"""<div style="font-family:Arial,sans-serif;max-width:420px;margin:auto;color:#0B1F33">
<h2 style="color:#023E8A;margin:0 0 12px">Recupera tu contraseña</h2>
<p>Usa este código en la app para crear una nueva contraseña:</p>
<p style="font-size:32px;font-weight:bold;letter-spacing:8px;color:#023E8A;margin:16px 0">{html.escape(code)}</p>
<p style="color:#4A6378;font-size:13px">Vence en {minutes} minutos. Si no lo pediste, ignora este
correo: tu contraseña sigue igual.</p>
</div>"""
    try:
        send(to, f"{code} es tu código de NATIA", text, body)
    except Exception as exc:  # noqa: BLE001 — ver docstring
        logger.error("No se pudo enviar el código de recuperación: %s", exc)
