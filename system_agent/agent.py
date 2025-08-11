from typing import List

from langchain.agents import AgentExecutor, create_tool_calling_agent
from langchain.memory import ConversationBufferWindowMemory
from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.schema import HumanMessage
from langchain.tools import Tool
from langchain_google_genai import ChatGoogleGenerativeAI

from system_agent.config import (
    AGENT_MAX_EXECUTION_TIME,
    AGENT_MAX_ITERATIONS,
    AGENT_NAME,
    MEMORY_WINDOW_SIZE,
    MODEL_NAME,
    MODEL_TEMPERATURE,
)
from system_agent.tools.archive import ArchiveManager
from system_agent.tools.database import DatabaseManager
from system_agent.tools.email import EmailManager
from system_agent.tools.file import FileManager
from system_agent.tools.network import NetworkManager
from system_agent.tools.scheduler import SchedulerManager
from system_agent.tools.security import SecurityManager
from system_agent.tools.system import SystemManager
from system_agent.tools.web_scraper import WebScraper


class AIAgent:
    """Main AI Agent class with LangChain and Google Gemini integration"""

    def __init__(self, model: str = MODEL_NAME):
        self.llm = ChatGoogleGenerativeAI(
            model=model,
            temperature=MODEL_TEMPERATURE,
        )

        # Initialize all managers
        self.file_manager = FileManager()
        self.web_scraper = WebScraper()
        self.system_manager = SystemManager()
        self.database_manager = DatabaseManager()
        self.email_manager = EmailManager()
        self.archive_manager = ArchiveManager()
        self.network_manager = NetworkManager()
        self.security_manager = SecurityManager()
        self.scheduler_manager = SchedulerManager()

        # Create tools
        self.tools = self._create_tools()

        # Create memory with configurable window size
        self.memory = ConversationBufferWindowMemory(
            k=MEMORY_WINDOW_SIZE, memory_key="chat_history", return_messages=True
        )

        # Create prompt template optimized for Gemini
        self.prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    f"""You are a helpful AI assistant powered by Google's Gemini model with access to various tools.
Your creator's name: Hemang Gour
Your name: {AGENT_NAME}

You can:
CAPABILITIES:
1. File Operations: Read, write, modify, delete files and manage directories
2. Web Operations: Scrape websites, extract links, download files
3. System Operations: Execute commands, monitor system resources
4. Database Operations: Execute SQLite queries and manage databases
5. Email Operations: Send emails with attachments
6. Archive Operations: Create and extract ZIP files
7. Network Operations: Ping hosts, download files
8. Security Operations: Calculate hashes, scan for duplicates
9. Task Scheduling: Schedule and manage automated tasks
10. Memory: Remember last 10 messages for context

INSTRUCTIONS:
- Use the available tools when needed to complete tasks
- Always provide clear, helpful, and detailed responses
- When working with files, specify full paths and handle errors gracefully
- When scraping websites, be respectful of rate limits and robots.txt
- Remember context from previous messages in our conversation
- Break down complex tasks into manageable steps
- For dangerous operations, ask for confirmation first

Available tools: read_file, write_file, append_to_file, delete_file, list_files, get_file_info, scrape_website, extract_links, download_file, execute_command, get_system_info, get_running_processes, execute_sqlite_query, send_email, create_zip_archive, extract_zip_archive, ping_host, calculate_file_hash, scan_directory_for_duplicates, schedule_task, list_scheduled_tasks""",  # noqa
                ),
                MessagesPlaceholder(variable_name="chat_history"),
                ("human", "{input}"),
                MessagesPlaceholder(variable_name="agent_scratchpad"),
            ]
        )

        # Create agent using tool calling
        self.agent = create_tool_calling_agent(
            llm=self.llm, tools=self.tools, prompt=self.prompt
        )

        # Create agent executor
        self.agent_executor = AgentExecutor(
            agent=self.agent,
            tools=self.tools,
            memory=self.memory,
            verbose=True,
            handle_parsing_errors=True,
            max_iterations=AGENT_MAX_ITERATIONS,
            max_execution_time=AGENT_MAX_EXECUTION_TIME,
        )

    def _create_tools(self) -> List[Tool]:
        """Create comprehensive tools for the agent"""
        tools = [
            # File Operations
            Tool(
                name="read_file",
                description="Read content from a file. Input: file_path (string). You can use relative paths from workspace root or absolute paths within workspace. Examples: 'notes.txt', 'docs/example.md'",  # noqa
                func=self.file_manager.read_file,
            ),
            Tool(
                name="write_file",
                description="Create a new file or overwrite existing file. Input format: 'file_path|||content' (separated by three pipes). Example: 'notes.txt|||Hello World'",  # noqa
                func=self._write_file_wrapper,
            ),
            Tool(
                name="append_to_file",
                description="Append content to an existing file. Input format: 'file_path|||content' (separated by three pipes). Example: 'log.txt|||New entry'",  # noqa
                func=self._append_file_wrapper,
            ),
            Tool(
                name="delete_file",
                description="Delete a file. Input: file_path (string). Example: 'old_file.txt'",
                func=self.file_manager.delete_file,
            ),
            Tool(
                name="list_files",
                description="List files in directory. Input: directory_path (string, use '.' for current). Example: '.'",  # noqa
                func=self.file_manager.list_files,
            ),
            Tool(
                name="get_file_info",
                description="Get file information. Input: file_path (string). Example: 'notes.txt'",
                func=self.file_manager.get_file_info,
            ),
            # Web Operations
            Tool(
                name="scrape_website",
                description="Scrape website content. Input: url (string). Example: 'https://example.com'",  # noqa
                func=self.web_scraper.scrape_url,
            ),
            Tool(
                name="extract_links",
                description="Extract links from webpage. Input: url (string). Example: 'https://example.com'",  # noqa
                func=self.web_scraper.extract_links,
            ),
            Tool(
                name="download_file",
                description="Download file from URL. Input format: 'url|||save_path' (separated by three pipes). Example: 'https://example.com/file.pdf|||file.pdf'",  # noqa
                func=self._download_file_wrapper,
            ),
            # System Operations
            Tool(
                name="execute_command",
                description="Execute shell command safely. Input: command (string). Example: 'ls -la'",  # noqa
                func=self.system_manager.execute_command,
            ),
            Tool(
                name="get_system_info",
                description="Get system information. No input required.",
                func=lambda x: self.system_manager.get_system_info(),
            ),
            Tool(
                name="get_running_processes",
                description="Get running processes. No input required.",
                func=lambda x: self.system_manager.get_running_processes(),
            ),
            # Database Operations
            Tool(
                name="execute_sqlite_query",
                description="Execute SQLite query. Input format: 'db_path|||query' (separated by three pipes). Example: 'test.db|||SELECT * FROM users'",  # noqa
                func=self._sqlite_query_wrapper,
            ),
            # Email Operations
            Tool(
                name="send_email",
                description="Send email. Input format: 'to_email|||subject|||body|||attachment_path' (attachment optional). Example: 'user@example.com|||Test|||Hello|||'",  # noqa
                func=self._send_email_wrapper,
            ),
            # Archive Operations
            Tool(
                name="create_zip_archive",
                description="Create ZIP archive. Input format: 'source_path|||archive_path' (separated by three pipes). Example: 'my_folder|||backup.zip'",  # noqa
                func=self._create_zip_wrapper,
            ),
            Tool(
                name="extract_zip_archive",
                description="Extract ZIP archive. Input format: 'archive_path|||extract_path' (separated by three pipes). Example: 'backup.zip|||./extracted'",  # noqa
                func=self._extract_zip_wrapper,
            ),
            # Network Operations
            Tool(
                name="ping_host",
                description="Ping a host. Input: hostname or IP address (string). Example: 'google.com'",  # noqa
                func=self.network_manager.ping_host,
            ),
            # Security Operations
            Tool(
                name="calculate_file_hash",
                description="Calculate file hash. Input format: 'file_path|||hash_type' (hash_type optional, defaults to md5). Example: 'file.txt|||sha256'",  # noqa
                func=self._calculate_hash_wrapper,
            ),
            Tool(
                name="scan_directory_for_duplicates",
                description="Scan directory for duplicate files. Input: directory_path (string). Example: './documents'",  # noqa
                func=self.security_manager.scan_directory_for_duplicates,
            ),
            # Task Scheduling
            Tool(
                name="schedule_task",
                description="Schedule a task. Input format: 'task_name|||command|||schedule_time' (separated by three pipes). Example: 'daily_backup|||cp file.txt backup.txt|||daily at 2pm'",  # noqa
                func=self._schedule_task_wrapper,
            ),
            Tool(
                name="list_scheduled_tasks",
                description="List all scheduled tasks. No input required.",
                func=lambda x: self.scheduler_manager.list_scheduled_tasks(),
            ),
        ]

        return tools

    # Wrapper functions for tools that need input parsing
    def _write_file_wrapper(self, input_str: str) -> str:
        """Wrapper for write_file tool"""
        try:
            parts = input_str.split("|||", 1)
            if len(parts) != 2:
                return "Error: Input format should be 'file_path|||content'"
            file_path, content = parts
            return self.file_manager.write_file(file_path, content)
        except Exception as e:
            return f"Error parsing input: {str(e)}"

    def _append_file_wrapper(self, input_str: str) -> str:
        """Wrapper for append_file tool"""
        try:
            parts = input_str.split("|||", 1)
            if len(parts) != 2:
                return "Error: Input format should be 'file_path|||content'"
            file_path, content = parts
            return self.file_manager.write_file(file_path, content, mode="a")
        except Exception as e:
            return f"Error parsing input: {str(e)}"

    def _download_file_wrapper(self, input_str: str) -> str:
        """Wrapper for download_file tool"""
        try:
            parts = input_str.split("|||", 1)
            if len(parts) != 2:
                return "Error: Input format should be 'url|||save_path'"
            url, save_path = parts
            return self.network_manager.download_file(url, save_path)
        except Exception as e:
            return f"Error parsing input: {str(e)}"

    def _sqlite_query_wrapper(self, input_str: str) -> str:
        """Wrapper for sqlite_query tool"""
        try:
            parts = input_str.split("|||", 1)
            if len(parts) != 2:
                return "Error: Input format should be 'db_path|||query'"
            db_path, query = parts
            return self.database_manager.execute_sqlite_query(db_path, query)
        except Exception as e:
            return f"Error parsing input: {str(e)}"

    def _send_email_wrapper(self, input_str: str) -> str:
        """Wrapper for send_email tool"""
        try:
            parts = input_str.split("|||")
            if len(parts) < 3:
                return "Error: Input format should be 'to_email|||subject|||body|||attachment_path' (attachment optional)"  # noqa

            to_email, subject, body = parts[:3]
            attachment_path = parts[3] if len(parts) > 3 and parts[3].strip() else None

            return self.email_manager.send_email(
                to_email, subject, body, attachment_path
            )
        except Exception as e:
            return f"Error parsing input: {str(e)}"

    def _create_zip_wrapper(self, input_str: str) -> str:
        """Wrapper for create_zip_archive tool"""
        try:
            parts = input_str.split("|||", 1)
            if len(parts) != 2:
                return "Error: Input format should be 'source_path|||archive_path'"
            source_path, archive_path = parts
            return self.archive_manager.create_zip_archive(source_path, archive_path)
        except Exception as e:
            return f"Error parsing input: {str(e)}"

    def _extract_zip_wrapper(self, input_str: str) -> str:
        """Wrapper for extract_zip_archive tool"""
        try:
            parts = input_str.split("|||", 1)
            if len(parts) != 2:
                return "Error: Input format should be 'archive_path|||extract_path'"
            archive_path, extract_path = parts
            return self.archive_manager.extract_zip_archive(archive_path, extract_path)
        except Exception as e:
            return f"Error parsing input: {str(e)}"

    def _calculate_hash_wrapper(self, input_str: str) -> str:
        """Wrapper for calculate_file_hash tool"""
        try:
            parts = input_str.split("|||")
            file_path = parts[0]
            hash_type = parts[1] if len(parts) > 1 else "md5"
            return self.security_manager.calculate_file_hash(file_path, hash_type)
        except Exception as e:
            return f"Error parsing input: {str(e)}"

    def _schedule_task_wrapper(self, input_str: str) -> str:
        """Wrapper for schedule_task tool"""
        try:
            parts = input_str.split("|||")
            if len(parts) != 3:
                return "Error: Input format should be 'task_name|||command|||schedule_time'"
            task_name, command, schedule_time = parts
            return self.scheduler_manager.schedule_task(
                task_name, command, schedule_time
            )
        except Exception as e:
            return f"Error parsing input: {str(e)}"

    def run(self, user_input: str) -> str:
        """Run the agent with user input"""
        try:
            response = self.agent_executor.invoke({"input": user_input})
            return response["output"]

        except Exception as e:
            error_msg = str(e)
            if "Rate limit" in error_msg:
                return "Rate limit exceeded. Please wait a moment before trying again."
            elif "No such file" in error_msg or "FileNotFoundError" in error_msg:
                return "The specified file could not be found. Please check if the file exists and the path is correct."
            elif "Permission" in error_msg:
                return "Access denied. I don't have permission to access this file or directory."
            else:
                return f"Error processing request: {error_msg}"

    def get_memory_summary(self) -> str:
        """Get a summary of the conversation memory"""
        messages = self.memory.chat_memory.messages
        if not messages:
            return "No conversation history yet."

        summary = f"Conversation history ({len(messages)} messages, showing last 10):\n"
        summary += "=" * 50 + "\n"

        for i, msg in enumerate(messages[-10:], 1):  # Show last 10 messages
            role = "👤 You" if isinstance(msg, HumanMessage) else "🤖 AI Assistant"
            content = (
                msg.content[:150] + "..." if len(msg.content) > 150 else msg.content
            )
            summary += f"{i}. {role}: {content}\n\n"

        return summary

    def clear_memory(self) -> str:
        """Clear conversation memory"""
        self.memory.clear()
        return "Conversation memory cleared successfully"
