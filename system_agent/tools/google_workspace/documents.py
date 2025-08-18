import json
from typing import Any, Dict

from googleapiclient.discovery import build
from langchain.tools import Tool


class DocumentsManager:
    """Handles Google Docs operations"""

    def __init__(self, credentials):
        self.credentials = credentials
        self.service = build("docs", "v1", credentials=credentials)
        self.drive_service = build("drive", "v3", credentials=credentials)

    def create_document(self, title: str, content: str = "") -> Dict[str, Any]:
        """Create a new Google Doc"""
        try:
            document = {"title": title}

            doc = self.service.documents().create(body=document).execute()
            doc_id = doc.get("documentId")

            if content:
                self._insert_text(doc_id, content)

            return {
                "success": True,
                "document_id": doc_id,
                "document_url": f"https://docs.google.com/document/d/{doc_id}/edit",
                "message": f"Document '{title}' created successfully",
            }

        except Exception as e:
            return {"success": False, "error": f"Error creating document: {str(e)}"}

    def read_document(
        self, document_id: str = None, document_name: str = None
    ) -> Dict[str, Any]:
        """Read content from Google Doc by ID or name"""
        try:
            if document_name and not document_id:
                document_id = self._find_document_id(document_name)
                if not document_id:
                    return {
                        "success": False,
                        "error": f"Document '{document_name}' not found",
                    }

            document = self.service.documents().get(documentId=document_id).execute()
            content = self._extract_text_from_document(document)

            return {
                "success": True,
                "document_id": document_id,
                "title": document.get("title"),
                "content": content,
            }

        except Exception as e:
            return {"success": False, "error": f"Error reading document: {str(e)}"}

    def edit_document(
        self, document_id: str, new_content: str, append: bool = False
    ) -> str:
        """Edit document content (replace or append)"""
        try:
            if not append:
                # Clear existing content first
                document = (
                    self.service.documents().get(documentId=document_id).execute()
                )
                body_content = document.get("body", {}).get("content", [])

                if len(body_content) > 2:
                    last_index = body_content[-1]["endIndex"]
                    requests = [
                        {
                            "deleteContentRange": {
                                "range": {
                                    "startIndex": 1,
                                    "endIndex": last_index - 1,  # keep the last newline
                                }
                            }
                        }
                    ]
                    self.service.documents().batchUpdate(
                        documentId=document_id, body={"requests": requests}
                    ).execute()

            # Insert new content
            self._insert_text(document_id, new_content)

            action = "appended to" if append else "updated"
            return f"Document {action} successfully"

        except Exception as e:
            return f"Error editing document: {str(e)}"

    def format_text(
        self,
        document_id: str,
        start_index: int,
        end_index: int,
        bold: bool = None,
        italic: bool = None,
        font_size: int = None,
    ) -> str:
        """Apply formatting to specific text range"""
        try:
            requests = []

            text_style = {}
            if bold is not None:
                text_style["bold"] = bold
            if italic is not None:
                text_style["italic"] = italic
            if font_size is not None:
                text_style["fontSize"] = {"magnitude": font_size, "unit": "PT"}

            if text_style:
                requests.append(
                    {
                        "updateTextStyle": {
                            "range": {"startIndex": start_index, "endIndex": end_index},
                            "textStyle": text_style,
                            "fields": ",".join(text_style.keys()),
                        }
                    }
                )

            if requests:
                self.service.documents().batchUpdate(
                    documentId=document_id, body={"requests": requests}
                ).execute()

                return "Text formatting applied successfully"
            else:
                return "No formatting changes specified"

        except Exception as e:
            return f"Error formatting text: {str(e)}"

    def _find_document_id(self, document_name: str) -> str:
        """Find document ID by name"""
        try:
            results = (
                self.drive_service.files()
                .list(
                    q=f"name='{document_name}' and mimeType='application/vnd.google-apps.document'",
                    fields="files(id, name)",
                )
                .execute()
            )

            files = results.get("files", [])
            return files[0]["id"] if files else None

        except Exception:
            return None

    def _insert_text(self, document_id: str, text: str):
        """Helper method to insert text at the end of document"""
        requests = [{"insertText": {"location": {"index": 1}, "text": text}}]

        self.service.documents().batchUpdate(
            documentId=document_id, body={"requests": requests}
        ).execute()

    def _extract_text_from_document(self, document: Dict) -> str:
        """Extract plain text from document structure"""
        content = ""

        for element in document.get("body", {}).get("content", []):
            if "paragraph" in element:
                for text_element in element["paragraph"].get("elements", []):
                    if "textRun" in text_element:
                        content += text_element["textRun"].get("content", "")

        return content

    def _create_document_wrapper(self, input_str: str) -> str:
        """
        Wrapper for create_document function.

        Input format: 'title|||content'
        - title: Document title (required)
        - content: Initial document content (optional)

        Examples:
        - "My Document"
        - "Meeting Notes|||Today's meeting agenda: 1. Review..."
        """
        try:
            if "|||" in input_str:
                parts = input_str.split("|||", 1)
                title = parts[0]
                content = parts[1] if len(parts) > 1 else ""
            else:
                title = input_str
                content = ""

            result = self.create_document(title=title, content=content)
            return json.dumps(result, indent=2)

        except Exception as e:
            return f"Error parsing input: {str(e)}"

    def _read_document_wrapper(self, input_str: str) -> str:
        """
        Wrapper for read_document function.

        Input format: 'document_id_or_name'
        - document_id_or_name: Document ID or document name (required)

        Examples:
        - "1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms"
        - "My Document"
        """
        try:
            identifier = input_str.strip()

            # Check if it looks like a document ID (long alphanumeric string)
            if (
                len(identifier) > 30
                and identifier.replace("_", "").replace("-", "").isalnum()
            ):
                result = self.read_document(document_id=identifier)
            else:
                result = self.read_document(document_name=identifier)

            return json.dumps(result, indent=2)

        except Exception as e:
            return f"Error parsing input: {str(e)}"

    def _edit_document_wrapper(self, input_str: str) -> str:
        """
        Wrapper for edit_document function.

        Input format: 'document_id|||new_content|||options_json'
        - document_id: Document ID (required)
        - new_content: New content to add/replace (required)
        - options_json: JSON string with optional parameters (optional)

        Options JSON can contain:
        - append: Boolean to append instead of replace (default: false)

        Examples:
        - "doc123|||New content here"
        - "doc123|||Additional content|||{\"append\": true}"
        """
        try:
            parts = input_str.split("|||")
            if len(parts) < 2:
                return "Error: Input format should be 'document_id|||new_content|||options_json'"

            document_id = parts[0]
            new_content = parts[1]

            options = {"append": False}

            if len(parts) > 2 and parts[2].strip():
                try:
                    user_options = json.loads(parts[2])
                    options.update(user_options)
                except json.JSONDecodeError:
                    return f"Error: Invalid JSON in options: {parts[2]}"

            return self.edit_document(
                document_id=document_id,
                new_content=new_content,
                append=options["append"],
            )

        except Exception as e:
            return f"Error parsing input: {str(e)}"

    def _format_text_wrapper(self, input_str: str) -> str:
        """
        Wrapper for format_text function.

        Input format: 'document_id|||start_index|||end_index|||options_json'
        - document_id: Document ID (required)
        - start_index: Start character index (required)
        - end_index: End character index (required)
        - options_json: JSON string with formatting options (optional)

        Options JSON can contain:
        - bold: Boolean for bold formatting
        - italic: Boolean for italic formatting
        - font_size: Integer for font size in points

        Example:
        - "doc123|||0|||10|||{\"bold\": true, \"font_size\": 14}"
        """
        try:
            parts = input_str.split("|||")
            if len(parts) < 3:
                return "Error: Input format should be 'document_id|||start_index|||end_index|||options_json'"  # noqa

            document_id = parts[0]
            start_index = int(parts[1])
            end_index = int(parts[2])

            options = {}

            if len(parts) > 3 and parts[3].strip():
                try:
                    options = json.loads(parts[3])
                except json.JSONDecodeError:
                    return f"Error: Invalid JSON in options: {parts[3]}"

            return self.format_text(
                document_id=document_id,
                start_index=start_index,
                end_index=end_index,
                bold=options.get("bold"),
                italic=options.get("italic"),
                font_size=options.get("font_size"),
            )

        except Exception as e:
            return f"Error parsing input: {str(e)}"

    def get_tools(self):
        tools = [
            Tool(
                name="create_document",
                description="Create a new Google Doc with optional initial content",
                func=lambda params: self.create_document(**params),
            ),
            Tool(
                name="read_document",
                description="Read content from Google Doc by ID or name",
                func=lambda params: self.read_document(**params),
            ),
            Tool(
                name="edit_document",
                description="Edit document content (replace or append text)",
                func=lambda params: self.edit_document(**params),
            ),
            Tool(
                name="format_document_text",
                description="Apply formatting (bold, italic, font size) to text range",
                func=lambda params: self.format_text(**params),
            ),
        ]
        return tools

    def get_tools_wrappers(self):
        tools = [
            Tool(
                name="create_document",
                description="Create a new Google Doc. Format: 'title|||content'",
                func=self._create_document_wrapper,
            ),
            Tool(
                name="read_document",
                description="Read Google Doc content. Format: 'document_id_or_name'",
                func=self._read_document_wrapper,
            ),
            Tool(
                name="edit_document",
                description="Edit document content. Format: 'document_id|||new_content|||options_json'",  # noqa
                func=self._edit_document_wrapper,
            ),
            Tool(
                name="format_document_text",
                description="Format document text. Format: 'document_id|||start_index|||end_index|||options_json'",  # noqa
                func=self._format_text_wrapper,
            ),
        ]
        return tools
