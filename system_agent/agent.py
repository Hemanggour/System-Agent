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
        """Create comprehensive tools for the agent by collecting tools from all managers."""
        # Initialize an empty list to hold all tools
        all_tools = []

        # Add tools from each manager
        all_tools.extend(self.file_manager.get_tools())
        all_tools.extend(self.web_scraper.get_tools())
        all_tools.extend(self.system_manager.get_tools())
        all_tools.extend(self.database_manager.get_tools())
        all_tools.extend(self.email_manager.get_tools())
        all_tools.extend(self.archive_manager.get_tools())
        all_tools.extend(self.network_manager.get_tools())
        all_tools.extend(self.security_manager.get_tools())
        all_tools.extend(self.scheduler_manager.get_tools())

        return all_tools

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
