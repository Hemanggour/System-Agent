import os
import platform
import subprocess
from typing import List

import requests
from langchain.tools import StructuredTool

from system_agent.config import (
    DOWNLOAD_CHUNK_SIZE,
    DOWNLOAD_TIMEOUT,
    PING_COUNT,
    WEB_REQUEST_TIMEOUT,
    WEB_USER_AGENT,
)


class NetworkManager:
    """Handles network operations"""

    @staticmethod
    def ping_host(host: str) -> str:
        """Ping a host to check network connectivity.

        Args:
            host: Hostname or IP address to ping

        Returns:
            str: Ping results or error message
        """
        try:
            if not host or not isinstance(host, str):
                return "Error: Invalid host specified"

            # Sanitize host input to prevent command injection
            if any(char in host for char in [";", "&", "|", "`", "$", ">", "<"]):
                return "Error: Invalid characters in hostname"

            # Choose the correct ping command based on the OS
            param = "-n" if platform.system().lower() == "windows" else "-c"

            # Build the ping command
            command = ["ping", param, str(PING_COUNT), host]

            # Run the ping command with timeout from config or default
            timeout = int(WEB_REQUEST_TIMEOUT)
            result = subprocess.run(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=timeout,
            )

            if result.returncode == 0:
                # Extract summary from ping output
                output = result.stdout.strip()
                summary = "\n".join(
                    line for line in output.split("\n")[-3:] if line.strip()
                )
                return f" Ping to {host} successful\n{summary}"
            else:
                error_msg = result.stderr or result.stdout
                if (
                    "Name or service not known" in error_msg
                    or "could not find host" in error_msg.lower()
                ):
                    return f" Host '{host}' not found or unreachable"
                return f" Ping to {host} failed\n{error_msg}"

        except subprocess.TimeoutExpired:
            return f" Ping to {host} timed out after {timeout} seconds"
        except Exception as e:
            return f" Error pinging {host}: {str(e)}"

    @staticmethod
    def download_file(url: str, save_path: str) -> str:
        """Download file from URL"""
        try:
            headers = {"User-Agent": WEB_USER_AGENT}
            timeout = DOWNLOAD_TIMEOUT

            response = requests.get(url, stream=True, timeout=timeout, headers=headers)
            response.raise_for_status()

            # Get total file size for progress tracking
            total_size = int(response.headers.get("content-length", 0))
            downloaded_size = 0

            os.makedirs(os.path.dirname(save_path), exist_ok=True)

            with open(save_path, "wb") as f:
                for chunk in response.iter_content(chunk_size=DOWNLOAD_CHUNK_SIZE):
                    if chunk:  # filter out keep-alive chunks
                        f.write(chunk)
                        downloaded_size += len(chunk)
                        # Show progress if total size is known
                        if total_size > 0:
                            progress = (downloaded_size / total_size) * 100
                            print(f"\rDownloading... {progress:.1f}%", end="")

            file_size = os.path.getsize(save_path)
            file_size_mb = file_size / (1024 * 1024)
            return (
                f"File downloaded successfully!\n"
                f"Path: {save_path}\n"
                f"Size: {file_size_mb:.2f} MB"
            )
        except Exception as e:
            return f"Error downloading file: {str(e)}"

    def get_tools(self) -> List[StructuredTool]:
        """Return a list of StructuredTool objects for network operations."""
        return [
            StructuredTool.from_function(
                name="ping_host",
                func=self.ping_host,
                args_schema={
                    "host": {
                        "type": "string",
                        "description": "Hostname or IP address to ping",
                    }
                },
                description="""Ping a host to check network connectivity.
                Example:
                {
                    "host": "google.com"
                }
                Returns detailed ping statistics including:
                - Packet loss percentage
                - Round-trip time (min/avg/max)
                - Connection status""",
            ),
            StructuredTool.from_function(
                name="download_file",
                func=self.download_file,
                args_schema={
                    "url": {
                        "type": "string",
                        "description": "URL of the file to download (must include http:// or https://)",  # noqa
                    },
                    "save_path": {
                        "type": "string",
                        "description": "Local filesystem path where to save the downloaded file",
                    },
                },
                description="""Download a file from a URL to the local filesystem.
                Example:
                {
                    "url": "https://example.com/file.txt",
                    "save_path": "./downloads/example.txt"
                }""",
            ),
        ]
