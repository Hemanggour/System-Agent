import re
from typing import Any, Dict, List, Optional, Tuple

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from langchain.tools import Tool

# optional: nicer markdown parser; if not present we'll still work (no formatting)
try:
    from markdown_it import MarkdownIt
except Exception:
    MarkdownIt = None


class DocumentsManager:
    """
    Robust Google Docs helper for LangChain Tools.
    - edit_document supports markdown=True to parse markdown -> real formatting.
    - edit_document supports append=True to append, otherwise it replaces the document safely.
    """

    MAX_BATCH_REQUESTS = 100  # fallback chunk size if single batch fails

    def __init__(self, credentials):
        self.credentials = credentials
        self.service = build("docs", "v1", credentials=credentials)
        self.drive_service = build("drive", "v3", credentials=credentials)

    # -------------------------
    # High level operations
    # -------------------------
    def create_document(self, title: str) -> Dict[str, Any]:
        doc = self.service.documents().create(body={"title": title}).execute()
        doc_id = doc.get("documentId")
        return {"document_id": doc_id, "title": title}

    def read_document(self, document_id: Optional[str] = None, document_name: Optional[str] = None) -> Dict[str, Any]:
        if not document_id and not document_name:
            raise ValueError("Provide either document_id or document_name")

        if not document_id:
            document_id = self._find_document_id(document_name)

        doc = self.service.documents().get(documentId=document_id).execute()
        text = self._extract_text_from_document(doc)
        return {"document_id": document_id, "content": text}

    def edit_document(
            self,
            document_id: str,
            content: str,
            append: bool = False,
            markdown: bool = False,
        ) -> Dict[str, Any]:
        """
        Replace or append content to a Google Doc safely.

        Edge-case safe rules implemented:
        - Always fetch document first to compute safe indices.
        - Only issue deleteContentRange when start < end (non-empty and excluding trailing newline).
        - Compute insertion index from current plain-text length.
        - Apply all formatting requests after computing absolute indexes.
        - Catch HttpErrors and return helpful messages.
        """
        try:
            doc = self.service.documents().get(documentId=document_id).execute()
        except HttpError as e:
            raise RuntimeError(f"Failed to fetch document: {e}")

        # Parse markdown if requested
        if markdown:
            plain_text, style_ranges = self._parse_markdown_to_plain_and_styles(content)
        else:
            plain_text = content
            style_ranges = []

        # Compute current plain text length
        existing_text = self._extract_text_from_document(doc)
        existing_len = len(existing_text)

        # Determine insertion index
        insertion_index = 1 + existing_len if append else 1

        requests: List[Dict[str, Any]] = []

        # Safe deletion when replacing (not appending)
        if not append:
            body = doc.get("body", {}).get("content", [])
            last_end_index = body[-1].get("endIndex", 1) if body else 1

            # Only delete if there’s content beyond first sentinel and exclude the trailing newline
            delete_start = 1
            delete_end = max(1, last_end_index - 1)
            if delete_end > delete_start:
                requests.append({
                    "deleteContentRange": {"range": {"startIndex": delete_start, "endIndex": delete_end}}
                })

        # Insert new text
        if plain_text:
            requests.append({"insertText": {"location": {"index": insertion_index}, "text": plain_text}})

        # Apply styles from Markdown
        for r in style_ranges:
            start0, end0, style = r["start"], r["end"], r["style"]
            if end0 <= start0:
                continue  # skip empty ranges
            start_index = insertion_index + start0
            end_index = insertion_index + end0
            text_style = {}
            if style.get("bold"):
                text_style["bold"] = True
            if style.get("italic"):
                text_style["italic"] = True
            if "fontSize" in style:
                text_style["fontSize"] = {"magnitude": style["fontSize"], "unit": "PT"}
            if style.get("code"):
                text_style["weightedFontFamily"] = {"fontFamily": "Courier New"}

            if not text_style:
                continue

            fields = ",".join(text_style.keys())
            requests.append({
                "updateTextStyle": {
                    "range": {"startIndex": start_index, "endIndex": end_index},
                    "textStyle": text_style,
                    "fields": fields,
                }
            })

        if not requests:
            return {"document_id": document_id, "status": "no_changes"}

        # Execute batchUpdate safely
        try:
            result = self.service.documents().batchUpdate(documentId=document_id, body={"requests": requests}).execute()
        except HttpError as e:
            msg = str(e)
            # Optional: chunk large requests
            if "Request too large" in msg or "exceeds" in msg or "Request had too many" in msg:
                try:
                    for i in range(0, len(requests), self.MAX_BATCH_REQUESTS):
                        chunk = requests[i:i + self.MAX_BATCH_REQUESTS]
                        self.service.documents().batchUpdate(documentId=document_id, body={"requests": chunk}).execute()
                    result = {"status": "ok_chunked"}
                except HttpError as e2:
                    raise RuntimeError(f"Batch update failed when chunking: {e2}")
            else:
                raise RuntimeError(f"Batch update failed: {e}")

        return {"document_id": document_id, "status": "updated"}


    # -------------------------
    # Helpers & parsers
    # -------------------------
    def format_text(self, document_id: str, text: str, **styles) -> Dict[str, Any]:
        """
        Apply styles by explicit offsets: user can call this if they know start/end indexes.
        Example: format_text(doc_id, text="Hello", bold=True) -> finds first occurrence and applies style safely.
        """
        # find text position in the document
        doc = self.service.documents().get(documentId=document_id).execute()
        whole = self._extract_text_from_document(doc)
        start0 = whole.find(text)
        if start0 == -1:
            raise ValueError("Text not found in document")
        end0 = start0 + len(text)
        start_index = 1 + start0
        end_index = 1 + end0
        text_style = {}
        if styles.get("bold"):
            text_style["bold"] = True
        if styles.get("italic"):
            text_style["italic"] = True
        if "font_size" in styles:
            text_style["fontSize"] = {"magnitude": int(styles["font_size"]), "unit": "PT"}

        if not text_style:
            return {"document_id": document_id, "status": "nothing_to_apply"}

        fields = ",".join(text_style.keys())
        req = {
            "updateTextStyle": {
                "range": {"startIndex": start_index, "endIndex": end_index},
                "textStyle": text_style,
                "fields": fields,
            }
        }
        self.service.documents().batchUpdate(documentId=document_id, body={"requests": [req]}).execute()
        return {"document_id": document_id, "status": "formatted"}

    def _find_document_id(self, document_name: str) -> str:
        resp = self.drive_service.files().list(
            q=f"name='{document_name}' and mimeType='application/vnd.google-apps.document'",
            fields="files(id, name)",
            pageSize=5,
        ).execute()
        files = resp.get("files", [])
        if not files:
            raise ValueError(f"Document named '{document_name}' not found.")
        # return the first match
        return files[0]["id"]

    def _insert_text(self, document_id: str, text: str):
        """Simple insertion at the front (legacy helper). Use edit_document for robust behavior."""
        if not text:
            return
        requests = [{"insertText": {"location": {"index": 1}, "text": text}}]
        self.service.documents().batchUpdate(documentId=document_id, body={"requests": requests}).execute()

    def _extract_text_from_document(self, document: Dict[str, Any]) -> str:
        """Extract plain text from the Google Docs document structure (best-effort)."""
        text = ""
        for structural in document.get("body", {}).get("content", []):
            para = structural.get("paragraph")
            if not para:
                # might be table or other type; skip or handle table cells if needed
                continue
            for elem in para.get("elements", []):
                tr = elem.get("textRun")
                if tr:
                    text += tr.get("content", "")
        return text

    # -------------------------
    # Markdown parsing
    # -------------------------
    def _parse_markdown_to_plain_and_styles(self, markdown_text: str) -> Tuple[str, List[Dict[str, Any]]]:
        """
        Parse Markdown -> returns (plain_text, style_ranges)
        style_ranges is a list of dicts: {"start": int, "end": int, "style": {"bold": True, "italic": True, "fontSize": 18, "code": True}}
        Offsets are 0-based relative to the returned plain_text.
        Requires markdown-it-py for best results. If not installed, returns plain text with no styles.
        """
        if not MarkdownIt:
            # fallback: strip markdown markers (basic) and return plain text without ranges
            stripped = re.sub(r"\*\*(.*?)\*\*", r"\1", markdown_text)
            stripped = re.sub(r"\*(.*?)\*", r"\1", stripped)
            stripped = re.sub(r"`(.*?)`", r"\1", stripped)
            # headings -> remove leading #'s
            stripped = re.sub(r"^#{1,6}\s+", "", stripped, flags=re.MULTILINE)
            return stripped, []

        md = MarkdownIt()
        tokens = md.parse(markdown_text)

        plain = []
        pos = 0  # 0-based offset into plain
        ranges: List[Dict[str, Any]] = []
        style_stack: List[Dict[str, Any]] = []

        def push_style(kind: str, extra: Optional[Any] = None):
            style_stack.append({"kind": kind, "extra": extra})

        def pop_style(kind: str):
            # pop the last matching kind
            for i in range(len(style_stack) - 1, -1, -1):
                if style_stack[i]["kind"] == kind:
                    style_stack.pop(i)
                    return

        def current_style_snapshot() -> Dict[str, Any]:
            s = {}
            for entry in style_stack:
                if entry["kind"] == "strong":
                    s["bold"] = True
                if entry["kind"] == "em":
                    s["italic"] = True
                if entry["kind"].startswith("heading_"):
                    # heading => larger font
                    level = int(entry["kind"].split("_", 1)[1])
                    # simple mapping: h1 -> 24pt, h2 -> 20pt, h3 -> 18pt ...
                    size = max(12, 26 - (level - 1) * 4)
                    s["fontSize"] = size
                    s["bold"] = True
                if entry["kind"] == "code":
                    s["code"] = True
            return s

        def handle_text_chunk(chunk: str):
            nonlocal pos
            if not chunk:
                return
            start = pos
            plain.append(chunk)
            pos += len(chunk)
            style_snapshot = current_style_snapshot()
            if style_snapshot:
                ranges.append({"start": start, "end": pos, "style": style_snapshot})

        # tokens walker. markdown-it produces nested inline tokens, handle them.
        def walk_tokens(toks):
            for token in toks:
                ttype = token.type
                if ttype == "paragraph_open":
                    # nothing to do
                    pass
                elif ttype == "paragraph_close":
                    handle_text_chunk("\n")
                elif ttype == "softbreak":
                    handle_text_chunk("\n")
                elif ttype == "hardbreak":
                    handle_text_chunk("\n")
                elif ttype in ("heading_open",):
                    # token.tag like 'h1'
                    tag = token.tag or ""
                    if tag.startswith("h"):
                        level = int(tag[1:])
                        push_style(f"heading_{level}")
                elif ttype in ("heading_close",):
                    tag = token.tag or ""
                    if tag.startswith("h"):
                        pop_style(f"heading_{int(tag[1:])}")
                        handle_text_chunk("\n")
                elif ttype in ("strong_open",):
                    push_style("strong")
                elif ttype in ("strong_close",):
                    pop_style("strong")
                elif ttype in ("em_open",):
                    push_style("em")
                elif ttype in ("em_close",):
                    pop_style("em")
                elif ttype in ("code_inline",):
                    push_style("code")
                    handle_text_chunk(token.content)
                    pop_style("code")
                elif ttype == "fence":  # code fence -> treat as block
                    # insert as-is and mark monospace (we'll mark entire block as code style)
                    start_pos = pos
                    content = token.content + "\n"
                    plain.append(content)
                    pos += len(content)
                    ranges.append({"start": start_pos, "end": pos, "style": {"code": True}})
                elif ttype == "inline":
                    # dive into children
                    if token.children:
                        walk_tokens(token.children)
                elif ttype == "text":
                    handle_text_chunk(token.content)
                else:
                    # fallback: if token has children, walk them
                    if getattr(token, "children", None):
                        walk_tokens(token.children)

        walk_tokens(tokens)
        return ("".join(plain), ranges)

    # -------------------------
    # LangChain Tools exporter
    # -------------------------
    def get_tools(self) -> List[Tool]:
        return [
            Tool(
                name="create_google_doc",
                description='Create a new Google Doc. JSON input: {"title":"str"}',
                func=lambda params: self.create_document(**(params if isinstance(params, dict) else __import__("json").loads(params))),
            ),
            Tool(
                name="read_google_doc",
                description='Read Google Doc. JSON input: {"document_id":"str"} or {"document_name":"str"}',
                func=lambda params: self.read_document(**(params if isinstance(params, dict) else __import__("json").loads(params))),
            ),
            Tool(
                name="edit_google_doc",
                description='Edit Google Doc. JSON: {"document_id":"str","content":"str","append":true/false,"markdown":true/false}',
                func=lambda params: self.edit_document(**(params if isinstance(params, dict) else __import__("json").loads(params))),
            ),
            Tool(
                name="format_google_doc_text",
                description='Format text by literal search. JSON: {"document_id":"str","text":"str","bold":true/false,"italic":true/false,"font_size":int}',
                func=lambda params: self.format_text(**(params if isinstance(params, dict) else __import__("json").loads(params))),
            ),
        ]
