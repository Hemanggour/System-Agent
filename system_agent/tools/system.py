import os
import subprocess

import psutil

from system_agent.config import COMMAND_TIMEOUT, DANGEROUS_COMMANDS


class SystemManager:
    """Handles system-level operations"""

    @staticmethod
    def execute_command(command: str) -> str:
        """Execute shell/system commands safely"""
        try:
            if any(dangerous in command.lower() for dangerous in DANGEROUS_COMMANDS):
                return "Error: Dangerous command blocked for security reasons"

            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=COMMAND_TIMEOUT,
            )

            output = ""
            if result.stdout:
                output += f"Output:\n{result.stdout}\n"
            if result.stderr:
                output += f"Error:\n{result.stderr}\n"

            output += f"Return code: {result.returncode}"
            return output

        except subprocess.TimeoutExpired:
            return "Error: Command timed out (30 second limit)"
        except Exception as e:
            return f"Error executing command: {str(e)}"

    @staticmethod
    def get_system_info() -> str:
        """Get system information"""
        try:
            info = "=== SYSTEM INFORMATION ===\n"
            info += f"OS: {os.name}\n"

            if hasattr(os, "uname"):
                uname = os.uname()
                info += f"System: {uname.sysname}\n"
                info += f"Node: {uname.nodename}\n"
                info += f"Release: {uname.release}\n"

            info += f"CPU Count: {os.cpu_count()}\n"
            info += f"Current Directory: {os.getcwd()}\n"

            try:
                python_version = subprocess.check_output(
                    ["python", "--version"], text=True
                ).strip()
                info += f"Python Version: {python_version}\n"
            except Exception:
                info += "Python Version: Unable to determine\n"

            try:
                memory = psutil.virtual_memory()
                disk = psutil.disk_usage(".")

                info += f"RAM: {memory.used // (1024**3):.1f}GB / {memory.total // (1024**3):.1f}GB ({memory.percent:.1f}% used)\n"  # noqa
                info += f"Disk: {disk.used // (1024**3):.1f}GB / {disk.total // (1024**3):.1f}GB ({disk.percent:.1f}% used)\n"  # noqa
            except Exception:
                info += "Memory/Disk info: Unable to retrieve\n"

            return info
        except Exception as e:
            return f"Error getting system info: {str(e)}"

    @staticmethod
    def get_running_processes() -> str:
        """Get list of running processes"""
        try:
            processes = []
            for proc in psutil.process_iter(["pid", "name", "memory_percent"]):
                try:
                    processes.append(proc.info)
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass

            processes.sort(key=lambda x: x.get("memory_percent", 0), reverse=True)

            result = "Top 10 processes by memory usage:\n"
            for i, proc in enumerate(processes[:10]):
                result += f"{i+1}. PID: {proc['pid']}, Name: {proc['name']}, Memory: {proc.get('memory_percent', 0):.1f}%\n"  # noqa

            return result
        except Exception as e:
            return f"Error getting processes: {str(e)}"
