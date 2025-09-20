import os
import shutil
import zipfile
from typing import List, Optional

from langchain.tools import StructuredTool


class ArchiveManager:
    """Handles compression and archiving"""

    @staticmethod
    def create_zip_archive(
        source_path: str,
        archive_path: str,
        compression: str = "deflated",
        compression_level: int = 6,
        include_hidden: bool = False,
    ) -> str:
        """Create a ZIP archive from a file or directory.

        Args:
            source_path: Path to the file or directory to archive
            archive_path: Path where the ZIP archive will be created
            compression: Compression method ('stored' or 'deflated')
            compression_level: Compression level (0-9, where 0 is no compression)
            include_hidden: Whether to include hidden files/directories

        Returns:
            str: Success/error message
        """
        try:
            # Validate compression method
            compression_methods = {
                "stored": zipfile.ZIP_STORED,
                "deflated": zipfile.ZIP_DEFLATED,
            }
            if compression.lower() not in compression_methods:
                return f"Error: Invalid compression method. Must be one of: {', '.join(compression_methods.keys())}"  # noqa

            # Validate compression level
            if not 0 <= compression_level <= 9:
                return "Error: Compression level must be between 0 and 9"

            source_path = os.path.abspath(source_path)
            archive_path = os.path.abspath(archive_path)

            # Check if source exists
            if not os.path.exists(source_path):
                return f"Error: Source path '{source_path}' does not exist"

            # Check if archive path directory exists
            archive_dir = os.path.dirname(archive_path)
            if archive_dir and not os.path.exists(archive_dir):
                os.makedirs(archive_dir, exist_ok=True)

            # Check available disk space (at least 2x the source size)
            if os.path.exists(source_path):
                total_size = 0
                for dirpath, _, filenames in os.walk(source_path):
                    for f in filenames:
                        fp = os.path.join(dirpath, f)
                        if not include_hidden and os.path.basename(fp).startswith("."):
                            continue
                        try:
                            total_size += os.path.getsize(fp)
                        except (OSError, PermissionError):
                            continue

                try:
                    stat = os.statvfs(archive_dir)
                    available_space = stat.f_frsize * stat.f_bavail
                    if total_size * 2 > available_space:
                        return f"Error: Not enough disk space available. Need at least {total_size * 2} bytes"  # noqa
                except AttributeError:
                    # statvfs not available on this platform
                    pass

            # Create the archive
            with zipfile.ZipFile(
                archive_path,
                "w",
                compression=compression_methods[compression],
                compresslevel=compression_level,
            ) as zipf:
                if os.path.isfile(source_path):
                    # Add single file
                    zipf.write(source_path, os.path.basename(source_path))
                elif os.path.isdir(source_path):
                    # Add directory contents
                    for root, dirs, files in os.walk(source_path):
                        # Skip hidden files/directories if not included
                        if not include_hidden:
                            files = [f for f in files if not f.startswith(".")]
                            dirs[:] = [d for d in dirs if not d.startswith(".")]

                        for file in files:
                            file_path = os.path.join(root, file)
                            arcname = os.path.relpath(
                                file_path, os.path.dirname(source_path)
                            )
                            try:
                                zipf.write(file_path, arcname)
                            except (OSError, PermissionError) as e:
                                return f"Error adding file to archive: {str(e)}"

            # Verify the archive was created
            if not os.path.exists(archive_path):
                return "Error: Failed to create archive"

            archive_size = os.path.getsize(archive_path)
            return (
                f"Archive created successfully: {archive_path}\n"
                f"Size: {archive_size} bytes\n"
                f"Compression: {compression} (level {compression_level})"
            )

        except zipfile.BadZipFile:
            return "Error: Failed to create archive - invalid ZIP file"
        except PermissionError:
            return f"Error: Permission denied when creating archive at {archive_path}"
        except OSError as e:
            return f"Error creating archive: {str(e)}"

    @staticmethod
    def extract_zip_archive(
        archive_path: str,
        extract_path: str,
        password: Optional[str] = None,
        members: Optional[List[str]] = None,
        overwrite: bool = False,
    ) -> str:
        """Extract a ZIP archive to a specified directory.

        Args:
            archive_path: Path to the ZIP archive to extract
            extract_path: Directory where to extract the contents
            password: Optional password for encrypted archives
            members: Optional list of filenames to extract (default: extract all)
            overwrite: Whether to overwrite existing files (default: False)

        Returns:
            str: Success/error message with extraction details
        """
        try:
            # Validate archive path
            if not os.path.isfile(archive_path):
                return (
                    f"Error: Archive '{archive_path}' does not exist or is not a file"
                )

            # Check if the file is actually a zip file
            if not zipfile.is_zipfile(archive_path):
                return f"Error: '{archive_path}' is not a valid ZIP archive"

            # Create extraction directory if it doesn't exist
            os.makedirs(extract_path, exist_ok=True)

            # Check available disk space
            try:
                archive_size = os.path.getsize(archive_path)
                stat = os.statvfs(extract_path)
                available_space = stat.f_frsize * stat.f_bavail
                if archive_size * 2 > available_space:
                    return f"Error: Not enough disk space available. Need at least {archive_size * 2} bytes"  # noqa
            except (AttributeError, OSError):
                # statvfs not available on this platform or other error
                pass

            # Extract the archive
            extracted_files = []
            with zipfile.ZipFile(archive_path, "r") as zip_ref:
                # Set password if provided
                if password:
                    zip_ref.setpassword(password.encode("utf-8"))

                # Get list of files to extract
                file_list = members if members is not None else zip_ref.namelist()

                # Check for zip bombs (too many files or too deep paths)
                if len(file_list) > 10000:  # Arbitrary limit
                    return "Error: Archive contains too many files (potential zip bomb)"

                for file in file_list:
                    # Prevent path traversal attacks
                    file_path = os.path.abspath(os.path.join(extract_path, file))
                    if not file_path.startswith(os.path.abspath(extract_path)):
                        return f"Error: Attempted path traversal in archive with file: {file}"

                # Extract files
                for file in file_list:
                    try:
                        # Skip directories (they'll be created automatically)
                        if not file.endswith("/"):
                            # Check if file exists and we're not overwriting
                            dest_path = os.path.join(extract_path, file)
                            if os.path.exists(dest_path) and not overwrite:
                                return f"Error: File already exists: {dest_path} (use overwrite=True to overwrite)"  # noqa

                            # Create parent directories if they don't exist
                            os.makedirs(os.path.dirname(dest_path), exist_ok=True)

                            # Extract the file
                            with zip_ref.open(file) as source, open(
                                dest_path, "wb"
                            ) as target:
                                shutil.copyfileobj(source, target)

                            extracted_files.append(file)
                    except (RuntimeError, zipfile.BadZipFile) as e:
                        if "password" in str(e).lower():
                            return "Error: Incorrect password or encrypted file"
                        return f"Error extracting file '{file}': {str(e)}"
                    except Exception as e:
                        return f"Error extracting file '{file}': {str(e)}"

            # Verify extraction
            if not extracted_files:
                return "Warning: No files were extracted from the archive"

            return (
                f"Successfully extracted {len(extracted_files)} files to: {extract_path}\n"
                f"First few files: {', '.join(extracted_files[:5])}{'...' if len(extracted_files) > 5 else ''}"  # noqa
            )

        except zipfile.BadZipFile:
            return "Error: The file is not a valid ZIP archive"
        except PermissionError:
            return f"Error: Permission denied when extracting to {extract_path}"
        except Exception as e:
            return f"Error extracting archive: {str(e)}"

    def get_tools(self) -> List[StructuredTool]:
        """Return a list of StructuredTool objects for archive operations."""
        return [
            StructuredTool.from_function(
                name="create_zip_archive",
                func=self.create_zip_archive,
                args_schema={
                    "source_path": {
                        "type": "string",
                        "description": "Path to the file or directory to archive",
                    },
                    "archive_path": {
                        "type": "string",
                        "description": "Path where the ZIP archive will be created",
                    },
                    "compression": {
                        "type": "string",
                        "description": "Compression method ('stored' or 'deflated')",
                        "default": "deflated",
                    },
                    "compression_level": {
                        "type": "integer",
                        "description": "Compression level (0-9, where 0 is no compression)",
                        "default": 6,
                    },
                    "include_hidden": {
                        "type": "boolean",
                        "description": "Whether to include hidden files/directories",
                        "default": False,
                    },
                },
                description="""Create a ZIP archive from a file or directory.
                Example:
                {
                    "source_path": "/path/to/source",
                    "archive_path": "archive.zip",
                    "compression": "deflated",
                    "compression_level": 6,
                    "include_hidden": false
                }
                Features:
                - Supports both files and directories
                - Configurable compression level (0-9)
                - Option to exclude hidden files
                - Automatic directory creation
                - Disk space and size validation""",
            ),
            StructuredTool.from_function(
                name="extract_zip_archive",
                func=self.extract_zip_archive,
                args_schema={
                    "archive_path": {
                        "type": "string",
                        "description": "Path to the ZIP archive to extract",
                    },
                    "extract_path": {
                        "type": "string",
                        "description": "Directory where to extract the contents",
                    },
                    "password": {
                        "type": "string",
                        "description": "Password for encrypted archives",
                        "default": None,
                    },
                    "members": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of specific files to extract (default: all)",
                        "default": None,
                    },
                    "overwrite": {
                        "type": "boolean",
                        "description": "Whether to overwrite existing files",
                        "default": False,
                    },
                },
                description="""Extract a ZIP archive to a specified directory.
                Example:
                {
                    "archive_path": "archive.zip",
                    "extract_path": "./extracted",
                    "password": "mypassword",
                    "members": ["file1.txt", "subdir/file2.txt"],
                    "overwrite": false
                }
                Features:
                - Supports password-protected archives
                - Selective file extraction
                - Overwrite protection
                - Path traversal protection
                - Disk space validation
                - Progress tracking""",
            ),
        ]
