import base64
import json
from email import encoders
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Any, Dict, List

from googleapiclient.discovery import build
from langchain.tools import Tool


class GmailManager:
    """Handles Gmail operations"""

    def __init__(self, credentials):
        self.credentials = credentials
        self.service = build("gmail", "v1", credentials=credentials)

    def send_email(
        self,
        to_emails: List[str],
        subject: str,
        body: str,
        cc_emails: List[str] = None,
        bcc_emails: List[str] = None,
        is_html: bool = False,
    ) -> str:
        """Send email to multiple recipients"""
        try:
            message = MIMEMultipart()
            message["to"] = ", ".join(to_emails)
            message["subject"] = subject

            if cc_emails:
                message["cc"] = ", ".join(cc_emails)
            if bcc_emails:
                message["bcc"] = ", ".join(bcc_emails)

            content_type = "html" if is_html else "plain"
            message.attach(MIMEText(body, content_type))

            raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode()

            result = (
                self.service.users()
                .messages()
                .send(userId="me", body={"raw": raw_message})
                .execute()
            )

            return f"Email sent successfully. Message ID: {result.get('id')}"

        except Exception as e:
            return f"Error sending email: {str(e)}"

    def send_email_with_attachment(
        self,
        to_emails: List[str],
        subject: str,
        body: str,
        file_path: str,
        cc_emails: List[str] = None,
    ) -> str:
        """Send email with attachment to multiple recipients"""
        try:
            message = MIMEMultipart()
            message["to"] = ", ".join(to_emails)
            message["subject"] = subject

            if cc_emails:
                message["cc"] = ", ".join(cc_emails)

            message.attach(MIMEText(body, "plain"))

            # Add attachment
            with open(file_path, "rb") as attachment:
                part = MIMEBase("application", "octet-stream")
                part.set_payload(attachment.read())

            encoders.encode_base64(part)
            part.add_header(
                "Content-Disposition",
                f'attachment; filename= {file_path.split("/")[-1]}',
            )
            message.attach(part)

            raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode()

            result = (
                self.service.users()
                .messages()
                .send(userId="me", body={"raw": raw_message})
                .execute()
            )

            return f"Email with attachment sent successfully. Message ID: {result.get('id')}"

        except Exception as e:
            return f"Error sending email with attachment: {str(e)}"

    def read_emails(self, query: str = "", max_results: int = 10) -> Dict[str, Any]:
        """Read emails with optional search query"""
        try:
            results = (
                self.service.users()
                .messages()
                .list(userId="me", q=query, maxResults=max_results)
                .execute()
            )

            messages = results.get("messages", [])
            emails = []

            for msg in messages:
                message = (
                    self.service.users()
                    .messages()
                    .get(userId="me", id=msg["id"])
                    .execute()
                )

                payload = message["payload"]
                headers = payload.get("headers", [])

                email_data = {"id": message["id"], "snippet": message["snippet"]}

                for header in headers:
                    if header["name"] in ["From", "To", "Subject", "Date"]:
                        email_data[header["name"].lower()] = header["value"]

                emails.append(email_data)

            return {"success": True, "emails": emails, "total_found": len(emails)}

        except Exception as e:
            return {
                "success": False,
                "error": f"Error reading emails: {str(e)}",
                "emails": [],
            }

    def download_attachment(
        self, message_id: str, attachment_id: str, file_name: str
    ) -> str:
        """Download email attachment"""
        try:
            attachment = (
                self.service.users()
                .messages()
                .attachments()
                .get(userId="me", messageId=message_id, id=attachment_id)
                .execute()
            )

            data = attachment["data"]
            file_data = base64.urlsafe_b64decode(data.encode("UTF-8"))

            with open(file_name, "wb") as f:
                f.write(file_data)

            return f"Attachment downloaded successfully as {file_name}"

        except Exception as e:
            return f"Error downloading attachment: {str(e)}"

    def _send_email_wrapper(self, input_str: str) -> str:
        """
        Wrapper for send_email function to work as an AI agent tool.

        Input format: 'to_emails|||subject|||body|||options_json'
        - to_emails: Comma-separated list of recipient emails (required)
        - subject: Email subject (required)
        - body: Email body content (required)
        - options_json: JSON string with optional parameters (optional)

        Options JSON can contain:
        - cc_emails: List of CC emails (default: [])
        - bcc_emails: List of BCC emails (default: [])
        - is_html: Boolean for HTML content (default: false)

        Examples:
        - "user@example.com|||Test Subject|||Hello World"
        - "user1@example.com,user2@example.com|||Meeting|||Please join|||{\"cc_emails\": [\"manager@example.com\"]}"
        - "team@example.com|||Report|||<h1>Report</h1>|||{\"is_html\": true}"
        """  # noqa
        try:
            parts = input_str.split("|||")
            if len(parts) < 3:
                return "Error: Input format should be 'to_emails|||subject|||body|||options_json'"

            to_emails = [email.strip() for email in parts[0].split(",")]
            subject = parts[1]
            body = parts[2]

            # Default options
            options = {"cc_emails": [], "bcc_emails": [], "is_html": False}

            # Parse options if provided
            if len(parts) > 3 and parts[3].strip():
                try:
                    user_options = json.loads(parts[3])
                    options.update(user_options)
                except json.JSONDecodeError:
                    return f"Error: Invalid JSON in options: {parts[3]}"

            return self.send_email(
                to_emails=to_emails,
                subject=subject,
                body=body,
                cc_emails=options["cc_emails"],
                bcc_emails=options["bcc_emails"],
                is_html=options["is_html"],
            )

        except Exception as e:
            return f"Error parsing input: {str(e)}"

    def _send_email_with_attachment_wrapper(self, input_str: str) -> str:
        """
        Wrapper for send_email_with_attachment function.

        Input format: 'to_emails|||subject|||body|||file_path|||options_json'
        - to_emails: Comma-separated list of recipient emails (required)
        - subject: Email subject (required)
        - body: Email body content (required)
        - file_path: Path to attachment file (required)
        - options_json: JSON string with optional parameters (optional)

        Options JSON can contain:
        - cc_emails: List of CC emails (default: [])

        Example:
        - "user@example.com|||Report|||Please find attached|||/path/to/file.pdf"
        """
        try:
            parts = input_str.split("|||")
            if len(parts) < 4:
                return "Error: Input format should be 'to_emails|||subject|||body|||file_path|||options_json'"  # noqa

            to_emails = [email.strip() for email in parts[0].split(",")]
            subject = parts[1]
            body = parts[2]
            file_path = parts[3]

            options = {"cc_emails": []}

            if len(parts) > 4 and parts[4].strip():
                try:
                    user_options = json.loads(parts[4])
                    options.update(user_options)
                except json.JSONDecodeError:
                    return f"Error: Invalid JSON in options: {parts[4]}"

            return self.send_email_with_attachment(
                to_emails=to_emails,
                subject=subject,
                body=body,
                file_path=file_path,
                cc_emails=options["cc_emails"],
            )

        except Exception as e:
            return f"Error parsing input: {str(e)}"

    def _read_emails_wrapper(self, input_str: str) -> str:
        """
        Wrapper for read_emails function.

        Input format: 'query|||options_json'
        - query: Gmail search query (optional, defaults to empty)
        - options_json: JSON string with optional parameters (optional)

        Options JSON can contain:
        - max_results: Maximum number of emails to return (default: 10)

        Examples:
        - ""  (read recent emails)
        - "from:user@example.com"
        - "subject:meeting|||{\"max_results\": 20}"
        """
        try:
            if "|||" in input_str:
                parts = input_str.split("|||", 1)
                query = parts[0]
                options_json = parts[1] if len(parts) > 1 else "{}"
            else:
                query = input_str
                options_json = "{}"

            options = {"max_results": 10}

            if options_json.strip():
                try:
                    user_options = json.loads(options_json)
                    options.update(user_options)
                except json.JSONDecodeError:
                    return f"Error: Invalid JSON in options: {options_json}"

            result = self.read_emails(query=query, max_results=options["max_results"])
            return json.dumps(result, indent=2)

        except Exception as e:
            return f"Error parsing input: {str(e)}"

    def _download_attachment_wrapper(self, input_str: str) -> str:
        """
        Wrapper for download_attachment function.

        Input format: 'message_id|||attachment_id|||file_name'
        - message_id: Gmail message ID (required)
        - attachment_id: Attachment ID (required)
        - file_name: Local file name to save as (required)

        Example:
        - "msg123|||att456|||document.pdf"
        """
        try:
            parts = input_str.split("|||")
            if len(parts) != 3:
                return "Error: Input format should be 'message_id|||attachment_id|||file_name'"

            message_id, attachment_id, file_name = parts

            return self.download_attachment(
                message_id=message_id, attachment_id=attachment_id, file_name=file_name
            )

        except Exception as e:
            return f"Error parsing input: {str(e)}"

    def get_tools(self):
        tools = [
            Tool(
                name="send_email",
                description='Send email. JSON: {"to_emails": ["str"], "subject": "str", "body": "str", "cc_emails": ["str"], "bcc_emails": ["str"], "is_html": true/false}',
                func=lambda params: self.send_email(**(params if isinstance(params, dict) else __import__("json").loads(params))),
            ),
            Tool(
                name="send_email_with_attachment",
                description='Send email with attachment. JSON: {"to_emails": ["str"], "subject": "str", "body": "str", "file_path": "str", "cc_emails": ["str"]}',
                func=lambda params: self.send_email_with_attachment(**(params if isinstance(params, dict) else __import__("json").loads(params))),
            ),
            Tool(
                name="read_emails",
                description='Read and search emails. JSON: {"query": "str", "max_results": int, "label_ids": ["str"]}',
                func=lambda params: self.read_emails(**(params if isinstance(params, dict) else __import__("json").loads(params))),
            ),
            Tool(
                name="download_attachment",
                description='Download email attachment. JSON: {"message_id": "str", "attachment_id": "str", "file_name": "str"}',
                func=lambda params: self.download_attachment(**(params if isinstance(params, dict) else __import__("json").loads(params))),
            ),
        ]
        return tools

    def get_tools_wrappers(self):
        tools = [
            Tool(
                name="send_email",
                description="Send email to multiple recipients. Format: 'to_emails|||subject|||body|||options_json'",  # noqa
                func=self._send_email_wrapper,
            ),
            Tool(
                name="send_email_with_attachment",
                description="Send email with attachment. Format: 'to_emails|||subject|||body|||file_path|||options_json'",  # noqa
                func=self._send_email_with_attachment_wrapper,
            ),
            Tool(
                name="read_emails",
                description="Read and search emails. Format: 'query|||options_json'",
                func=self._read_emails_wrapper,
            ),
            Tool(
                name="download_attachment",
                description="Download email attachment. Format: 'message_id|||attachment_id|||file_name'",  # noqa
                func=self._download_attachment_wrapper,
            ),
        ]
        return tools
