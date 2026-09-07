"""Secure email service for sending the management report.

The SENDER is configured ONLY through secrets, never typed by the user:
  1) Streamlit secrets (preferred) — `.streamlit/secrets.toml` with:

         [smtp]
         host = "smtp.example.com"
         port = "587"
         username = "sender@example.com"
         password = "app-password-or-token"
         from_addr = "Sender <sender@example.com>"

     or the SMTP_* entries in Streamlit Cloud / your environment, or
  2) environment variables SMTP_HOST, SMTP_PORT, SMTP_USERNAME,
     SMTP_PASSWORD, SMTP_FROM.

The user ONLY enters the recipient address, subject and optional message.
Credentials are never displayed, stored in the UI, or sent back to the client.
The recipient is never restricted — any valid email address is accepted.
"""

from __future__ import annotations

import os
import re
import smtplib
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Any

REQUIRED_KEYS = ["host", "port", "username", "password", "from_addr"]
_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def validate_recipient(email: str) -> tuple[bool, str]:
    """Return (ok, message) for a recipient address. Never restricts domains."""
    email = (email or "").strip()
    if not email:
        return False, "Please enter the recipient's email address."
    if len(email) > 320 or not _EMAIL_RE.match(email):
        return False, "That does not look like a valid email address (e.g. name@company.com)."
    return True, ""


def secure_smtp_config() -> dict[str, str]:
    """Load sender config from Streamlit secrets, then environment variables.

    Secret values are returned to the sender module in memory only; they are
    never surfaced in the UI.
    """
    cfg = {
        "host": os.getenv("SMTP_HOST", ""),
        "port": os.getenv("SMTP_PORT", "587"),
        "username": os.getenv("SMTP_USERNAME", ""),
        "password": os.getenv("SMTP_PASSWORD", ""),
        "from_addr": os.getenv("SMTP_FROM", ""),
    }
    try:
        import streamlit as st  # noqa: PLC0415

        secrets = st.secrets.get("smtp", {}) or {}
    except Exception:  # noqa: BLE001 (no Streamlit runtime in tests/scripts)
        secrets = {}
    for key in REQUIRED_KEYS:
        value = secrets.get(key)
        if value:
            cfg[key] = str(value)
    return cfg


def sender_status(cfg: dict[str, str] | None = None) -> dict[str, Any]:
    """Describe the sender configuration WITHOUT exposing any secret values."""
    cfg = cfg or secure_smtp_config()
    configured = is_configured(cfg)
    masked_password = "••••••••" if cfg.get("password") else ""
    return {
        "configured": configured,
        "host": (cfg.get("host") or "").strip() or "not set",
        "port": (cfg.get("port") or "").strip() or "not set",
        "username": (cfg.get("username") or "").strip() or "not set",
        "password": masked_password,
        "from_addr": (cfg.get("from_addr") or "").strip() or "not set",
        "source": "secrets / environment",
    }


def default_smtp_from_env() -> dict[str, str]:
    return secure_smtp_config()


def env_status() -> dict[str, bool]:
    cfg = secure_smtp_config()
    return {k: bool(cfg.get(k)) for k in REQUIRED_KEYS}


def is_configured(cfg: dict[str, str] | None = None) -> bool:
    if cfg is None:
        cfg = secure_smtp_config()
    for key in REQUIRED_KEYS:
        if not (cfg.get(key) or "").strip():
            return False
    try:
        int((cfg.get("port") or "0").strip())
    except (TypeError, ValueError):
        return False
    return True


def smtp_ready() -> bool:
    """True when a sender is fully configured through secrets/env."""
    return is_configured(secure_smtp_config())


def test_connection(cfg: dict[str, str] | None = None) -> tuple[bool, str]:
    """Connect, authenticate and disconnect from the sender — nothing is sent."""
    cfg = cfg or secure_smtp_config()
    if not is_configured(cfg):
        return False, "Sender is not configured (see Settings page)."
    try:
        host = cfg["host"].strip()
        port = int(cfg["port"].strip())
        with smtplib.SMTP(host, port, timeout=20) as server:
            server.ehlo()
            server.starttls()
            server.ehlo()
            server.login(cfg["username"].strip(), cfg["password"])
        return True, f"Connected and authenticated to {host}:{port} as {cfg['username'].strip()}."
    except smtplib.SMTPAuthenticationError:
        return False, "Authentication failed — check SMTP username/password in secrets."
    except Exception as e:  # noqa: BLE001
        return False, f"Connection failed: {e}"


