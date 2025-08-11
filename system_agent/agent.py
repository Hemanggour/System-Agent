from datetime import datetime
from typing import List

from langchain.agents import AgentExecutor, create_tool_calling_agent
from langchain.tools import Tool
from langchain.schema import HumanMessage
from langchain.memory import ConversationBufferWindowMemory
from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_google_genai import ChatGoogleGenerativeAI

from system_agent.tools.file_manager import FileManager
from system_agent.tools.web_scraper import WebScraper


class AIAgent:
    """Main AI Agent class with LangChain and Google Gemini integration"""
    
    def __init__(self, google_api_key: str, model: str = "gemini-1.5-flash"):
        self.llm = ChatGoogleGenerativeAI(
            google_api_key=google_api_key,
            model=model,
            temperature=0.7,
            convert_system_message_to_human=True  # Required for Gemini compatibility
        )
        
        # Initialize file manager and web scraper
        self.file_manager = FileManager()
        self.web_scraper = WebScraper()
        
        # Create tools
        self.tools = self._create_tools()
        
        # Create memory with window of 10 messages
        self.memory = ConversationBufferWindowMemory(
            k=10,
            memory_key="chat_history",
            return_messages=True
        )
        
        # Create prompt template optimized for Gemini
        self.prompt = ChatPromptTemplate.from_messages([
            ("system", """You are a helpful AI assistant powered by Google's Gemini model with access to various tools. You can:

CAPABILITIES:
1. File Operations:
   - Read, write, and modify files
   - Delete files and list directory contents
2. Web Scraping:
   - Scrape websites and extract information
   - Extract links from webpages
3. Memory:
   - Remember the last 10 messages in our conversation
4. Task Execution:
   - Perform complex multi-step tasks
   - Chain operations together intelligently

INSTRUCTIONS:
- Use the available tools when needed to complete tasks
- Always provide clear, helpful, and detailed responses
- When working with files, specify full paths and handle errors gracefully
- When scraping websites, be respectful of rate limits and robots.txt
- Remember context from previous messages in our conversation
- Break down complex tasks into manageable steps

Available tools: read_file, write_file, append_to_file, delete_file, list_files, scrape_website, extract_links"""),
            MessagesPlaceholder(variable_name="chat_history"),
            ("human", "{input}"),
            MessagesPlaceholder(variable_name="agent_scratchpad")
        ])
        
        # Create agent using tool calling (compatible with Gemini)
        self.agent = create_tool_calling_agent(
            llm=self.llm,
            tools=self.tools,
            prompt=self.prompt
        )
        
        # Create agent executor
        self.agent_executor = AgentExecutor(
            agent=self.agent,
            tools=self.tools,
            memory=self.memory,
            verbose=True,
            handle_parsing_errors=True,
            max_iterations=5,  # Prevent infinite loops
            max_execution_time=30  # Timeout after 30 seconds
        )
    
    def _create_tools(self) -> List[Tool]:
        """Create tools for the agent"""
        tools = [
            Tool(
                name="read_file",
                description="Read content from a file. Input: file_path (string). Example: 'notes.txt' or '/path/to/file.txt'",
                func=self.file_manager.read_file
            ),
            Tool(
                name="write_file", 
                description="Create a new file or overwrite existing file with content. Input format: 'file_path|||content' (separated by three pipes). Example: 'notes.txt|||This is my note content'",
                func=lambda x: self._write_file_wrapper(x)
            ),
            Tool(
                name="append_to_file",
                description="Append content to an existing file (or create if doesn't exist). Input format: 'file_path|||content' (separated by three pipes). Example: 'log.txt|||New log entry'",
                func=lambda x: self._append_file_wrapper(x)
            ),
            Tool(
                name="delete_file",
                description="Delete a file from the filesystem. Input: file_path (string). Use with caution as this cannot be undone. Example: 'old_file.txt'",
                func=self.file_manager.delete_file
            ),
            Tool(
                name="list_files",
                description="List all files and directories in a given directory. Input: directory_path (string, use '.' for current directory). Example: '.' or '/home/user/documents'",
                func=self.file_manager.list_files
            ),
            Tool(
                name="get_file_info",
                description="Get detailed information about a file including size, creation date, etc. Input: file_path (string). Example: 'notes.txt'",
                func=self.file_manager.get_file_info
            ),
            Tool(
                name="scrape_website",
                description="Scrape text content from a website URL. Input: url (string). Returns cleaned text content from the webpage. Example: 'https://example.com'",
                func=self.web_scraper.scrape_url
            ),
            Tool(
                name="extract_links",
                description="Extract all hyperlinks from a webpage. Input: url (string). Returns a list of links found on the page. Example: 'https://example.com'",
                func=self.web_scraper.extract_links
            )
        ]
        return tools
    
    def _write_file_wrapper(self, input_str: str) -> str:
        """Wrapper for write_file to handle the file_path|||content format"""
        try:
            if not input_str or input_str.strip() == "":
                return "Error: No input provided. Use format 'file_path|||content'"
            
            # Split on ||| but only split once to handle content with |||
            parts = input_str.split('|||', 1)
            if len(parts) != 2:
                return "Error: Input must be in format 'file_path|||content' (separated by three pipes). Example: 'notes.txt|||Hello World'"
            
            file_path, content = parts
            file_path = file_path.strip()
            
            if not file_path:
                return "Error: File path cannot be empty"
            
            # Content can be empty (creating empty file is valid)
            result = self.file_manager.write_file(file_path, content)
            return result
            
        except Exception as e:
            return f"Error in write_file operation: {str(e)}"
    
    def _append_file_wrapper(self, input_str: str) -> str:
        """Wrapper for append_file to handle the file_path|||content format"""
        try:
            if not input_str or input_str.strip() == "":
                return "Error: No input provided. Use format 'file_path|||content'"
            
            # Split on ||| but only split once to handle content with |||
            parts = input_str.split('|||', 1)
            if len(parts) != 2:
                return "Error: Input must be in format 'file_path|||content' (separated by three pipes). Example: 'log.txt|||New entry'"
            
            file_path, content = parts
            file_path = file_path.strip()
            
            if not file_path:
                return "Error: File path cannot be empty"
            
            # For append, we typically want some content
            if not content:
                return "Warning: Appending empty content. Use write_file to create empty files."
            
            result = self.file_manager.write_file(file_path, content, mode='a')
            return result
            
        except Exception as e:
            return f"Error in append_file operation: {str(e)}"
    
    def chat(self, message: str) -> str:
        """Main chat method"""
        try:
            # Add timestamp to the message content instead of as separate input
            timestamped_message = f"[Current time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {message}"
            
            response = self.agent_executor.invoke({
                "input": timestamped_message
            })
            
            return response["output"]
        except Exception as e:
            return f"I apologize, but I encountered an error processing your request: {str(e)}\n\nPlease try rephrasing your request or break it down into smaller steps."
    
    def get_memory_summary(self) -> str:
        """Get a summary of the conversation memory"""
        messages = self.memory.chat_memory.messages
        if not messages:
            return "No conversation history yet."
        
        summary = f"Conversation history ({len(messages)} messages, showing last 10):\n"
        summary += "=" * 50 + "\n"
        
        for i, msg in enumerate(messages[-10:], 1):  # Show last 10 messages
            role = "👤 You" if isinstance(msg, HumanMessage) else "🤖 AI Assistant"
            content = msg.content[:150] + "..." if len(msg.content) > 150 else msg.content
            summary += f"{i}. {role}: {content}\n\n"
        
        return summary
    
    def clear_memory(self) -> str:
        """Clear conversation memory"""
        self.memory.clear()
        return "✅ Conversation memory has been cleared. Starting fresh!"
    
    def get_capabilities(self) -> str:
        """Return a summary of agent capabilities"""
        return """
🚀 AI Agent Capabilities:

📁 FILE OPERATIONS:
   • Read files and display content
   • Create new files with custom content  
   • Append to existing files
   • Delete files (with confirmation)
   • List directory contents
   • Get detailed file information

🌐 WEB OPERATIONS:
   • Scrape website content
   • Extract all links from webpages
   • Handle various web formats
   • Respect rate limits and timeouts

🧠 MEMORY & CONVERSATION:
   • Remember last 10 messages
   • Maintain context across interactions
   • Handle complex multi-step tasks
   • Chain operations intelligently

💡 EXAMPLE COMMANDS:
   • "Create a file called 'notes.txt' with my meeting notes"
   • "Scrape https://example.com and save the content to a file"
   • "What did we discuss earlier about file operations?"
   • "Find all links on Wikipedia's homepage and save them"
   • "Read my notes.txt file and summarize the content"
        """
