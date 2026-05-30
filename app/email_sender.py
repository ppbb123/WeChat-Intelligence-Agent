from __future__ import annotations

from email.mime.text import MIMEText
import smtplib


def send_email(
    host: str,
    port: int,
    user: str,
    password: str,
    to_address: str,
    subject: str,
    body: str,
) -> None:
    if not all([host, port, user, password, to_address]):
        raise ValueError("Email settings are incomplete.")

    message = MIMEText(body, "plain", "utf-8")
    message["From"] = user
    message["To"] = to_address
    message["Subject"] = subject

    with smtplib.SMTP_SSL(host, port) as server:
        server.login(user, password)
        server.sendmail(user, [to_address], message.as_string())

