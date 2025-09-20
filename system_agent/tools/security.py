import hashlib
import os
from typing import List, Optional

from langchain.tools import StructuredTool

from system_agent.config import DEFAULT_IGNORE_DIRS, DEFAULT_IGNORE_FILES


class SecurityManager:
    """Handles security operations"""

    @staticmethod
    def hash_file(file_path: str, algorithm: str = "sha256") -> str:
        """Calculate file hash"""
        try:
            if not os.path.exists(file_path):
                return f"Error: File '{file_path}' does not exist"

            algorithm = algorithm.lower()
            if algorithm not in ["md5", "sha1", "sha256", "sha512"]:
                return "Error: Supported hash types are md5, sha1, sha256, sha512"

            hash_obj = getattr(hashlib, algorithm)()

            with open(file_path, "rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hash_obj.update(chunk)

            return f"{algorithm.upper()} hash of '{file_path}': {hash_obj.hexdigest()}"
        except Exception as e:
            return f"Error calculating hash: {str(e)}"

    @staticmethod
    def find_duplicate_files(
        directory: str,
        min_file_size: int = 1,
        max_file_size: int = 100 * 1024 * 1024,
        exclude_dirs: Optional[List[str]] = None,
        exclude_extensions: Optional[List[str]] = None,
    ) -> str:
        """Find duplicate files in directory"""
        try:
            if not os.path.exists(directory):
                return f"Error: Directory '{directory}' does not exist"

            if exclude_dirs is None:
                exclude_dirs = DEFAULT_IGNORE_DIRS
            if exclude_extensions is None:
                exclude_extensions = DEFAULT_IGNORE_FILES

            file_hashes = {}
            duplicates = []

            for root, dirs, files in os.walk(directory):
                for dir in dirs:
                    if dir in exclude_dirs:
                        dirs.remove(dir)
                for file in files:
                    file_path = os.path.join(root, file)
                    file_size = os.path.getsize(file_path)
                    if file_size < min_file_size or file_size > max_file_size:
                        continue
                    if os.path.splitext(file)[1].lower() in exclude_extensions:
                        continue
                    try:
                        with open(file_path, "rb") as f:
                            file_hash = hashlib.md5(f.read()).hexdigest()

                        if file_hash in file_hashes:
                            duplicates.append((file_path, file_hashes[file_hash]))
                        else:
                            file_hashes[file_hash] = file_path
                    except Exception:
                        continue

            if duplicates:
                result = f"Found {len(duplicates)} duplicate file pairs:\n"
                for dup in duplicates[:10]:
                    result += f"Duplicate: {dup[0]} <-> {dup[1]}\n"
                if len(duplicates) > 10:
                    result += f"... and {len(duplicates) - 10} more duplicates\n"
                return result
            else:
                return "No duplicate files found"

        except Exception as e:
            return f"Error scanning for duplicates: {str(e)}"

    def get_tools(self) -> List[StructuredTool]:
        """Return a list of StructuredTool objects for security operations."""
        return [
            StructuredTool.from_function(
                name="hash_file",
                func=self.hash_file,
                args_schema={
                    "file_path": {
                        "type": "string",
                        "description": "Path to the file to hash",
                    },
                    "algorithm": {
                        "type": "string",
                        "description": "Hashing algorithm to use",
                        "enum": ["md5", "sha1", "sha256", "sha512"],
                        "default": "sha256",
                    },
                },
                description="""Calculate the hash of a file using the specified algorithm.
                Example:
                {
                    "file_path": "path/to/file.txt",
                    "algorithm": "sha256"
                }
                Supported algorithms: md5, sha1, sha256, sha512""",
            ),
            StructuredTool.from_function(
                name="find_duplicate_files",
                func=self.find_duplicate_files,
                args_schema={
                    "directory": {
                        "type": "string",
                        "description": "Directory to search for duplicate files in",
                        "default": ".",
                    },
                    "algorithm": {
                        "type": "string",
                        "description": "Hashing algorithm to use for comparison",
                        "enum": ["md5", "sha1", "sha256"],
                        "default": "md5",
                    },
                    "min_file_size": {
                        "type": "integer",
                        "description": "Minimum file size in bytes to consider (default: 1)",
                        "default": 1,
                    },
                    "max_file_size": {
                        "type": "integer",
                        "description": "Maximum file size in bytes to consider (default: 100MB)",
                        "default": 100 * 1024 * 1024,
                    },
                    "exclude_dirs": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Directories to exclude from search",
                        "default": ["venv", ".git", "__pycache__"],
                    },
                    "exclude_extensions": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "File extensions to exclude (with leading .)",
                        "default": [
                            ".pyc",
                            ".pyo",
                            ".pyd",
                            ".so",
                            ".dll",
                            ".exe",
                            ".zip",
                            ".tar",
                        ],
                    },
                },
                description="""Find duplicate files in a directory using file hashing.
                Example (full parameters):
                {
                    "directory": "/path/to/search",
                    "algorithm": "sha256",
                    "min_file_size": 1024,
                    "max_file_size": 104857600,
                    "exclude_dirs": ["venv", ".git"],
                    "exclude_extensions": [".pyc", ".pyo"]
                }
                Simple usage:
                {
                    "directory": "/path/to/search"
                }""",
            ),
        ]
