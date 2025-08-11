import os
from datetime import datetime


class FileManager:
    """Handles file operations with proper error handling and path management"""
    
    @staticmethod
    def read_file(file_path: str) -> str:
        """Read content from a file"""
        try:
            # Ensure we have a valid file path
            if not file_path or file_path.strip() == "":
                return "Error: No file path provided"
            
            # Clean the file path
            file_path = file_path.strip()
            
            # Check if file exists
            if not os.path.exists(file_path):
                return f"Error: File '{file_path}' does not exist"
            
            # Check if it's actually a file (not a directory)
            if not os.path.isfile(file_path):
                return f"Error: '{file_path}' is not a file"
            
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            if content.strip() == "":
                return f"File '{file_path}' exists but is empty"
            
            return f"Successfully read file '{file_path}':\n\n{content}"
        except PermissionError:
            return f"Error: Permission denied to read file '{file_path}'"
        except UnicodeDecodeError:
            try:
                # Try reading as binary and show first few bytes
                with open(file_path, 'rb') as f:
                    content = f.read()
                return f"File '{file_path}' appears to be binary. Size: {len(content)} bytes"
            except:
                return f"Error: Cannot read file '{file_path}' - appears to be binary or corrupted"
        except Exception as e:
            return f"Error reading file '{file_path}': {str(e)}"
    
    @staticmethod
    def write_file(file_path: str, content: str, mode: str = 'w') -> str:
        """Write content to a file"""
        try:
            # Ensure we have valid inputs
            if not file_path or file_path.strip() == "":
                return "Error: No file path provided"
            
            file_path = file_path.strip()
            
            # Create directory if it doesn't exist
            directory = os.path.dirname(file_path)
            if directory and not os.path.exists(directory):
                os.makedirs(directory, exist_ok=True)
            
            # Write the file
            with open(file_path, mode, encoding='utf-8') as f:
                f.write(content)
            
            # Verify the write was successful
            if os.path.exists(file_path):
                file_size = os.path.getsize(file_path)
                action = 'appended to' if mode == 'a' else 'created/wrote to'
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
            
            # Verify deletion
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
            
            # Separate files and directories
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
