import os
import zipfile


class ArchiveManager:
    """Handles compression and archiving"""

    @staticmethod
    def create_zip_archive(source_path: str, archive_path: str) -> str:
        """Create a ZIP archive"""
        try:
            with zipfile.ZipFile(archive_path, "w", zipfile.ZIP_DEFLATED) as zipf:
                if os.path.isfile(source_path):
                    zipf.write(source_path, os.path.basename(source_path))
                elif os.path.isdir(source_path):
                    for root, dirs, files in os.walk(source_path):
                        for file in files:
                            file_path = os.path.join(root, file)
                            arcname = os.path.relpath(file_path, source_path)
                            zipf.write(file_path, arcname)
                else:
                    return f"Error: Source path '{source_path}' does not exist"

            return f"Archive created successfully: {archive_path}"
        except Exception as e:
            return f"Error creating archive: {str(e)}"

    @staticmethod
    def extract_zip_archive(archive_path: str, extract_path: str) -> str:
        """Extract a ZIP archive"""
        try:
            if not os.path.exists(archive_path):
                return f"Error: Archive '{archive_path}' does not exist"

            with zipfile.ZipFile(archive_path, "r") as zipf:
                zipf.extractall(extract_path)

            return f"Archive extracted successfully to: {extract_path}"
        except Exception as e:
            return f"Error extracting archive: {str(e)}"
