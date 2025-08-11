import os
import smtplib
from email import encoders
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText


class EmailManager:
    """Handles email operations"""

    @staticmethod
    def send_email(
        to_email: str, subject: str, body: str, attachment_path: str = None
    ) -> str:
        """Send email with optional attachment"""
        try:
            smtp_server = os.getenv("SMTP_SERVER", "smtp.gmail.com")
            smtp_port = int(os.getenv("SMTP_PORT", "587"))
            email_user = os.getenv("EMAIL_USER")
            email_password = os.getenv("EMAIL_PASSWORD")

            if not email_user or not email_password:
                return "Error: EMAIL_USER and EMAIL_PASSWORD environment variables required"

            msg = MIMEMultipart()
            msg["From"] = email_user
            msg["To"] = to_email
            msg["Subject"] = subject

            msg.attach(MIMEText(body, "plain"))

            if attachment_path and os.path.exists(attachment_path):
                with open(attachment_path, "rb") as attachment:
                    part = MIMEBase("application", "octet-stream")
                    part.set_payload(attachment.read())

                encoders.encode_base64(part)
                part.add_header(
                    "Content-Disposition",
                    f"attachment; filename= {os.path.basename(attachment_path)}",
                )
                msg.attach(part)

            server = smtplib.SMTP(smtp_server, smtp_port)
            server.starttls()
            server.login(email_user, email_password)
            server.sendmail(email_user, to_email, msg.as_string())
            server.quit()

            return f"Email sent successfully to {to_email}"

        except Exception as e:
            return f"Error sending email: {str(e)}"
