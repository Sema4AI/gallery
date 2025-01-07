"""Actions for sending email.
"""

from sema4ai.actions import action, Secret, Response, ActionError

from dotenv import load_dotenv
import os
from pathlib import Path
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

load_dotenv(Path(__file__).absolute().parent / "devdata" / ".env")

DEFAULT_SMTP_PORT = "587"


@action(is_consequential=False)
def send_email(
    sender: str,
    to: str,
    subject: str,
    body: str,
    smtp_host: Secret,
    smtp_port: Secret,
    smtp_username: Secret,
    smtp_password: Secret,
    cc: str = "",
    bcc: str = "",
) -> Response[str]:
    """Send email to set recipients with subject and body using SMTP server.

    Recipient email addresses ('to', 'cc' and 'bcc') can be separated by commas without any spaces.

    If email is sent successfully please remind the user that recipient may need to
    check their spam folder.

    Args:
        sender: email address of the sender
        to: email address(es) of the recipient(s)
        subject: subject of the email
        body: body of the email
        cc: email address(es) of the recipient(s) to be CC'd
        bcc: email address(es) of the recipient(s) to be BCC'd
        smtp_host: SMTP server host
        smtp_port: SMTP server port, default value is 587
        smtp_username: SMTP server username
        smtp_password: SMTP server password

    Returns:
        Text "Email sent successfully!" or error message if email sending fails
    """
    host = smtp_host.value or os.getenv("SEMA4_SMTP_HOST")
    smtp_port_value = (
        smtp_port.value or os.getenv("SEMA4_SMTP_PORT") or DEFAULT_SMTP_PORT
    )
    username = smtp_username.value or os.getenv("SEMA4_SMTP_USERNAME")
    password = smtp_password.value or os.getenv("SEMA4_SMTP_PASSWORD")

    if not host or not smtp_port_value or not username or not password:
        raise ActionError("SMTP server details are missing.")

    port = int(smtp_port_value)
    # Create list of all recipients (including BCC)
    recipients = to.split(",")

    # Create MIME message
    message = MIMEMultipart()
    message["From"] = sender
    message["To"] = to
    message["Subject"] = subject

    if cc:
        message["CC"] = cc
        recipients += cc.split(",")

    if bcc:
        recipients += bcc.split(",")

    # Attach the email body
    message.attach(MIMEText(body, "plain"))

    try:
        # Create SMTP session
        with smtplib.SMTP(host, port) as server:
            server.starttls()  # Secure the connection
            server.login(username, password)
            text = message.as_string()
            server.sendmail(sender, recipients, text)
    except Exception as e:
        error_message = f"Email send error: {e}"
        print(error_message)
        raise ActionError(error_message)

    return Response(result="Email sent successfully!")
