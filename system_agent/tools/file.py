import fnmatch
import mmap
import os
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime


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

            directory = os.path.dirname(file_path)
            if directory and not os.path.exists(directory):
                os.makedirs(directory, exist_ok=True)

            with open(file_path, mode, encoding="utf-8") as f:
                f.write(content)

            if os.path.exists(file_path):
                file_size = os.path.getsize(file_path)
                action = "appended to" if mode == "a" else "created/wrote to"
                return f"Successfully {action} file '{file_path}' (Size: {file_size} bytes)"
            else:
                return f"Error: Failed to create file '{file_path}'"

        except PermissionError:
            return f"Error: Permission denied to write to '{file_path}'"
        except OSError as e:
            return f"Error: Cannot write to '{file_path}' - {str(e)}"
        except Exception as e:
            return f"Error writing to file '{file_path}': {str(e)}"

    @staticmethod
    def delete_file(file_path: str) -> str:
        """Delete a file"""
        try:
            if not file_path or file_path.strip() == "":
                return "Error: No file path provided"

            file_path = file_path.strip()

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
    ):
        """
        High-performance recursive string search using multiple optimization techniques.

        Args:
            search_string (str): The string to search for
            directory (str, optional): Directory to search in. Defaults to current directory.
            file_pattern (str): File pattern to match. Defaults to "*".
            ignore_case (bool): Whether to ignore case. Defaults to True.
            max_workers (int): Number of parallel threads. Defaults to 4.
            max_file_size_mb (int): Skip files larger than this (MB). Defaults to 100.
            use_memory_mapping (bool): Use memory mapping for large files. Defaults to True.

        Returns:
            list: List of search results
        """

        def _search_with_mmap(file_path, search_bytes, ignore_case, base_directory):
            """Search using memory mapping - fastest for larger files."""
            results = []

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

        if directory is None:
            directory = os.getcwd()

        # Convert to bytes for faster searching
        search_bytes = search_string.encode("utf-8", errors="ignore")
        if ignore_case:
            search_bytes = search_bytes.lower()

        # Collect all files first
        files_to_search = []
        max_file_size_bytes = max_file_size_mb * 1024 * 1024

        for root, dirs, files in os.walk(directory):
            for file in files:
                if fnmatch.fnmatch(file, file_pattern):
                    file_path = os.path.join(root, file)
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
