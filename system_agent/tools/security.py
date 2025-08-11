import hashlib
import os


class SecurityManager:
    """Handles security operations"""

    @staticmethod
    def calculate_file_hash(file_path: str, hash_type: str = "md5") -> str:
        """Calculate file hash"""
        try:
            if not os.path.exists(file_path):
                return f"Error: File '{file_path}' does not exist"

            hash_type = hash_type.lower()
            if hash_type not in ["md5", "sha1", "sha256", "sha512"]:
                return "Error: Supported hash types are md5, sha1, sha256, sha512"

            hash_obj = getattr(hashlib, hash_type)()

            with open(file_path, "rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hash_obj.update(chunk)

            return f"{hash_type.upper()} hash of '{file_path}': {hash_obj.hexdigest()}"
        except Exception as e:
            return f"Error calculating hash: {str(e)}"

    @staticmethod
    def scan_directory_for_duplicates(directory: str) -> str:
        """Find duplicate files in directory"""
        try:
            if not os.path.exists(directory):
                return f"Error: Directory '{directory}' does not exist"

            file_hashes = {}
            duplicates = []

            for root, dirs, files in os.walk(directory):
                for file in files:
                    file_path = os.path.join(root, file)
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
