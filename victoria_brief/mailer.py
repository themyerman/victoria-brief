import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText


def send(subject: str, html: str) -> None:
    """Send the digest via SMTP TLS. Reads config from env vars."""
    smtp_host = os.environ["EMAIL_SMTP_HOST"]
    smtp_port = int(os.environ.get("EMAIL_SMTP_PORT", "587"))
    smtp_user = os.environ["EMAIL_SMTP_USER"]
    smtp_pass = os.environ["EMAIL_SMTP_PASSWORD"]
    from_addr = os.environ["EMAIL_FROM"]
    to_addr = os.environ["EMAIL_TO"]

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = from_addr
    msg["To"] = to_addr
    msg.attach(MIMEText(html, "html", "utf-8"))

    with smtplib.SMTP(smtp_host, smtp_port) as server:
        server.ehlo()
        server.starttls()
        server.ehlo()
        server.login(smtp_user, smtp_pass)
        server.sendmail(from_addr, [to_addr], msg.as_string())

    print(f"Sent: {subject} → {to_addr}")


def notify(recipients: list[str], url: str = "https://myerman.art/victoria-brief/") -> None:
    """Send a short 'brief is ready' notification email to a list of recipients."""
    from datetime import datetime
    smtp_host = os.environ["EMAIL_SMTP_HOST"]
    smtp_port = int(os.environ.get("EMAIL_SMTP_PORT", "587"))
    smtp_user = os.environ["EMAIL_SMTP_USER"]
    smtp_pass = os.environ["EMAIL_SMTP_PASSWORD"]
    from_addr = os.environ["EMAIL_FROM"]

    today = datetime.now().strftime("%A, %B %-d")
    subject = f"Victoria Morning Brief — {today}"
    html = f"""<p>Good morning — today's brief is ready:</p>
<p><a href="{url}">{url}</a></p>"""

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = from_addr
    msg["To"] = ", ".join(recipients)
    msg.attach(MIMEText(html, "html", "utf-8"))

    with smtplib.SMTP(smtp_host, smtp_port) as server:
        server.ehlo()
        server.starttls()
        server.ehlo()
        server.login(smtp_user, smtp_pass)
        server.sendmail(from_addr, recipients, msg.as_string())

    print(f"Notified: {', '.join(recipients)}")
