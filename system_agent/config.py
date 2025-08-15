import os
from typing import Any, Dict, List

from dotenv import load_dotenv

load_dotenv()


# Model Configuration
MODEL_NAME = os.getenv("MODEL_NAME", "gemini-2.5-flash-lite")
MODEL_TEMPERATURE = float(os.getenv("MODEL_TEMPERATURE", "0.7"))


# Memory Configuration
MEMORY_WINDOW_SIZE = int(os.getenv("MEMORY_WINDOW_SIZE", "20"))


# Email Configuration
SMTP_SERVER = os.getenv("SMTP_SERVER", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
EMAIL_USE_TLS = os.getenv("EMAIL_USE_TLS", "True").lower() == "true"
EMAIL_USE_SSL = os.getenv("EMAIL_USE_SSL", "False").lower() == "true"
EMAIL_TIMEOUT = int(os.getenv("EMAIL_TIMEOUT", "30"))
EMAIL_DEFAULT_SENDER = os.getenv("EMAIL_DEFAULT_SENDER", "")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD", "")


# Web Scraper Configuration
WEB_USER_AGENT = os.getenv(
    "WEB_USER_AGENT",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",  # noqa
)
WEB_CONTENT_LIMIT = int(os.getenv("WEB_CONTENT_LIMIT", "5000"))
WEB_LINKS_LIMIT = int(os.getenv("WEB_LINKS_LIMIT", "20"))
WEB_REQUEST_TIMEOUT = int(os.getenv("WEB_REQUEST_TIMEOUT", "10"))


# System Command Configuration
COMMAND_TIMEOUT = int(os.getenv("COMMAND_TIMEOUT", "30"))
DANGEROUS_COMMANDS: List[str] = [
    "rm -rf /",
    "del /f /s /q",
    "format",
    "mkfs",
    "dd if=",
    "shutdown",
    "reboot",
    "halt",
    "sudo rm",
    "rm -rf *",
]


# Network Configuration
PING_COUNT = int(os.getenv("PING_COUNT", "4"))
DOWNLOAD_CHUNK_SIZE = int(os.getenv("DOWNLOAD_CHUNK_SIZE", "8192"))
DOWNLOAD_TIMEOUT = int(os.getenv("DOWNLOAD_TIMEOUT", "30"))


# Agent Configuration
AGENT_NAME = os.getenv("AGENT_NAME", "ThinkPad")
AGENT_MAX_ITERATIONS = int(os.getenv("AGENT_MAX_ITERATIONS", "15"))
AGENT_MAX_EXECUTION_TIME = int(os.getenv("AGENT_MAX_EXECUTION_TIME", "60"))


# Default directories and files to ignore
DISABLE_SMART_IGNORE = False

DEFAULT_IGNORE_DIRS = {
    # Virtual environments
    "venv",
    "env",
    ".venv",
    ".env",
    "virtualenv",
    "ENV",
    "env.bak",
    "venv.bak",
    # Package managers and dependencies
    "node_modules",
    "__pycache__",
    ".pytest_cache",
    "pip-wheel-metadata",
    "site-packages",
    "dist",
    "build",
    "egg-info",
    ".eggs",
    "wheels",
    # Version control
    ".git",
    ".hg",
    ".svn",
    ".bzr",
    "_darcs",
    # IDEs and editors
    ".vscode",
    ".idea",
    ".vs",
    ".atom",
    ".sublime-project",
    ".sublime-workspace",
    # OS specific
    ".DS_Store",
    "Thumbs.db",
    "__MACOSX",
    # Logs and temporary files
    "logs",
    "log",
    "tmp",
    "temp",
    ".tmp",
    ".temp",
    # Documentation builds
    "_build",
    "docs/_build",
    "site",
    ".docusaurus",
    # Other common ignore patterns
    ".mypy_cache",
    ".tox",
    ".nox",
    ".coverage",
    "htmlcov",
    ".nyc_output",
    "coverage",
    ".sass-cache",
    ".parcel-cache",
    ".next",
    ".nuxt",
}

DEFAULT_IGNORE_FILES = {
    # Compiled files
    "*.pyc",
    "*.pyo",
    "*.pyd",
    "*.class",
    "*.dll",
    "*.exe",
    "*.o",
    "*.a",
    "*.lib",
    "*.so",
    # Archives
    "*.zip",
    "*.tar",
    "*.tar.gz",
    "*.rar",
    "*.7z",
    # Images (usually not searched)
    "*.jpg",
    "*.jpeg",
    "*.png",
    "*.gif",
    "*.bmp",
    "*.ico",
    "*.svg",
    "*.webp",
    # Videos and audio
    "*.mp4",
    "*.avi",
    "*.mov",
    "*.mp3",
    "*.wav",
    "*.flac",
    # Documents (can be large)
    "*.pdf",
    "*.doc",
    "*.docx",
    "*.xls",
    "*.xlsx",
    "*.ppt",
    "*.pptx",
    # Database files
    "*.db",
    "*.sqlite",
    "*.sqlite3",
    # Lock files
    "package-lock.json",
    "yarn.lock",
    "Pipfile.lock",
    "poetry.lock",
    # Other
    "*.min.js",
    "*.min.css",
    ".gitignore",
    ".gitkeep",
}


def get_all_config() -> Dict[str, Any]:
    """Return all configuration as a dictionary"""
    return {
        "model": {
            "name": MODEL_NAME,
            "temperature": MODEL_TEMPERATURE,
        },
        "memory": {
            "window_size": MEMORY_WINDOW_SIZE,
        },
        "email": {
            "smtp_server": SMTP_SERVER,
            "smtp_port": SMTP_PORT,
            "use_tls": EMAIL_USE_TLS,
            "use_ssl": EMAIL_USE_SSL,
            "timeout": EMAIL_TIMEOUT,
            "default_sender": EMAIL_DEFAULT_SENDER,
            "password": EMAIL_PASSWORD,
        },
        "web": {
            "user_agent": WEB_USER_AGENT,
            "content_limit": WEB_CONTENT_LIMIT,
            "links_limit": WEB_LINKS_LIMIT,
            "timeout": WEB_REQUEST_TIMEOUT,
        },
        "system": {
            "command_timeout": COMMAND_TIMEOUT,
            "dangerous_commands": DANGEROUS_COMMANDS,
        },
        "network": {
            "ping_count": PING_COUNT,
            "download_chunk_size": DOWNLOAD_CHUNK_SIZE,
            "download_timeout": DOWNLOAD_TIMEOUT,
        },
        "file": {
            "ignore_dirs": DEFAULT_IGNORE_DIRS,
            "ignore_files": DEFAULT_IGNORE_FILES,
        },
        "agent": {
            "name": AGENT_NAME,
            "max_iterations": AGENT_MAX_ITERATIONS,
            "max_execution_time": AGENT_MAX_EXECUTION_TIME,
        },
    }
