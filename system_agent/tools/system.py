import os
import platform
import subprocess
from typing import List

import psutil
from langchain.tools import StructuredTool

from system_agent.config import COMMAND_TIMEOUT, DANGEROUS_COMMANDS


class SystemManager:
    """Handles system-level operations"""

    @staticmethod
    def execute_command(
        command: str,
        timeout_seconds: int = COMMAND_TIMEOUT,
        shell: bool = True,
        cwd: str = ".",
    ) -> str:
        """Execute a shell command and return its output.

        Args:
            command: The shell command to execute
            timeout_seconds: Maximum execution time in seconds
            shell: Whether to use shell execution
            cwd: Working directory for command execution

        Returns:
            str: The command output including stdout, stderr, and return code
        """
        """Execute shell/system commands safely"""
        try:
            if any(dangerous in command.lower() for dangerous in DANGEROUS_COMMANDS):
                return "Error: Dangerous command blocked for security reasons"

            result = subprocess.run(
                command,
                shell=shell,
                capture_output=True,
                text=True,
                timeout=timeout_seconds,
                cwd=cwd,
            )

            output = ""
            if result.stdout:
                output += f"Output:\n{result.stdout}\n"
            if result.stderr:
                output += f"Error:\n{result.stderr}\n"

            output += f"Return code: {result.returncode}"
            return output

        except subprocess.TimeoutExpired:
            return "Error: Command timed out"
        except Exception as e:
            return f"Error executing command: {str(e)}"

    @staticmethod
    def get_system_info() -> str:
        """Get system information"""
        try:
            info = "=== SYSTEM INFORMATION ===\n"
            info += f"OS: {platform.system()}\n"
            info += f"OS Version: {platform.release()}\n"
            info += f"Hostname: {platform.node()}\n"
            info += f"Python Version: {platform.python_version()}\n"
            info += f"CPU: {platform.processor()}\n"
            info += f"System Architecture: {platform.machine()}\n"
            info += f"Current User: {os.getlogin()}\n"

            return info
        except Exception as e:
            return f"Error getting system info: {str(e)}"

    @staticmethod
    def list_processes() -> str:
        """Get a list of running processes"""
        try:
            processes = []
            for proc in psutil.process_iter(
                ["pid", "name", "status", "username", "memory_percent", "cpu_percent"]
            ):
                try:
                    processes.append(proc.info)
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass

            result = "Running Processes:\n"
            for proc in processes:
                result += f"PID: {proc['pid']}, Name: {proc['name']}, Status: {proc['status']}, Username: {proc['username']}, Memory: {proc.get('memory_percent', 0):.1f}%, CPU: {proc.get('cpu_percent', 0):.1f}%\n"  # noqa

            return result
        except Exception as e:
            return f"Error getting processes: {str(e)}"

    @staticmethod
    def get_disk_usage(path: str = "/") -> str:
        """Get disk usage information"""
        try:
            disk = psutil.disk_usage(path)

            result = f"Disk Usage for {path}:\n"
            result += f"Total Space: {disk.total // (1024**3):.1f}GB\n"
            result += f"Used Space: {disk.used // (1024**3):.1f}GB\n"
            result += f"Free Space: {disk.free // (1024**3):.1f}GB\n"
            result += f"Usage Percentage: {disk.percent:.1f}%\n"

            return result
        except Exception as e:
            return f"Error getting disk usage: {str(e)}"

    @staticmethod
    def get_memory_usage() -> str:
        """Get detailed memory usage information"""
        try:
            result = "Memory Information:\n"

            # Try to get basic memory info using psutil
            try:
                memory = psutil.virtual_memory()
                result += "\nPhysical Memory:\n"
                result += f"  Total: {memory.total // (1024**3):.1f}GB\n"
                result += f"  Available: {memory.available // (1024**3):.1f}GB\n"
                result += f"  Used: {memory.used // (1024**3):.1f}GB\n"
                if hasattr(memory, "percent"):
                    result += f"  Usage: {memory.percent}%\n"
            except Exception as e:
                result += (
                    "\n[!] Could not retrieve detailed physical memory information\n"
                )
                result += f"[!] Error: {str(e)}\n"

            # Try to get swap memory info
            try:
                swap = psutil.swap_memory()
                result += "\nSwap Memory:\n"
                result += f"  Total: {swap.total // (1024**3):.1f}GB\n"
                result += f"  Used: {swap.used // (1024**3):.1f}GB\n"
                result += f"  Free: {swap.free // (1024**3):.1f}GB\n"
                if hasattr(swap, "percent"):
                    result += f"  Usage: {swap.percent}%\n"
            except Exception as e:
                result += "\n[!] Could not retrieve swap memory information\n"
                result += f"[!] Error: {str(e)}\n"

            # Add a note about performance counters if needed
            if "PdhAddEnglishCounterW" in result:
                result += "\nNote: Some metrics may be limited due to Windows Performance Counters being disabled.\n"  # noqa
                result += (
                    "To enable them, run the following command as Administrator:\n"
                )
                result += "  lodctr /r\n"
                result += "  winmgmt /resetrepository\n"

            return result

        except Exception as e:
            # Fallback to basic memory info if everything else fails
            try:
                import ctypes

                kernel32 = ctypes.windll.kernel32

                class MEMORYSTATUSEX(ctypes.Structure):
                    _fields_ = [
                        ("dwLength", ctypes.c_ulong),
                        ("dwMemoryLoad", ctypes.c_ulong),
                        ("ullTotalPhys", ctypes.c_ulonglong),
                        ("ullAvailPhys", ctypes.c_ulonglong),
                        ("ullTotalPageFile", ctypes.c_ulonglong),
                        ("ullAvailPageFile", ctypes.c_ulonglong),
                        ("ullTotalVirtual", ctypes.c_ulonglong),
                        ("ullAvailVirtual", ctypes.c_ulonglong),
                        ("sullAvailExtendedVirtual", ctypes.c_ulonglong),
                    ]

                memory_status = MEMORYSTATUSEX()
                memory_status.dwLength = ctypes.sizeof(MEMORYSTATUSEX)
                kernel32.GlobalMemoryStatusEx(ctypes.byref(memory_status))

                result = "Memory Information (Basic):\n"
                result += f"  Memory Load: {memory_status.dwMemoryLoad}%\n"
                result += f"  Total Physical: {memory_status.ullTotalPhys // (1024**3):.1f}GB\n"
                result += f"  Available Physical: {memory_status.ullAvailPhys // (1024**3):.1f}GB\n"
                result += f"  Total Page File: {memory_status.ullTotalPageFile // (1024**3):.1f}GB\n"  # noqa
                result += f"  Available Page File: {memory_status.ullAvailPageFile // (1024**3):.1f}GB\n"  # noqa
                result += "\nNote: Some metrics are not available due to system limitations.\n"  # noqa
                result += "To enable full memory monitoring, ensure Windows Performance Counters are enabled.\n"  # noqa
                return result

            except Exception as inner_e:
                return f"Error getting memory usage: {str(e)}\nAlso failed to get basic memory info: {str(inner_e)}"  # noqa

    @staticmethod
    def get_network_info() -> str:
        """Get network interface information"""
        try:
            net_if_addrs = psutil.net_if_addrs()
            net_io = psutil.net_io_counters(pernic=True)
            net_if_stats = psutil.net_if_stats()

            result = "Network Interfaces:\n"
            for interface_name, interface_addresses in net_if_addrs.items():
                # Skip loopback interfaces
                if interface_name == "lo" or interface_name.startswith("Loopback"):
                    continue

                result += f"\nInterface: {interface_name}\n"
                result += "-" * (len(interface_name) + 11) + "\n"

                # Get interface statistics
                stats = net_if_stats.get(interface_name, None)
                if stats:
                    result += f"  Status: {'Up' if stats.isup else 'Down'}\n"
                    result += f"  Speed: {stats.speed}Mbps\n"
                # Get interface addresses
                for address in interface_addresses:
                    if address.family == psutil.AF_LINK:
                        result += f"  MAC Address: {address.address}\n"
                    elif address.family == 2:  # AF_INET
                        result += f"  IPv4 Address: {address.address}\n"
                        if address.netmask:
                            result += f"  IPv4 Netmask: {address.netmask}\n"
                        if address.broadcast:
                            result += f"  IPv4 Broadcast: {address.broadcast}\n"
                    elif address.family == 30:  # AF_INET6
                        result += f"  IPv6 Address: {address.address}\n"
                        if address.netmask:
                            result += f"  IPv6 Netmask: {address.netmask}\n"
                # Get I/O statistics
                io = net_io.get(interface_name)
                if io:
                    result += "\n  Network I/O Statistics:\n"
                    result += f"  - Bytes Sent: {io.bytes_sent / (1024**2):.2f} MB\n"
                    result += (
                        f"  - Bytes Received: {io.bytes_recv / (1024**2):.2f} MB\n"
                    )
                    result += f"  - Packets Sent: {io.packets_sent:,}\n"
                    result += f"  - Packets Received: {io.packets_recv:,}\n"
            return result
        except Exception as e:
            return f"Error getting network info: {str(e)}"

    def get_tools(self) -> List[StructuredTool]:
        """Return a list of StructuredTool objects for system operations."""
        return [
            StructuredTool.from_function(
                name="execute_command",
                func=self.execute_command,
                args_schema={
                    "command": {"type": "string", "description": "Command to execute"},
                    "timeout_seconds": {
                        "type": "integer",
                        "description": "Maximum execution time in seconds",
                        "default": 30,
                    },
                    "shell": {
                        "type": "boolean",
                        "description": "Whether to use shell execution",
                        "default": True,
                    },
                    "cwd": {
                        "type": "string",
                        "description": "Working directory for command execution",
                        "default": ".",
                    },
                },
                description="""Execute a system command and return the output.
                Example:
                {
                    "command": "ls -la",
                    "timeout_seconds": 30,
                    "shell": true,
                    "cwd": "/path/to/directory"
                }""",
            ),
            StructuredTool.from_function(
                name="get_system_info",
                func=self.get_system_info,
                description="""Get detailed system information including:
                - OS name and version
                - Hostname
                - Python version
                - CPU information
                - System architecture
                - Current user""",
            ),
            StructuredTool.from_function(
                name="get_running_processes",
                func=lambda **kwargs: SystemManager.list_processes(),
                args_schema={},
                description="""Get list of running processes sorted by memory usage.
                No parameters needed.
                Returns a list of processes with their details:
                - PID
                - Name
                - Memory usage""",
            ),
            StructuredTool.from_function(
                name="get_disk_usage",
                func=lambda **kwargs: SystemManager.get_disk_usage(),
                args_schema={
                    "path": {
                        "type": "string",
                        "description": "Path to check disk usage for",
                        "default": "/",
                    }
                },
                description="""Get disk usage information for a specified path.
                Example:
                {
                    "path": "/"
                }""",
            ),
            StructuredTool.from_function(
                name="get_memory_usage",
                func=lambda **kwargs: SystemManager.get_memory_usage(),
                args_schema={},
                description="""Get detailed memory usage information.
                No parameters needed.
                Returns a list of processes with their details:
                - PID
                - Name
                - Memory usage""",
            ),
            StructuredTool.from_function(
                name="get_network_info",
                func=lambda **kwargs: SystemManager.get_network_info(),
                args_schema={},
                description="""Get network interface information.
                No parameters needed.
                Returns a list of processes with their details:
                - PID
                - Name
                - Memory usage""",
            ),
        ]
