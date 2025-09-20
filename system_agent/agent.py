import json
import os
from typing import List

from langchain.agents import AgentExecutor, create_tool_calling_agent
from langchain.memory import ConversationBufferWindowMemory
from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.schema import HumanMessage
from langchain.tools import Tool

from system_agent.config import (
    AGENT_MAX_EXECUTION_TIME,
    AGENT_MAX_ITERATIONS,
    AGENT_NAME,
    DEFAULT_MODEL_CONFIG,
    DISABLE_SMART_IGNORE,
    MEMORY_WINDOW_SIZE,
    VERBOSE,
)
from system_agent.gen_ai import load_model
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
    """
    Main AI Agent class with LangChain integration.

    This agent wraps around LangChain-compatible chat models (`BaseChatModel`)
    and provides a unified interface for system control and task execution.

    Args:
        model (str, optional): Model in the format "provider:modelName"
            (e.g., "gemini:gemini-2.0-flash", "openai:gpt-4o-mini").
            If not provided and no `llm` is given, defaults to the value
            defined in `DEFAULT_MODEL_CONFIG`.
        llm (BaseChatModel, optional): An existing LangChain `BaseChatModel`
            instance. If provided, this takes priority over `model`.
        model_kwargs (dict, optional): Extra keyword arguments for model
            configuration (e.g., `temperature`, `max_tokens`). If not provided
            when using `model`, the defaults from `DEFAULT_MODEL_CONFIG["config"]`
            are applied.

    Supported Models:
        - Only text-based chat models are supported for now.
        - Must be instances of LangChain's `BaseChatModel`.

    Environment Variables:
        These must be set in your `.env` file or environment for authentication.
        - `OPENAI_API_KEY`      → Required for OpenAI models
        - `GOOGLE_API_KEY`      → Required for Gemini models
        - `ANTHROPIC_API_KEY`   → Required for Anthropic models

        Additional optional fields (e.g., for email integration or advanced tools)
        are documented in the `.env.example` file. Users can remove or change
        default values as needed.

    Examples:
        Using a provider + model name with extra kwargs:
        ```python
        agent = AIAgent(model="openai:gpt-4o-mini", temperature=0.3)
        response = agent.run("Summarize the benefits of LangChain.")
        print(response)
        ```

        Using a pre-configured LangChain model instance:
        ```python
        from langchain_ollama import ChatOllama

        # Use any ollama model you have pulled, e.g., "llama3", "mistral", "gemma"
        llm = ChatOllama(model="llama3", temperature=0.2)

        agent = AIAgent(llm=llm)
        response = agent.run("Explain system AI agents in simple terms.")
        print(response)

        ```
    """

    def __init__(self, model: str = None, llm: object = None, **model_kwargs):
        if llm:
            self.llm = llm

        elif model:
            if not model_kwargs:
                model_kwargs = DEFAULT_MODEL_CONFIG.get("config")
            self.llm = load_model(model, **model_kwargs)

        else:
            self.llm = load_model(
                model=DEFAULT_MODEL_CONFIG.get("model"),
                model_kwargs=DEFAULT_MODEL_CONFIG.get("config"),
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
        self.tools = self.__create_tools()

        # Create memory with configurable window size
        self.memory = ConversationBufferWindowMemory(
            k=MEMORY_WINDOW_SIZE, memory_key="chat_history", return_messages=True
        )

        self.prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    f"""You are a helpful AI assistant with access to various tools.
You are build by: Hemang Gour
Your name: {AGENT_NAME}

INSTRUCTIONS:
- If any task given then first create a proper flow plan of that task.
- Always extract all information returned from tools results.
- If any instructions are unclear ask the user before proceed.
- Use the available tools when needed to complete tasks
- Always provide clear, helpful, and detailed responses
- When working with files, specify full paths and handle errors gracefully
- When scraping websites, be respectful of rate limits and robots.txt
- Remember context from previous messages in our conversation
- Break down complex tasks into manageable steps
- For dangerous operations, ask for confirmation first""",  # noqa
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
            verbose=VERBOSE,
            handle_parsing_errors=True,
            max_iterations=AGENT_MAX_ITERATIONS,
            max_execution_time=AGENT_MAX_EXECUTION_TIME,
        )

    def __create_tools(self) -> List[Tool]:
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
                func=self.__write_file_wrapper,
            ),
            Tool(
                name="append_to_file",
                description="Append content to an existing file. Input format: 'file_path|||content' (separated by three pipes). Example: 'log.txt|||New entry'",  # noqa
                func=self.__append_file_wrapper,
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
                func=self.__download_file_wrapper,
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
                func=self.__sqlite_query_wrapper,
            ),
            # Email Operations
            Tool(
                name="send_email",
                description="Send email. Input format: 'to_email|||subject|||body|||attachment_path' (attachment optional). Example: 'user@example.com|||Test|||Hello|||'",  # noqa
                func=self.__send_email_wrapper,
            ),
            # Archive Operations
            Tool(
                name="create_zip_archive",
                description="Create ZIP archive. Input format: 'source_path|||archive_path' (separated by three pipes). Example: 'my_folder|||backup.zip'",  # noqa
                func=self.__create_zip_wrapper,
            ),
            Tool(
                name="extract_zip_archive",
                description="Extract ZIP archive. Input format: 'archive_path|||extract_path' (separated by three pipes). Example: 'backup.zip|||./extracted'",  # noqa
                func=self.__extract_zip_wrapper,
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
                func=self.__calculate_hash_wrapper,
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
                func=self.__schedule_task_wrapper,
            ),
            Tool(
                name="list_scheduled_tasks",
                description="List all scheduled tasks. No input required.",
                func=lambda x: self.scheduler_manager.list_scheduled_tasks(),
            ),
            Tool(
                name="search_string_in_files",
                description="""Usage: Search fir string in files and directories and gives the `file path`, `line number` and `content`

Input format: 'search_string|||directory|||options_json'
- search_string: The string to search for (required)
- directory: Directory to search in (optional, defaults to current directory)
- options_json: JSON string with search options (optional)

Options JSON can contain:
- file_pattern: File pattern to match (default: "*")
- ignore_case: Case-insensitive search (default: true)
- custom_ignore_patterns: List of additional patterns to ignore (default: [])
- additional_ignore_dirs: List of additional directory names to ignore (default: [])
- additional_ignore_files: List of additional file patterns to ignore (default: [])

Examples:
- "function"
- "TODO|||/path/to/project"
- "error|||/logs|||{\"file_pattern\": \"*.log\", \"ignore_case\": false}\"""",  # noqa
                func=self.__search_string_in_files_wrapper,
            ),
            Tool(
                name="duckduckgo_search",
                description="Search the web using DuckDuckGo for real-time information.",
                func=self.web_scraper.duckduckgo_search,
            ),
        ]

        return tools

    def __search_string_in_files_wrapper(self, input_str: str) -> str:
        """
        Wrapper for search_string_in_files function to work as an AI agent tool.
        Uses the same format as print_search_results for consistent LLM-friendly output.
        Now includes smart filtering to automatically ignore common unwanted directories and files.

        Input format: 'search_string|||directory|||options_json'
        - search_string: The string to search for (required)
        - directory: Directory to search in (optional, defaults to current directory)
        - options_json: JSON string with search options (optional)

        Options JSON can contain:
        - file_pattern: File pattern to match (default: "*")
        - ignore_case: Case-insensitive search (default: true)
        - max_workers: Number of parallel threads (default: 4)
        - max_file_size_mb: Skip files larger than this MB (default: 100)
        - max_results: Maximum results to return (default: 50)
        - use_memory_mapping: Use memory mapping (default: true)
        - disable_smart_ignore: Disable automatic ignore patterns (default: false)
        - custom_ignore_patterns: List of additional patterns to ignore (default: [])
        - additional_ignore_dirs: List of additional directory names to ignore (default: [])
        - additional_ignore_files: List of additional file patterns to ignore (default: [])

        Examples:
        - "function"
        - "TODO|||/path/to/project"
        - "error|||/logs|||{\"file_pattern\": \"*.log\", \"ignore_case\": false}"
        - "test|||.|||{\"custom_ignore_patterns\": [\"*backup*\", \"*.tmp\"], \"disable_smart_ignore\": false}"
        - "import|||src|||{\"additional_ignore_dirs\": [\"deprecated\", \"old\"], \"file_pattern\": \"*.py\"}"
        """  # noqa
        try:
            # Parse input
            parts = input_str.split("|||")

            if len(parts) < 1 or not parts[0].strip():
                return "Error: Search string is required"

            search_string = parts[0].strip()
            directory = (
                parts[1].strip() if len(parts) > 1 and parts[1].strip() else None
            )
            options_str = (
                parts[2].strip() if len(parts) > 2 and parts[2].strip() else "{}"
            )

            # Parse options
            try:
                options = json.loads(options_str)
            except json.JSONDecodeError as e:
                return f"Error: Invalid JSON in options: {str(e)}"

            # Set default options
            search_options = {
                "file_pattern": options.get("file_pattern", "*"),
                "ignore_case": options.get("ignore_case", True),
                "max_workers": options.get("max_workers", 4),
                "max_file_size_mb": options.get("max_file_size_mb", 100),
                "use_memory_mapping": options.get("use_memory_mapping", True),
                "disable_smart_ignore": options.get(
                    "disable_smart_ignore", DISABLE_SMART_IGNORE
                ),
                "custom_ignore_patterns": options.get("custom_ignore_patterns", []),
                "additional_ignore_dirs": options.get("additional_ignore_dirs", []),
                "additional_ignore_files": options.get("additional_ignore_files", []),
            }

            max_results = options.get("max_results", 50)

            # Validate directory
            if directory and not os.path.exists(directory):
                return f"Error: Directory '{directory}' does not exist"

            # Validate max_workers
            if (
                not isinstance(search_options["max_workers"], int)
                or search_options["max_workers"] < 1
            ):
                search_options["max_workers"] = 4

            # Validate ignore pattern lists
            for key in [
                "custom_ignore_patterns",
                "additional_ignore_dirs",
                "additional_ignore_files",
            ]:
                if not isinstance(search_options[key], list):
                    search_options[key] = []

            # Perform search with new filtering parameters
            results = self.file_manager.search_string_in_files(
                search_string=search_string, directory=directory, **search_options
            )

            # Handle empty results
            if not results:
                filter_info = ""
                if not search_options["disable_smart_ignore"]:
                    filter_info = " (smart filtering enabled - ignored common dirs like venv, node_modules, .git)"  # noqa
                return (
                    f"No matches found for '{search_string}'"
                    + (f" in directory '{directory}'" if directory else "")
                    + filter_info
                )

            # Limit results if needed
            original_count = len(results)
            if len(results) > max_results:
                results = results[:max_results]
                truncated = True
            else:
                truncated = False

            # Format results using print_search_results format
            output_lines = []

            # Header with count and filtering info
            header = f"Found {original_count} matches"
            if not search_options["disable_smart_ignore"]:
                header += " (smart filtering enabled - ignored common dirs like venv, node_modules, .git)"  # noqa
            header += ":"

            output_lines.append(header)
            output_lines.append("-" * 50)

            # Results in print_search_results format
            for result in results:
                # File path with line number (same format as print_search_results)
                file_info = result["relative_path"]
                if result.get("line_number"):
                    file_info += f"\n- line no.: {result['line_number']}"

                # File info line
                output_lines.append(file_info)

                # Content line with indentation (same as print_search_results)
                output_lines.append(f"- {result['line_content']}")

                # Empty line for readability (same as print_search_results)
                output_lines.append("")

            # Add truncation notice if needed
            if truncated:
                output_lines.append(
                    f"... and {original_count - max_results} more matches"
                )

            # Add filtering summary if custom patterns were used
            if (
                search_options["custom_ignore_patterns"]
                or search_options["additional_ignore_dirs"]
                or search_options["additional_ignore_files"]
            ):

                filter_summary = []
                if search_options["custom_ignore_patterns"]:
                    filter_summary.append(
                        f"Custom ignore patterns: {search_options['custom_ignore_patterns']}"
                    )
                if search_options["additional_ignore_dirs"]:
                    filter_summary.append(
                        f"Additional ignored dirs: {search_options['additional_ignore_dirs']}"
                    )
                if search_options["additional_ignore_files"]:
                    filter_summary.append(
                        f"Additional ignored files: {search_options['additional_ignore_files']}"
                    )

                if filter_summary:
                    output_lines.append("")
                    output_lines.append("Filtering applied:")
                    for summary in filter_summary:
                        output_lines.append(f"  {summary}")

            return "\n".join(output_lines)

        except Exception as e:
            return f"Error during search: {str(e)}"

    # Wrapper functions for tools that need input parsing
    def __write_file_wrapper(self, input_str: str) -> str:
        """Wrapper for write_file tool"""
        try:
            parts = input_str.split("|||", 1)
            if len(parts) != 2:
                return "Error: Input format should be 'file_path|||content'"
            file_path, content = parts
            return self.file_manager.write_file(file_path, content)
        except Exception as e:
            return f"Error parsing input: {str(e)}"

    def __append_file_wrapper(self, input_str: str) -> str:
        """Wrapper for append_file tool"""
        try:
            parts = input_str.split("|||", 1)
            if len(parts) != 2:
                return "Error: Input format should be 'file_path|||content'"
            file_path, content = parts
            return self.file_manager.write_file(file_path, content, mode="a")
        except Exception as e:
            return f"Error parsing input: {str(e)}"

    def __download_file_wrapper(self, input_str: str) -> str:
        """Wrapper for download_file tool"""
        try:
            parts = input_str.split("|||", 1)
            if len(parts) != 2:
                return "Error: Input format should be 'url|||save_path'"
            url, save_path = parts
            return self.network_manager.download_file(url, save_path)
        except Exception as e:
            return f"Error parsing input: {str(e)}"

    def __sqlite_query_wrapper(self, input_str: str) -> str:
        """Wrapper for sqlite_query tool"""
        try:
            parts = input_str.split("|||", 1)
            if len(parts) != 2:
                return "Error: Input format should be 'db_path|||query'"
            db_path, query = parts
            return self.database_manager.execute_sqlite_query(db_path, query)
        except Exception as e:
            return f"Error parsing input: {str(e)}"

    def __send_email_wrapper(self, input_str: str) -> str:
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

    def __create_zip_wrapper(self, input_str: str) -> str:
        """Wrapper for create_zip_archive tool"""
        try:
            parts = input_str.split("|||", 1)
            if len(parts) != 2:
                return "Error: Input format should be 'source_path|||archive_path'"
            source_path, archive_path = parts
            return self.archive_manager.create_zip_archive(source_path, archive_path)
        except Exception as e:
            return f"Error parsing input: {str(e)}"

    def __extract_zip_wrapper(self, input_str: str) -> str:
        """Wrapper for extract_zip_archive tool"""
        try:
            parts = input_str.split("|||", 1)
            if len(parts) != 2:
                return "Error: Input format should be 'archive_path|||extract_path'"
            archive_path, extract_path = parts
            return self.archive_manager.extract_zip_archive(archive_path, extract_path)
        except Exception as e:
            return f"Error parsing input: {str(e)}"

    def __calculate_hash_wrapper(self, input_str: str) -> str:
        """Wrapper for calculate_file_hash tool"""
        try:
            parts = input_str.split("|||")
            file_path = parts[0]
            hash_type = parts[1] if len(parts) > 1 else "md5"
            return self.security_manager.calculate_file_hash(file_path, hash_type)
        except Exception as e:
            return f"Error parsing input: {str(e)}"

    def __schedule_task_wrapper(self, input_str: str) -> str:
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
                return "The specified file could not be found. Please check if the file exists and the path is correct."  # noqa
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
