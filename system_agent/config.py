import os
from typing import Any, Dict

# Model Configuration
MODEL_NAME = os.getenv("MODEL_NAME", "gemini-2.5-flash-lite")
MODEL_TEMPERATURE = float(os.getenv("MODEL_TEMPERATURE", "0.7"))

# Memory Configuration
MEMORY_WINDOW_SIZE = int(os.getenv("MEMORY_WINDOW_SIZE", "20"))

# Email Configuration
SMTP_SERVER = os.getenv("SMTP_SERVER", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))

# Web Request Configuration
REQUEST_TIMEOUT = int(os.getenv("REQUEST_TIMEOUT", "30"))

# Command Execution Configuration
COMMAND_TIMEOUT = int(os.getenv("COMMAND_TIMEOUT", "30"))

# Agent Configuration
AGENT_MAX_ITERATIONS = int(os.getenv("AGENT_MAX_ITERATIONS", "15"))
AGENT_MAX_EXECUTION_TIME = int(os.getenv("AGENT_MAX_EXECUTION_TIME", "60"))

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
        },
        "timeouts": {
            "request": REQUEST_TIMEOUT,
            "command": COMMAND_TIMEOUT,
        },
        "agent": {
            "max_iterations": AGENT_MAX_ITERATIONS,
            "max_execution_time": AGENT_MAX_EXECUTION_TIME,
        },
    }
