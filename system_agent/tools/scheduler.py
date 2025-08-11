from datetime import datetime


class SchedulerManager:
    """Handles task scheduling"""

    scheduled_tasks = []

    @staticmethod
    def schedule_task(task_name: str, command: str, schedule_time: str) -> str:
        """Schedule a task (basic implementation)"""
        try:
            task_info = {
                "name": task_name,
                "command": command,
                "schedule": schedule_time,
                "created": datetime.now().isoformat(),
            }

            SchedulerManager.scheduled_tasks.append(task_info)
            return f"Task '{task_name}' scheduled: {command} at {schedule_time}"
        except Exception as e:
            return f"Error scheduling task: {str(e)}"

    @staticmethod
    def list_scheduled_tasks() -> str:
        """List all scheduled tasks"""
        if not SchedulerManager.scheduled_tasks:
            return "No scheduled tasks found"

        result = "Scheduled tasks:\n"
        for i, task in enumerate(SchedulerManager.scheduled_tasks, 1):
            result += f"{i}. {task['name']}: {task['command']} ({task['schedule']})\n"

        return result
