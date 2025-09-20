import os
import smtplib
from email import encoders
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import List, Optional

from langchain.tools import StructuredTool

from system_agent.config import (
    EMAIL_DEFAULT_SENDER,
    EMAIL_PASSWORD,
    EMAIL_TIMEOUT,
    EMAIL_USE_SSL,
    EMAIL_USE_TLS,
    SMTP_PORT,
    SMTP_SERVER,
)


class EmailManager:
    """Handles email operations"""

    @staticmethod
    def send_email(
        to_email: str,
        subject: str,
        body: str,
        attachment_path: Optional[str] = None,
    ) -> str:
        """Send an email with optional attachment.

        Args:
            to_email: Recipient email address or comma-separated list of addresses
            subject: Email subject
            body: Email body content (plain text or HTML)
            attachment_path: Optional path to file attachment

        Returns:
            str: Success message or error details
        """
        try:
            # Validate email configuration
            if not all([SMTP_SERVER, SMTP_PORT, EMAIL_DEFAULT_SENDER, EMAIL_PASSWORD]):
                return "Error: Email configuration is incomplete. Please check your settings."

            # Validate recipient
            if not to_email or not isinstance(to_email, str):
                return "Error: Invalid recipient email address"

            # Create message
            msg = MIMEMultipart()
            msg["From"] = EMAIL_DEFAULT_SENDER
            msg["To"] = to_email
            msg["Subject"] = subject or "(No subject)"

            # Detect if body is HTML
            is_html = "<html>" in body.lower() or "<p>" in body.lower()

            # Add body to email with appropriate content type
            msg.attach(MIMEText(body, "html" if is_html else "plain"))

            # Add attachment if provided
            if attachment_path:
                if not os.path.exists(attachment_path):
                    return f"Error: Attachment file not found: {attachment_path}"

                try:
                    with open(attachment_path, "rb") as attachment:
                        part = MIMEBase("application", "octet-stream")
                        part.set_payload(attachment.read())

                    encoders.encode_base64(part)
                    filename = os.path.basename(attachment_path)
                    part.add_header(
                        "Content-Disposition",
                        f"attachment; filename={filename}",
                    )
                    msg.attach(part)
                except Exception as e:
                    return f"Error processing attachment: {str(e)}"

            # Connect to server and send email with timeout
            try:
                if EMAIL_USE_SSL:
                    server = smtplib.SMTP_SSL(
                        SMTP_SERVER,
                        int(SMTP_PORT),
                        timeout=EMAIL_TIMEOUT,
                    )
                else:
                    server = smtplib.SMTP(
                        SMTP_SERVER,
                        int(SMTP_PORT),
                        timeout=EMAIL_TIMEOUT,
                    )
                    if EMAIL_USE_TLS:
                        server.starttls()

                # Set timeout for login and send operations
                server.login(EMAIL_DEFAULT_SENDER, EMAIL_PASSWORD)
                server.send_message(msg)
                server.quit()

                recipients = ", ".join(to_email.split(","))
                return f"Email sent successfully to: {recipients}"

            except smtplib.SMTPException as e:
                return f"SMTP error: {str(e)}"
            except Exception as e:
                return f"Error sending email: {str(e)}"

        except Exception as e:
            return f"Unexpected error: {str(e)}"

    def get_tools(self) -> List[StructuredTool]:
        """Return a list of StructuredTool objects for email operations."""
        return [
            StructuredTool.from_function(
                name="send_email",
                func=self.send_email,
                args_schema={
                    "to_email": {
                        "type": "string",
                        "description": "Recipient email address(es), comma-separated for multiple",
                    },
                    "subject": {"type": "string", "description": "Email subject"},
                    "body": {
                        "type": "string",
                        "description": "Email body (supports HTML or plain text)",
                    },
                    "attachment_path": {
                        "type": "string",
                        "description": "Optional path to file attachment",
                    },
                },
                description="""Send an email with optional attachment.
                Example:
                {
                    "to_email": "user@example.com",
                    "subject": "Important Update",
                    "body": "Hello, this is a test email.",
                    "attachment_path": "/path/to/file.pdf"
                }
                Features:
                - Supports multiple recipients (comma-separated)
                - Auto-detects HTML content
                - Handles file attachments
                - Secure connection (TLS/SSL)
                Note: Email server configuration (SMTP settings, credentials) should be set in environment variables.
                Required parameters:
                - to_email: Recipient's email address
                - subject: Email subject
                - body: Email message content
                Optional parameters:
                - attachment_path: Path to file to attach""",  # noqa
            )
        ]
