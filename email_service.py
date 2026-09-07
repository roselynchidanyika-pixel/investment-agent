import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from typing import Optional


def send_report_email(
    recipient: str,
    subject: str,
    body: str,
    attachment_path: Optional[str] = None,
    smtp_host: Optional[str] = None,
    smtp_port: Optional[int] = None,
    smtp_user: Optional[str] = None,
    smtp_pass: Optional[str] = None,
    use_tls: bool = True,
) -> dict:
    smtp_host = smtp_host or os.environ.get("SMTP_HOST", "")
    smtp_port = smtp_port or int(os.environ.get("SMTP_PORT", "587"))
    smtp_user = smtp_user or os.environ.get("SMTP_USER", "") or os.environ.get("SMTP_USERNAME", "")
    smtp_pass = smtp_pass or os.environ.get("SMTP_PASS", "") or os.environ.get("SMTP_PASSWORD", "")
    smtp_from = os.environ.get("SMTP_FROM", "")

    if not all([smtp_host, smtp_user, smtp_pass]):
        return {
            "success": False,
            "message": (
                "Email not sent. SMTP credentials not configured. "
                "Please set SMTP_HOST, SMTP_PORT, SMTP_USER (or SMTP_USERNAME), "
                "SMTP_PASS (or SMTP_PASSWORD) as environment variables before using "
                "this feature. Example:\n"
                "  set SMTP_HOST=smtp.gmail.com\n"
                "  set SMTP_PORT=587\n"
                "  set SMTP_USER=your_email@gmail.com\n"
                "  set SMTP_PASS=your_app_password"
            ),
        }

    if not recipient or "@" not in recipient:
        return {"success": False, "message": "Invalid recipient email address."}

    msg = MIMEMultipart()
    msg["From"] = smtp_from or smtp_user
    msg["To"] = recipient
    msg["Subject"] = subject

    msg.attach(MIMEText(body, "plain"))

    if attachment_path and os.path.exists(attachment_path):
        try:
            with open(attachment_path, "rb") as f:
                part = MIMEBase("application", "octet-stream")
                part.set_payload(f.read())
            encoders.encode_base64(part)
            filename = os.path.basename(attachment_path)
            part.add_header("Content-Disposition", f"attachment; filename={filename}")
            msg.attach(part)
        except Exception as e:
            return {"success": False, "message": f"Failed to attach file: {str(e)}"}

    try:
        server = smtplib.SMTP(smtp_host, smtp_port)
        if use_tls:
            server.starttls()
        server.login(smtp_user, smtp_pass)
        server.sendmail(smtp_user, [recipient], msg.as_string())
        server.quit()
        return {"success": True, "message": f"Report sent successfully to {recipient}."}
    except smtplib.SMTPAuthenticationError:
        return {"success": False, "message": "SMTP authentication failed. Check your credentials."}
    except smtplib.SMTPConnectError:
        return {"success": False, "message": f"Could not connect to SMTP server at {smtp_host}:{smtp_port}."}
    except Exception as e:
        return {"success": False, "message": f"Email sending failed: {str(e)}"}


def build_email_body(
    project_name: str,
    npv: float,
    irr: float,
    mirr: float,
    roi: float,
    payback: float,
    risk_level: str,
    decision: str,
    main_reason: str,
    supporting_points: Optional[List[str]] = None,
    custom_message: str = "",
    currency: str = "USD",
    currency_strategy: Optional[str] = None,
    fx_risk: Optional[str] = None,
) -> str:
    from data_validation import format_currency

    if payback == float("inf"):
        payback_str = "Never recovers"
    else:
        payback_str = f"{payback:.2f} years"

    lines = []
    lines.append("Dear recipient,")
    lines.append("")
    lines.append(f"Please find attached the Investment Decision Report for {project_name}.")
    lines.append("")
    lines.append("Summary of the analysis:")
    lines.append(f"- Net Present Value (NPV): {format_currency(npv, currency)}")
    lines.append(f"- Internal Rate of Return (IRR): {irr:.2%}")
    lines.append(f"- Modified Internal Rate of Return (MIRR): {mirr:.2%}")
    lines.append(f"- Return on Investment (ROI): {roi:.2%}")
    lines.append(f"- Payback Period: {payback_str}")
    lines.append(f"- Risk Level: {risk_level}")
    if fx_risk:
        lines.append(f"- FX Risk: {fx_risk}")
    if currency_strategy:
        lines.append(f"- Recommended Currency Strategy: {currency_strategy}")
    lines.append("")
    lines.append(f"FINAL DECISION: {decision}")
    if main_reason:
        reason_line = f"Main reason: {main_reason}"
        if supporting_points:
            reason_line += " Reasons:"
        lines.append(reason_line)
        for point in supporting_points or []:
            point = point.strip()
            if point.startswith("[+]") or point.startswith("[-]"):
                point = point[3:].strip()
            lines.append(f"- {point}")
    if custom_message:
        lines.append("")
        lines.append(custom_message.strip())
    lines.append("")
    lines.append(
        "This email was generated automatically by the "
        "Integrated Investment Decision Agent for Capital Projects."
    )
    lines.append("")

    return "\n".join(lines)
