import os
import subprocess

import requests

from system_agent.config import DOWNLOAD_CHUNK_SIZE, DOWNLOAD_TIMEOUT, PING_COUNT


class NetworkManager:
    """Handles network operations"""

    @staticmethod
    def ping_host(host: str) -> str:
        """Ping a host"""
        try:
            if os.name == "nt":
                result = subprocess.run(
                    ["ping", "-n", str(PING_COUNT), host],
                    capture_output=True,
                    text=True,
                )
            else:
                result = subprocess.run(
                    ["ping", "-c", str(PING_COUNT), host],
                    capture_output=True,
                    text=True,
                )

            return f"Ping results for {host}:\n{result.stdout}"
        except Exception as e:
            return f"Error pinging {host}: {str(e)}"

    @staticmethod
    def download_file(url: str, save_path: str) -> str:
        """Download file from URL"""
        try:
            response = requests.get(url, stream=True, timeout=DOWNLOAD_TIMEOUT)
            response.raise_for_status()

            with open(save_path, "wb") as f:
                for chunk in response.iter_content(chunk_size=DOWNLOAD_CHUNK_SIZE):
                    f.write(chunk)

            file_size = os.path.getsize(save_path)
            return f"File downloaded successfully: {save_path} ({file_size} bytes)"
        except Exception as e:
            return f"Error downloading file: {str(e)}"
