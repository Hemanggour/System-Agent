from datetime import datetime
from typing import Any, Dict, List

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from langchain.tools import StructuredTool


class SchedulerManager:
    """Handles task scheduling"""

    scheduled_tasks = []
    scheduler = BackgroundScheduler()

    @staticmethod
    def schedule_task(
        task_name: str,
        cron_expression: str,
        task_type: str,
        message: str,
        function_name: str = "",
        args: List[Any] = [],
        kwargs: Dict[str, Any] = {},
    ) -> str:
        """Schedule a task"""
        try:
            task_info = {
                "name": task_name,
                "cron_expression": cron_expression,
                "task_type": task_type,
                "message": message,
                "function_name": function_name,
                "args": args,
                "kwargs": kwargs,
                "created": datetime.now().isoformat(),
            }

            SchedulerManager.scheduled_tasks.append(task_info)

            if task_type == "print":
                SchedulerManager.scheduler.add_job(
                    print, CronTrigger.from_crontab(cron_expression), args=[message]
                )
            elif task_type == "command":
                SchedulerManager.scheduler.add_job(
                    lambda: exec(message), CronTrigger.from_crontab(cron_expression)
                )
            elif task_type == "function":
                SchedulerManager.scheduler.add_job(
                    function_name,
                    CronTrigger.from_crontab(cron_expression),
                    args=args,
                    kwargs=kwargs,
                )

            SchedulerManager.scheduler.start()

            return f"Task '{task_name}' scheduled: {message} at {cron_expression}"
        except Exception as e:
            return f"Error scheduling task: {str(e)}"

    @staticmethod
    def list_scheduled_tasks() -> str:
        """List all scheduled tasks"""
        if not SchedulerManager.scheduled_tasks:
            return "No scheduled tasks found"

        result = "Scheduled tasks:\n"
        for i, task in enumerate(SchedulerManager.scheduled_tasks, 1):
            result += (
                f"{i}. {task['name']}: {task['message']} ({task['cron_expression']})\n"
            )

        return result

    @staticmethod
    def remove_scheduled_task(task_id: str) -> str:
        """Remove a scheduled task by its ID"""
        try:
            for task in SchedulerManager.scheduled_tasks:
                if task["name"] == task_id:
                    SchedulerManager.scheduled_tasks.remove(task)
                    return f"Task '{task_id}' removed"
            return f"Task '{task_id}' not found"
        except Exception as e:
            return f"Error removing task: {str(e)}"

    def get_tools(self) -> List[StructuredTool]:
        """Return a list of StructuredTool objects for scheduling operations."""
        return [
            StructuredTool.from_function(
                name="schedule_task",
                func=self.schedule_task,
                args_schema={
                    "task_name": {
                        "type": "string",
                        "description": "Unique name for the scheduled task",
                    },
                    "cron_expression": {
                        "type": "string",
                        "description": "Cron expression for scheduling (e.g., '0 2 * * *' for 2 AM daily)",  # noqa
                    },
                    "task_type": {
                        "type": "string",
                        "enum": ["print", "function", "command"],
                        "description": "Type of task to schedule",
                    },
                    "message": {
                        "type": "string",
                        "description": "Message to print or command to execute",
                    },
                    "function_name": {
                        "type": "string",
                        "description": "Name of function to call (for 'function' type)",
                        "default": "",
                    },
                    "args": {
                        "type": "array",
                        "items": {"type": "any"},
                        "description": "Arguments to pass to the function",
                        "default": [],
                    },
                    "kwargs": {
                        "type": "object",
                        "description": "Keyword arguments to pass to the function",
                        "default": {},
                    },
                },
                description="""Schedule a task to run at a specific time or interval.
                Example (print task):
                {
                    "task_name": "daily_reminder",
                    "cron_expression": "0 9 * * *",  # 9 AM daily
                    "task_type": "print",
                    "message": "Good morning! Don't forget your daily standup at 10 AM."
                }
                Example (command task):
                {
                    "task_name": "backup_database",
                    "cron_expression": "0 2 * * *",  # 2 AM daily
                    "task_type": "command",
                    "message": "pg_dump mydb > backup.sql"
                }
                Cron format: minute hour day_of_month month day_of_week
                Example: '0 2 * * *' runs at 2 AM every day""",
            ),
            StructuredTool.from_function(
                name="list_scheduled_tasks",
                func=self.list_scheduled_tasks,
                description="List all currently scheduled tasks with their IDs and next run times.",
            ),
            StructuredTool.from_function(
                name="remove_scheduled_task",
                func=self.remove_scheduled_task,
                args_schema={
                    "task_id": {
                        "type": "string",
                        "description": "ID of the task to remove",
                    }
                },
                description="""Remove a scheduled task by its ID.
                Example:
                {
                    "task_id": "backup_database"
                }
                Returns success message or error if task not found.""",
            ),
        ]
