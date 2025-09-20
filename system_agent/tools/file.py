import fnmatch
import mmap
import os
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from typing import List, Set

from langchain.tools import StructuredTool

from system_agent.config import (
    DEFAULT_IGNORE_DIRS,
    DEFAULT_IGNORE_FILES,
    DISABLE_SMART_IGNORE,
)


class FileManager:
    """Handles file operations with proper error handling and path management"""

    @staticmethod
    def _normalize_path(file_path: str) -> str:
        """Normalize file path and ensure it's within workspace"""
        # Get the workspace root directory
        workspace_root = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "../../")
        )

        # Convert to absolute path if relative
        if not os.path.isabs(file_path):
            file_path = os.path.join(workspace_root, file_path)

        # Normalize path
        normalized_path = os.path.normpath(os.path.abspath(file_path))

        # Check if path is within workspace
        if not normalized_path.startswith(workspace_root):
            raise ValueError(
                f"Access denied: Cannot access files outside the workspace. "
                f"Please use paths within {workspace_root}"
            )

        return normalized_path

    @staticmethod
    def read_file(file_path: str) -> str:
        """Read content from a file"""
        try:
            if not file_path or file_path.strip() == "":
                return "Error: No file path provided"

            try:
                file_path = FileManager._normalize_path(file_path.strip())

            except ValueError as e:
                return str(e)

            if not os.path.exists(file_path):
                return f"Error: File '{file_path}' does not exist"

            if not os.path.isfile(file_path):
                return f"Error: '{file_path}' is not a file"

            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()

            if content.strip() == "":
                return f"File '{file_path}' exists but is empty"

            return f"Successfully read file '{file_path}':\n\n{content}"
        except PermissionError:
            return f"Error: Permission denied to read file '{file_path}'"
        except UnicodeDecodeError:
            try:
                with open(file_path, "rb") as f:
                    content = f.read()
                return f"File '{file_path}' appears to be binary. Size: {len(content)} bytes"
            except Exception:
                return f"Error: Cannot read file '{file_path}' - appears to be binary or corrupted"
        except Exception as e:
            return f"Error reading file '{file_path}': {str(e)}"

    @staticmethod
    def write_file(file_path: str, content: str, mode: str = "w") -> str:
        """Write content to a file (if not exists create's new file)"""
        try:
            if not file_path or file_path.strip() == "":
                return "Error: No file path provided"

            file_path = file_path.strip()
            file_path = FileManager._normalize_path(file_path)

            directory = os.path.dirname(file_path)
            if directory and not os.path.exists(directory):
                os.makedirs(directory, exist_ok=True)

            with open(file_path, mode, encoding="utf-8") as f:
                f.write(content)

            if os.path.exists(file_path):
                file_size = os.path.getsize(file_path)
                return f"Successfully wrote {file_size} bytes to '{file_path}'"
            return f"File '{file_path}' created but could not verify size"
        except PermissionError:
            return f"Error: Permission denied to write to '{file_path}'"
        except OSError as e:
            return f"Error: Cannot write to '{file_path}' - {str(e)}"
        except Exception as e:
            return f"Error writing to file '{file_path}': {str(e)}"

    @staticmethod
    def append_file(file_path: str, content: str) -> str:
        """Append content to a file (creates file if it doesn't exist)"""
        try:
            if not file_path or file_path.strip() == "":
                return "Error: No file path provided"

            file_path = file_path.strip()
            file_path = FileManager._normalize_path(file_path)

            # Create directory if it doesn't exist
            directory = os.path.dirname(file_path)
            if directory and not os.path.exists(directory):
                os.makedirs(directory, exist_ok=True)

            with open(file_path, "a", encoding="utf-8") as f:
                f.write(content)

            if os.path.exists(file_path):
                file_size = os.path.getsize(file_path)
                return f"Successfully appended {len(content)} bytes to '{file_path}'. New size: {file_size} bytes"  # noqa
            return f"Content appended to '{file_path}' but could not verify size"

        except PermissionError:
            return f"Error: Permission denied to write to '{file_path}'"
        except Exception as e:
            return f"Error appending to file '{file_path}': {str(e)}"

    @staticmethod
    def delete_file(file_path: str) -> str:
        """Delete a file"""
        try:
            if not file_path or file_path.strip() == "":
                return "Error: No file path provided"

            file_path = file_path.strip()
            file_path = FileManager._normalize_path(file_path)

            if not os.path.exists(file_path):
                return f"Error: File '{file_path}' does not exist"

            if not os.path.isfile(file_path):
                return f"Error: '{file_path}' is not a file (might be a directory)"

            os.remove(file_path)

            if not os.path.exists(file_path):
                return f"Successfully deleted file '{file_path}'"
            else:
                return f"Error: Failed to delete file '{file_path}'"

        except PermissionError:
            return f"Error: Permission denied to delete '{file_path}'"
        except Exception as e:
            return f"Error deleting file '{file_path}': {str(e)}"

    @staticmethod
    def list_files(directory: str = ".") -> str:
        """List files in a directory"""
        try:
            if not directory:
                directory = "."

            directory = directory.strip()
            directory = FileManager._normalize_path(directory)

            if not os.path.exists(directory):
                return f"Error: Directory '{directory}' does not exist"

            if not os.path.isdir(directory):
                return f"Error: '{directory}' is not a directory"

            items = os.listdir(directory)

            if not items:
                return f"Directory '{directory}' is empty"

            files = []
            directories = []

            for item in sorted(items):
                item_path = os.path.join(directory, item)
                if os.path.isfile(item_path):
                    size = os.path.getsize(item_path)
                    files.append(f"📄 {item} ({size} bytes)")
                elif os.path.isdir(item_path):
                    directories.append(f"📁 {item}/")

            result = f"Contents of directory '{directory}':\n"

            if directories:
                result += "\nDirectories:\n" + "\n".join(directories)

            if files:
                result += "\nFiles:\n" + "\n".join(files)

            return result

        except PermissionError:
            return f"Error: Permission denied to list directory '{directory}'"
        except Exception as e:
            return f"Error listing directory '{directory}': {str(e)}"

    @staticmethod
    def get_file_info(file_path: str) -> str:
        """Get detailed information about a file"""
        try:
            if not file_path or file_path.strip() == "":
                return "Error: No file path provided"

            file_path = file_path.strip()
            file_path = FileManager._normalize_path(file_path)

            if not os.path.exists(file_path):
                return f"Error: '{file_path}' does not exist"

            stat_info = os.stat(file_path)

            info = f"File information for '{file_path}':\n"
            info += f"Type: {'File' if os.path.isfile(file_path) else 'Directory'}\n"
            info += f"Size: {stat_info.st_size} bytes\n"
            info += f"Created: {datetime.fromtimestamp(stat_info.st_ctime)}\n"
            info += f"Modified: {datetime.fromtimestamp(stat_info.st_mtime)}\n"
            info += f"Permissions: {oct(stat_info.st_mode)[-3:]}\n"

            return info

        except Exception as e:
            return f"Error getting file info for '{file_path}': {str(e)}"

    @staticmethod
    def search_string_in_files(
        search_string,
        directory=None,
        file_pattern="*",
        ignore_case=True,
        max_workers=4,
        max_file_size_mb=100,
        use_memory_mapping=True,
        disable_smart_ignore=DISABLE_SMART_IGNORE,
        custom_ignore_patterns=None,
        additional_ignore_dirs=None,
        additional_ignore_files=None,
    ):
        """
        High-performance recursive string search using multiple optimization techniques.
        Now includes smart filtering to ignore common unwanted directories and files.

        Args:
            search_string (str): The string to search for
            directory (str, optional): Directory to search in. Defaults to current directory.
            file_pattern (str): File pattern to match. Defaults to "*".
            ignore_case (bool): Whether to ignore case. Defaults to True.
            max_workers (int): Number of parallel threads. Defaults to 4.
            max_file_size_mb (int): Skip files larger than this (MB). Defaults to 100.
            use_memory_mapping (bool): Use memory mapping for large files. Defaults to True.
            disable_smart_ignore (bool): Disable automatic ignore patterns. Defaults to False.
            custom_ignore_patterns (list): Additional patterns to ignore. Defaults to None.
            additional_ignore_dirs (list): Additional directory names to ignore. Defaults to None.
            additional_ignore_files (list): Additional file patterns to ignore. Defaults to None.

        Returns:
            list: List of search results
        """

        def _search_with_mmap(file_path, search_bytes, ignore_case, base_directory):
            """Search using memory mapping - fastest for larger files."""
            results = []

            # Normalize path if FileManager is available
            try:
                file_path = FileManager._normalize_path(file_path.strip())
            except Exception:
                file_path = file_path.strip()

            try:
                with open(file_path, "rb") as f:
                    with mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ) as mm:
                        if ignore_case:
                            content = mm[:].lower()
                        else:
                            content = mm[:]

                        # Find all occurrences
                        start = 0
                        while True:
                            pos = content.find(search_bytes, start)
                            if pos == -1:
                                break

                            # Find line number and content
                            line_start = content.rfind(b"\n", 0, pos) + 1
                            line_end = content.find(b"\n", pos)
                            if line_end == -1:
                                line_end = len(content)

                            line_number = content[:pos].count(b"\n") + 1
                            line_content = (
                                content[line_start:line_end]
                                .decode("utf-8", errors="ignore")
                                .strip()
                            )

                            results.append(
                                {
                                    "file_path": file_path,
                                    "line_number": line_number,
                                    "line_content": line_content,
                                    "relative_path": os.path.relpath(
                                        file_path, base_directory
                                    ),
                                }
                            )

                            start = pos + 1

            except Exception:
                pass

            return results

        def _search_with_read(file_path, search_bytes, ignore_case, base_directory):
            """Search by reading entire file into memory - good for smaller files."""
            results = []

            try:
                with open(file_path, "rb") as f:
                    content = f.read()

                if ignore_case:
                    content_to_search = content.lower()
                else:
                    content_to_search = content

                # Find all occurrences
                start = 0
                while True:
                    pos = content_to_search.find(search_bytes, start)
                    if pos == -1:
                        break

                    # Find line number and content
                    line_start = content.rfind(b"\n", 0, pos) + 1
                    line_end = content.find(b"\n", pos)
                    if line_end == -1:
                        line_end = len(content)

                    line_number = content[:pos].count(b"\n") + 1
                    line_content = (
                        content[line_start:line_end]
                        .decode("utf-8", errors="ignore")
                        .strip()
                    )

                    results.append(
                        {
                            "file_path": file_path,
                            "line_number": line_number,
                            "line_content": line_content,
                            "relative_path": os.path.relpath(file_path, base_directory),
                        }
                    )

                    start = pos + 1

            except Exception:
                pass

            return results

        def _should_ignore_path(
            path: str,
            ignore_dirs: Set[str],
            ignore_files: Set[str],
            custom_ignore_patterns: List[str] = None,
        ) -> bool:
            """
            Check if a path should be ignored based on ignore patterns.

            Args:
                path: File or directory path to check
                ignore_dirs: Set of directory names to ignore
                ignore_files: Set of file patterns to ignore
                custom_ignore_patterns: Additional custom patterns to ignore

            Returns:
                bool: True if path should be ignored
            """
            path_name = os.path.basename(path)

            # Check directory names
            if os.path.isdir(path) and path_name in ignore_dirs:
                return True

            # Check file patterns
            if os.path.isfile(path):
                for pattern in ignore_files:
                    if fnmatch.fnmatch(path_name.lower(), pattern.lower()):
                        return True

            # Check custom patterns
            if custom_ignore_patterns:
                for pattern in custom_ignore_patterns:
                    if fnmatch.fnmatch(path_name.lower(), pattern.lower()):
                        return True
                    # Also check if pattern matches any part of the path
                    if fnmatch.fnmatch(path.lower(), f"*{pattern.lower()}*"):
                        return True

            return False

        if directory is None:
            directory = os.getcwd()

        # Convert to bytes for faster searching
        search_bytes = search_string.encode("utf-8", errors="ignore")
        if ignore_case:
            search_bytes = search_bytes.lower()

        # Setup ignore patterns
        if disable_smart_ignore:
            ignore_dirs = set(additional_ignore_dirs or [])
            ignore_files = set(additional_ignore_files or [])
        else:
            ignore_dirs = DEFAULT_IGNORE_DIRS.copy()
            if additional_ignore_dirs:
                ignore_dirs.update(additional_ignore_dirs)
            ignore_files = DEFAULT_IGNORE_FILES.copy()
            if additional_ignore_files:
                ignore_files.update(additional_ignore_files)

        # Collect all files with smart filtering
        files_to_search = []
        max_file_size_bytes = max_file_size_mb * 1024 * 1024

        for root, dirs, files in os.walk(directory):
            # Filter out ignored directories from dirs list (modifies in-place to prevent walking into them) # noqa
            dirs[:] = [
                d
                for d in dirs
                if not _should_ignore_path(
                    os.path.join(root, d),
                    ignore_dirs,
                    ignore_files,
                    custom_ignore_patterns,
                )
            ]

            # Skip if current directory should be ignored
            if _should_ignore_path(
                root, ignore_dirs, ignore_files, custom_ignore_patterns
            ):
                continue

            for file in files:
                file_path = os.path.join(root, file)

                # Skip ignored files
                if _should_ignore_path(
                    file_path, ignore_dirs, ignore_files, custom_ignore_patterns
                ):
                    continue

                # Check file pattern match
                if fnmatch.fnmatch(file, file_pattern):
                    try:
                        file_size = os.path.getsize(file_path)
                        if file_size <= max_file_size_bytes:
                            files_to_search.append((file_path, file_size))
                    except OSError:
                        continue

        # Use thread pool for parallel processing
        results = []
        results_lock = threading.Lock()

        def search_file(file_info):
            file_path, file_size = file_info
            file_results = []

            try:
                if use_memory_mapping and file_size > 1024:  # Use mmap for files > 1KB
                    file_results = _search_with_mmap(
                        file_path, search_bytes, ignore_case, directory
                    )
                else:
                    file_results = _search_with_read(
                        file_path, search_bytes, ignore_case, directory
                    )

            except Exception:
                # Silently skip problematic files
                pass

            return file_results

        # Process files in parallel
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_file = {
                executor.submit(search_file, file_info): file_info
                for file_info in files_to_search
            }

            for future in as_completed(future_to_file):
                file_results = future.result()
                if file_results:
                    with results_lock:
                        results.extend(file_results)

        return results

    def get_tools(self) -> List[StructuredTool]:
        """Return a list of StructuredTool objects for file operations."""
        return [
            StructuredTool.from_function(
                name="read_file",
                func=self.read_file,
                args_schema={
                    "file_path": {
                        "type": "string",
                        "description": "Path to the file to read",
                    }
                },
                description="""Read content from a file.
                Example:
                {
                    "file_path": "path/to/file.txt"
                }""",
            ),
            StructuredTool.from_function(
                name="write_file",
                func=self.write_file,
                args_schema={
                    "file_path": {
                        "type": "string",
                        "description": "Path where the file will be written",
                    },
                    "content": {
                        "type": "string",
                        "description": "Content to write to the file",
                    },
                    "mode": {
                        "type": "string",
                        "description": "Write mode: 'w' for write (default), 'a' for append",
                        "default": "w",
                    },
                },
                description="""Write content to a file. Creates file if it doesn't exist.
                Example:
                {
                    "file_path": "path/to/file.txt",
                    "content": "Hello, World!",
                    "mode": "w"
                }""",
            ),
            StructuredTool.from_function(
                name="append_file",
                func=self.append_file,
                args_schema={
                    "file_path": {
                        "type": "string",
                        "description": "Path to the file to append to",
                    },
                    "content": {
                        "type": "string",
                        "description": "Content to append to the file",
                    },
                },
                description="""Append content to an existing file.
                Example:
                {
                    "file_path": "path/to/file.txt",
                    "content": "Additional content"
                }""",
            ),
            StructuredTool.from_function(
                name="list_files",
                func=self.list_files,
                args_schema={
                    "directory": {
                        "type": "string",
                        "description": "Directory path to list contents of (default: current directory)",  # noqa
                        "default": ".",
                    }
                },
                description="""List files and directories in a directory.
                Example:
                {
                    "directory": "path/to/directory"
                }""",
            ),
            StructuredTool.from_function(
                name="search_string_in_files",
                func=self.search_string_in_files,
                args_schema={
                    "search_string": {
                        "type": "string",
                        "description": "Text to search for in files",
                    },
                    "directory": {
                        "type": "string",
                        "description": "Directory to search in (default: current directory)",
                        "default": ".",
                    },
                    "file_extensions": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "File extensions to include (e.g., ['.py', '.txt'])",
                        "default": [],
                    },
                    "case_sensitive": {
                        "type": "boolean",
                        "description": "Whether the search is case sensitive",
                        "default": False,
                    },
                    "max_file_size_mb": {
                        "type": "number",
                        "description": "Maximum file size in MB to search",
                        "default": 5,
                    },
                    "exclude_dirs": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Directories to exclude from search",
                        "default": ["venv", ".git", "__pycache__"],
                    },
                    "additional_ignore_files": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Additional files to exclude from search",
                        "default": [],
                    },
                },
                description="""Search for a string in files within a directory.
                Example (full parameters):
                {
                    "search_string": "function",
                    "directory": "./src",
                    "file_extensions": [".py", ".txt"],
                    "case_sensitive": false,
                    "max_file_size_mb": 5,
                    "exclude_dirs": ["venv", ".git"],
                    "additional_ignore_files": []
                }
                Simple usage:
                {
                    "search_string": "function"
                }""",
            ),
            StructuredTool.from_function(
                name="delete_file",
                func=self.delete_file,
                args_schema={
                    "file_path": {
                        "type": "string",
                        "description": "Path to the file to delete",
                    },
                },
                description="Delete a file at a given path",
            ),
            StructuredTool.from_function(
                name="get_file_info",
                func=self.get_file_info,
                args_schema={
                    "file_path": {
                        "type": "string",
                        "description": "Path to the file to get info for",
                    },
                },
                description="Get detailed information about a file",
            ),
        ]
