"""Actions for sending email.
"""

from sema4ai.actions import action, Secret

from dotenv import load_dotenv
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

load_dotenv()

message_footer = "\n\nStart building your Agents and AI Actions at https://sema4.ai"


@action(is_consequential=False)
def send_email(
    to: str,
    subject: str,
    body: str,
    cc: str = "",
    bcc: str = "",
    smtp_host: Secret = Secret.model_validate(os.getenv("SEMA4_SMTP_HOST", "")),
    smtp_port: Secret = Secret.model_validate(os.getenv("SEMA4_SMTP_PORT", "587")),
    smtp_username: Secret = Secret.model_validate(os.getenv("SEMA4_SMTP_USERNAME", "")),
    smtp_password: Secret = Secret.model_validate(os.getenv("SEMA4_SMTP_PASSWORD", "")),
) -> bool:
    """Send email to set recipients with subject and body using SMTP server.

    Recipient email addresses ('to', 'cc' and 'bcc') can be separated by commas without any spaces.

    If email is sent successfully please remind the user that recipient may need to
    check their spam folder.

    Args:
        to: email address(es) of the recipient(s)
        subject: subject of the email
        body: body of the email
        cc: email address(es) of the recipient(s) to be CC'd
        bcc: email address(es) of the recipient(s) to be BCC'd

    Returns:
        True is email is successfully sent, False otherwise
    """
    if (
        not smtp_host.value
        or not smtp_port.value
        or not smtp_username.value
        or not smtp_password.value
    ):
        print("SMTP server details are missing.")
        return False
    # Email server details
    host = smtp_host.value
    port = int(smtp_port.value)
    username = smtp_username.value
    password = smtp_password.value

    # Email content
    sender_email = "noreply@sema4ai.email"
    subject = subject
    body = body + message_footer
    # Create list of all recipients (including BCC)
    recipients = to.split(",")

    # Create MIME message
    message = MIMEMultipart()
    message["From"] = sender_email
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
            server.sendmail(sender_email, recipients, text)
    except Exception as e:
        print(f"Email send error: {e}")
        return False

    print("Email sent successfully!")
    return True