def build_email_message(
    to_email: str,
    subject: str,
    body_text: str,
    attachments: list[tuple[str, bytes]] | None = None,
    from_addr: str = "",
) -> MIMEMultipart:
    msg = MIMEMultipart()
    msg["From"] = from_addr or os.getenv("SMTP_FROM", "")
    msg["To"] = to_email
    msg["Subject"] = subject
    msg.attach(MIMEText(body_text, "plain", "utf-8"))

    for fname, payload in attachments or []:
        part = MIMEApplication(payload, _subtype="pdf")
        part.add_header(
            "Content-Disposition", "attachment", filename=("utf-8", "", fname)
        )
        msg.attach(part)

    return msg


def send_email(
    to_email: str,
    subject: str,
    body_text: str,
    attachments: list[tuple[str, bytes]] | None = None,
    smtp_config: dict[str, str] | None = None,
) -> tuple[bool, str]:
    """Send the report to any valid recipient address. Returns (success, message).

    `smtp_config` optionally overrides the secrets/environment sender config.
    The recipient address is validated before any send attempt.
    """
    valid, msg0 = validate_recipient(to_email)
    if not valid:
        return False, msg0

    cfg = smtp_config or secure_smtp_config()
    if not is_configured(cfg):
        return (
            False,
            "Sender is not configured. Add the [smtp] section to .streamlit/secrets.toml "
            "(or set SMTP_HOST/ SMTP_PORT/ SMTP_USERNAME/ SMTP_PASSWORD/ SMTP_FROM as "
            "environment variables / Streamlit Cloud secrets) and restart the app.",
        )

    try:
        from_addr = cfg.get("from_addr", "")
        msg = build_email_message(
            to_email, subject, body_text, attachments, from_addr=from_addr
        )
        host = cfg.get("host", "").strip()
        port = int(cfg.get("port", "587"))
        username = cfg.get("username", "").strip()
        password = cfg.get("password", "")

        with smtplib.SMTP(host, port, timeout=30) as server:
            server.ehlo()
            server.starttls()
            server.ehlo()
            server.login(username, password)
            server.sendmail(from_addr, [to_email], msg.as_string())
        return True, f"Email sent successfully to {to_email}."
    except smtplib.SMTPAuthenticationError:
        return False, "SMTP authentication failed. Check SMTP username and password."
    except smtplib.SMTPRecipientsRefused as e:
        return False, f"Recipient refused by server: {e}"
    except Exception as e:  # noqa: BLE001
        return False, f"Email sending failed: {str(e)}"


def build_email_body(
    metrics: dict[str, Any],
    risk_level: str,
    decision_text: str,
    decision_reason: str,
    project_name: str,
) -> str:
    def money(v):
        return f"${v:,.0f}" if v is not None else "N/A"

    def pct(v):
        return f"{v:.2f}%" if v is not None else "N/A"

    lines = [
        f"Dear recipient,",
        "",
        f"Please find attached the Financial Engineering Investment Decision Report for {project_name}.",
        "",
        "Summary of the analysis:",
        f"- Net Present Value (NPV): {money(metrics.get('npv'))}",
        f"- Internal Rate of Return (IRR): {pct(metrics.get('irr'))}",
        f"- Modified Internal Rate of Return (MIRR): {pct(metrics.get('mirr'))}",
        f"- Return on Investment (ROI): {pct(metrics.get('roi'))}",
        f"- Payback Period: {metrics.get('payback') if metrics.get('payback') is not None else 'N/A'} years",
        f"- Risk Level: {risk_level}",
        "",
        f"FINAL DECISION: {decision_text}",
        f"Main reason: {decision_reason}",
        "",
        "This email was generated automatically by the Integrated Investment Decision Agent for Capital Project Evaluation.",
    ]
    return "\n".join(lines)