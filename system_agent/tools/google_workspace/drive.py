import io
import mimetypes
from typing import Any, Dict, List

from googleapiclient.discovery import build
from langchain.tools import Tool


class DriveManager:
    """Handles Google Drive operations"""

    def __init__(self, credentials):
        self.credentials = credentials
        self.service = build("drive", "v3", credentials=credentials)

    def upload_file(
        self, file_path: str, folder_id: str = None, file_name: str = None
    ) -> Dict[str, Any]:
        """Upload file to Google Drive"""
        try:
            if not file_name:
                file_name = file_path.split("/")[-1]

            mime_type, _ = mimetypes.guess_type(file_path)

            file_metadata = {"name": file_name}
            if folder_id:
                file_metadata["parents"] = [folder_id]

            with open(file_path, "rb") as f:
                media = f.read()

            from googleapiclient.http import MediaIoBaseUpload

            media_upload = MediaIoBaseUpload(
                io.BytesIO(media), mimetype=mime_type, resumable=True
            )

            file = (
                self.service.files()
                .create(
                    body=file_metadata,
                    media_body=media_upload,
                    fields="id,name,webViewLink",
                )
                .execute()
            )

            return {
                "success": True,
                "file_id": file.get("id"),
                "file_name": file.get("name"),
                "file_url": file.get("webViewLink"),
                "message": f"File '{file_name}' uploaded successfully",
            }

        except Exception as e:
            return {"success": False, "error": f"Error uploading file: {str(e)}"}

    def download_file(
        self, file_id: str = None, file_name: str = None, local_path: str = None
    ) -> str:
        """Download file from Google Drive by ID or name"""
        try:
            if file_name and not file_id:
                file_id = self._find_file_id(file_name)
                if not file_id:
                    return f"File '{file_name}' not found"

            # Get file metadata
            file_metadata = self.service.files().get(fileId=file_id).execute()
            file_name_actual = file_metadata.get("name")

            if not local_path:
                local_path = file_name_actual

            # Download file
            request = self.service.files().get_media(fileId=file_id)

            with open(local_path, "wb") as f:
                downloader = request.execute()
                f.write(downloader)

            return (
                f"File '{file_name_actual}' downloaded successfully as '{local_path}'"
            )

        except Exception as e:
            return f"Error downloading file: {str(e)}"

    def share_file(
        self, file_id: str, emails: List[str], role: str = "reader", notify: bool = True
    ) -> str:
        """Share file with multiple users"""
        try:
            results = []

            for email in emails:
                permission = {"type": "user", "role": role, "emailAddress": email}

                self.service.permissions().create(
                    fileId=file_id, body=permission, sendNotificationEmail=notify
                ).execute()

                results.append(f"Shared with {email} as {role}")

            return f"File shared successfully. {'; '.join(results)}"

        except Exception as e:
            return f"Error sharing file: {str(e)}"

    def create_folder(
        self, folder_name: str, parent_folder_id: str = None
    ) -> Dict[str, Any]:
        """Create a new folder"""
        try:
            file_metadata = {
                "name": folder_name,
                "mimeType": "application/vnd.google-apps.folder",
            }

            if parent_folder_id:
                file_metadata["parents"] = [parent_folder_id]

            folder = (
                self.service.files()
                .create(body=file_metadata, fields="id,name,webViewLink")
                .execute()
            )

            return {
                "success": True,
                "folder_id": folder.get("id"),
                "folder_name": folder.get("name"),
                "folder_url": folder.get("webViewLink"),
                "message": f"Folder '{folder_name}' created successfully",
            }

        except Exception as e:
            return {"success": False, "error": f"Error creating folder: {str(e)}"}

    def list_files(
        self, folder_id: str = None, file_type: str = None, max_results: int = 10
    ) -> Dict[str, Any]:
        """List files in Drive or specific folder"""
        try:
            query = "trashed=false"

            if folder_id:
                query += f" and '{folder_id}' in parents"

            if file_type:
                mime_types = {
                    "document": "application/vnd.google-apps.document",
                    "spreadsheet": "application/vnd.google-apps.spreadsheet",
                    "presentation": "application/vnd.google-apps.presentation",
                    "folder": "application/vnd.google-apps.folder",
                    "pdf": "application/pdf",
                    "image": "image/",
                }

                if file_type in mime_types:
                    mime_type = mime_types[file_type]
                    if file_type == "image":
                        query += f" and mimeType contains '{mime_type}'"
                    else:
                        query += f" and mimeType='{mime_type}'"

            results = (
                self.service.files()
                .list(
                    q=query,
                    pageSize=max_results,
                    fields="files(id,name,mimeType,modifiedTime,size,webViewLink)",
                )
                .execute()
            )

            files = results.get("files", [])

            return {
                "success": True,
                "files": files,
                "total_found": len(files),
                "message": f"Found {len(files)} files",
            }

        except Exception as e:
            return {
                "success": False,
                "error": f"Error listing files: {str(e)}",
                "files": [],
            }

    def move_file(self, file_id: str, destination_folder_id: str) -> str:
        """Move file to different folder"""
        try:
            # Get current parents
            file_metadata = (
                self.service.files().get(fileId=file_id, fields="parents").execute()
            )

            previous_parents = ",".join(file_metadata.get("parents"))

            # Move file
            file = (
                self.service.files()
                .update(
                    fileId=file_id,
                    addParents=destination_folder_id,
                    removeParents=previous_parents,
                    fields="id,name",
                )
                .execute()
            )

            return f"File '{file.get('name')}' moved successfully"

        except Exception as e:
            return f"Error moving file: {str(e)}"

    def _find_file_id(self, file_name: str) -> str:
        """Find file ID by name"""
        try:
            results = (
                self.service.files()
                .list(
                    q=f"name='{file_name}' and trashed=false", fields="files(id, name)"
                )
                .execute()
            )

            files = results.get("files", [])
            return files[0]["id"] if files else None

        except Exception:
            return None

    # Wrapper methods for DriveManager
    def _upload_file_wrapper(self, input_str: str) -> str:
        """Wrapper for upload_file. Format: 'file_path|||folder_id|||file_name'"""
        try:
            parts = input_str.split("|||")
            file_path = parts[0].strip()
            folder_id = (
                parts[1].strip() if len(parts) > 1 and parts[1].strip() else None
            )
            file_name = (
                parts[2].strip() if len(parts) > 2 and parts[2].strip() else None
            )

            result = self.upload_file(
                file_path=file_path, folder_id=folder_id, file_name=file_name
            )
            return str(result)
        except Exception as e:
            return f"Error uploading file: {str(e)}"

    def _download_file_wrapper(self, input_str: str) -> str:
        """Wrapper for download_file. Format: 'file_id|||file_name|||local_path'"""
        try:
            parts = input_str.split("|||")
            file_id = parts[0].strip() if parts[0].strip() else None
            file_name = (
                parts[1].strip() if len(parts) > 1 and parts[1].strip() else None
            )
            local_path = (
                parts[2].strip() if len(parts) > 2 and parts[2].strip() else None
            )

            result = self.download_file(
                file_id=file_id, file_name=file_name, local_path=local_path
            )
            return result
        except Exception as e:
            return f"Error downloading file: {str(e)}"

    def _share_file_wrapper(self, input_str: str) -> str:
        """Wrapper for share_file. Format: 'file_id|||emails_json|||role|||notify'"""
        try:
            import json

            parts = input_str.split("|||")
            file_id = parts[0].strip()
            emails = json.loads(parts[1].strip()) if len(parts) > 1 else []
            role = parts[2].strip() if len(parts) > 2 and parts[2].strip() else "reader"
            notify = parts[3].strip().lower() == "true" if len(parts) > 3 else True

            result = self.share_file(
                file_id=file_id, emails=emails, role=role, notify=notify
            )
            return result
        except Exception as e:
            return f"Error sharing file: {str(e)}"

    def _create_folder_wrapper(self, input_str: str) -> str:
        """Wrapper for create_folder. Format: 'folder_name|||parent_folder_id'"""
        try:
            parts = input_str.split("|||")
            folder_name = parts[0].strip()
            parent_folder_id = (
                parts[1].strip() if len(parts) > 1 and parts[1].strip() else None
            )

            result = self.create_folder(
                folder_name=folder_name, parent_folder_id=parent_folder_id
            )
            return str(result)
        except Exception as e:
            return f"Error creating folder: {str(e)}"

    def _list_files_wrapper(self, input_str: str) -> str:
        """Wrapper for list_files. Format: 'folder_id|||file_type|||max_results'"""
        try:
            parts = input_str.split("|||")
            folder_id = parts[0].strip() if parts[0].strip() else None
            file_type = (
                parts[1].strip() if len(parts) > 1 and parts[1].strip() else None
            )
            max_results = (
                int(parts[2].strip()) if len(parts) > 2 and parts[2].strip() else 10
            )

            result = self.list_files(
                folder_id=folder_id, file_type=file_type, max_results=max_results
            )
            return str(result)
        except Exception as e:
            return f"Error listing files: {str(e)}"

    def _move_file_wrapper(self, input_str: str) -> str:
        """Wrapper for move_file. Format: 'file_id|||destination_folder_id'"""
        try:
            parts = input_str.split("|||")
            file_id = parts[0].strip()
            destination_folder_id = parts[1].strip()

            result = self.move_file(
                file_id=file_id, destination_folder_id=destination_folder_id
            )
            return result
        except Exception as e:
            return f"Error moving file: {str(e)}"

    def get_tools_wrappers(self):
        """Get tools with wrapper methods that parse string inputs"""
        tools = [
            Tool(
                name="upload_file_to_drive",
                description="Upload file to Google Drive. Format: 'file_path|||folder_id|||file_name'",  # noqa
                func=self._upload_file_wrapper,
            ),
            Tool(
                name="download_file_from_drive",
                description="Download file from Google Drive. Format: 'file_id|||file_name|||local_path'",  # noqa
                func=self._download_file_wrapper,
            ),
            Tool(
                name="share_drive_file",
                description="Share Drive file with users. Format: 'file_id|||emails_json|||role|||notify'",  # noqa
                func=self._share_file_wrapper,
            ),
            Tool(
                name="create_drive_folder",
                description="Create new Drive folder. Format: 'folder_name|||parent_folder_id'",
                func=self._create_folder_wrapper,
            ),
            Tool(
                name="list_drive_files",
                description="List Drive files. Format: 'folder_id|||file_type|||max_results'",
                func=self._list_files_wrapper,
            ),
            Tool(
                name="move_drive_file",
                description="Move file to different folder. Format: 'file_id|||destination_folder_id'",  # noqa
                func=self._move_file_wrapper,
            ),
        ]
        return tools

    def get_tools(self):
        tools = [
            Tool(
                name="upload_file_to_drive",
                description='Upload file to Google Drive. JSON: {"file_path": "str", "folder_id": "str", "file_name": "str"}',
                func=lambda params: self.upload_file(**(params if isinstance(params, dict) else __import__("json").loads(params))),
            ),
            Tool(
                name="download_file_from_drive",
                description='Download file from Google Drive. JSON: {"file_id": "str", "file_name": "str", "local_path": "str"}',
                func=lambda params: self.download_file(**(params if isinstance(params, dict) else __import__("json").loads(params))),
            ),
            Tool(
                name="share_drive_file",
                description='Share file with users. JSON: {"file_id": "str", "emails": ["str"], "role": "str", "notify": true/false}',
                func=lambda params: self.share_file(**(params if isinstance(params, dict) else __import__("json").loads(params))),
            ),
            Tool(
                name="create_drive_folder",
                description='Create a new folder. JSON: {"folder_name": "str", "parent_folder_id": "str"}',
                func=lambda params: self.create_folder(**(params if isinstance(params, dict) else __import__("json").loads(params))),
            ),
            Tool(
                name="list_drive_files",
                description='List files in Drive. JSON: {"folder_id": "str", "file_type": "str", "max_results": int}',
                func=lambda params: self.list_files(**(params if isinstance(params, dict) else __import__("json").loads(params))),
            ),
            Tool(
                name="move_drive_file",
                description='Move file to different folder. JSON: {"file_id": "str", "destination_folder_id": "str"}',
                func=lambda params: self.move_file(**(params if isinstance(params, dict) else __import__("json").loads(params))),
            ),
        ]
        return tools
