# AI System Agent

## ⚠️ Note
The Google Workspace integration is **still under development** and may contain **bugs or unexpected behavior**.  
If you encounter any issues or notice anything not working as expected, please **create an issue** in this repository to help us improve it.

A powerful and extensible AI system agent with LangChain integration that can perform various system operations, file management, web scraping, and more through natural language commands.

## 🚀 Features

- **File Operations**: Read, write, append, delete, and list files
- **Web Scraping**: Extract content and links from websites
- **System Commands**: Execute and monitor system commands (with safety checks)
- **Database Operations**: Interact with SQLite databases
- **Email Integration**: Send emails with attachments
- **Archive Management**: Create and extract archives
- **Network Tools**: Perform network operations like ping and file downloads
- **Security Features**: File hashing and duplicate detection
- **Task Scheduling**: Schedule tasks for later execution
- **Conversation Memory**: Maintains context across interactions (configurable window size)
- **Multi-Model Support**: Works with Gemini (default), OpenAI, and Anthropic models

## 📦 Installation

1. **Clone the repository**:
   ```bash
   git clone https://github.com/Hemanggour/System-Agent.git
   cd System-Agent
   ```

2. **Create and activate a virtual environment** (recommended):
   ```bash
   python -m venv venv
   # On Windows:
   .\venv\Scripts\activate
   # On Unix or MacOS:
   source venv/bin/activate
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up environment variables**:
   Create a `.env` file in the project root with your configuration:
   ```
   # Required: Choose one of the following API keys
   GOOGLE_API_KEY=your_google_api_key  # Default provider (Gemini)
   # OPENAI_API_KEY=your_openai_api_key
   # ANTHROPIC_API_KEY=your_anthropic_api_key

   # Optional: Configure model settings
   MODEL=gemini:gemini-2.0-flash  # Default model
   MODEL_TEMPERATURE=0.7  # Default: 0.7
   
   # Email configuration (required for email features)
   SMTP_SERVER=smtp.gmail.com
   SMTP_PORT=587
   EMAIL_USE_TLS=True
   EMAIL_USE_SSL=False
   EMAIL_DEFAULT_SENDER=your_email@example.com
   EMAIL_PASSWORD=your_app_specific_password
   
   # Agent configuration
   AGENT_NAME=ThinkPad  # Customize your agent's name
   MEMORY_WINDOW_SIZE=20  # Number of messages to keep in memory
   VERBOSE=True  # Enable verbose output
   ```

## 🚀 Usage

### Basic Usage

1. **Run the agent with default settings**:
   ```bash
   python main.py
   ```

### Advanced Usage with Custom LLM

You can use any LangChain-compatible LLM with the AIAgent. Here's an example using Ollama with a local model:

```python
from system_agent.agent import AIAgent
from langchain_ollama import ChatOllama

# Initialize a local LLM using Ollama
# Make sure you have pulled the model first: `ollama pull llama3`
llm = ChatOllama(
    model="llama3",  # or any other model you've pulled (e.g., "mistral", "gemma")
    temperature=0.2,
    # Add any other model-specific parameters
)

# Create the agent with your custom LLM
agent = AIAgent(llm=llm)

# Run commands
response = agent.run("Explain system AI agents in simple terms.")
print(response)
```

To use this example, you'll need to install the Ollama integration:
```bash
pip install langchain-ollama
```

2. **Interact with the agent**:
   - Type your commands in natural language
   - Type 'memory' to see conversation history
   - Type 'clear' to clear the conversation memory
   - Type 'quit', 'exit', or 'bye' to exit

### Example Commands

- File Operations:
  - "Read the contents of notes.txt"
  - "Create a file called todo.txt with my tasks"
  - "List all files in the current directory"

- Web Operations:
  - "Scrape the latest news from example.com"
  - "Search for information about LangChain"

- System Operations:
  - "Show system information"
  - "Check disk usage"

- Email:
  - "Send an email to test@example.com with subject 'Hello' and body 'This is a test'"

## 🛠️ Configuration

Key configuration options in `.env`:

```
# Core Settings
AGENT_NAME=ThinkPad  # Name of your agent
MEMORY_WINDOW_SIZE=20  # Conversation history length
MODEL=gemini:gemini-2.0-flash  # Default model
MODEL_TEMPERATURE=0.7  # 0.0 to 1.0 (lower = more focused, higher = more creative)

# Execution Limits
AGENT_MAX_ITERATIONS=15  # Maximum tool calls per request
AGENT_MAX_EXECUTION_TIME=60  # Maximum execution time in seconds

# Web Scraping
WEB_CONTENT_LIMIT=5000  # Max characters to scrape
WEB_LINKS_LIMIT=20  # Max links to return
WEB_REQUEST_TIMEOUT=10  # Request timeout in seconds
```

## 🔧 Dependencies

### Core Dependencies (from requirements.txt)
- `langchain` - Core framework for building the agent
- `langchain-community` - Community-maintained LangChain components
- `python-dotenv` - Environment variable management
- `langchain-google-genai` - Google Gemini integration
- `requests` - HTTP requests
- `beautifulsoup4` - HTML parsing
- `pandas` - Data manipulation
- `psutil` - System monitoring
- `ddgs` - DuckDuckGo search

### Google Workspace Dependencies
To use Google Workspace features, install the following additional packages:
```bash
pip install google-api-python-client google-auth-httplib2 google-auth-oauthlib
```

## 🔄 Google Workspace Integration

The agent includes powerful Google Workspace integration with the following features:

### Available Services
- **Gmail**: Send and read emails, manage labels
- **Google Calendar**: Create and manage events, list calendars
- **Google Drive**: Upload, download, and manage files
- **Google Docs**: Create and edit documents
- **Google Sheets**: Read and write spreadsheet data

### Setup Instructions

1. **Enable Google Workspace API**
   - Go to the [Google Cloud Console](https://console.cloud.google.com/)
   - Create a new project or select an existing one
   - Enable the following APIs:
     - Gmail API
     - Google Calendar API
     - Google Drive API
     - Google Docs API
     - Google Sheets API

2. **Configure OAuth Consent Screen**
   - In the Google Cloud Console, go to "APIs & Services" > "OAuth consent screen"
   - Set the user type to "External" and create
   - Fill in the required app information
   - Add the following scopes under "Scopes":
     - `https://www.googleapis.com/auth/gmail.send`
     - `https://www.googleapis.com/auth/gmail.readonly`
     - `https://www.googleapis.com/auth/calendar`
     - `https://www.googleapis.com/auth/drive`
     - `https://www.googleapis.com/auth/documents`
     - `https://www.googleapis.com/auth/spreadsheets`
   - Add test users (email addresses that will use the app)
   - Save and continue

3. **Create OAuth Credentials**
   - Go to "APIs & Services" > "Credentials"
   - Click "Create Credentials" > "OAuth client ID"
   - Select "Desktop app" as the application type
   - Download the credentials JSON file and save it as `credentials.json` in your project root

4. **Enable Google Workspace in Agent**
   Update your `.env` file with:
   ```
   # Google Workspace Configuration
   GOOGLE_WORKSPACE_ENABLED=True
   ```

5. **First Run Authentication**
   On first run, the agent will open a browser window for OAuth authentication. 
   - Sign in with your Google account
   - Grant the requested permissions
   - The token will be saved to `token.pickle` for future use

### Example Usage

```python
# After setting up, the agent will automatically have access to Google Workspace tools
# Example: Create a new Google Doc
response = agent.run("Create a new Google Doc named 'Project Plan' with some initial content")
print(response)
```

### Security Notes
- Never commit `credentials.json` or `token.pickle` to version control
- Add these files to your `.gitignore`:
  ```
  credentials.json
  token.pickle
  ```
- The token is stored locally and can be revoked at any time from your Google Account settings

### Optional Dependencies
- `langchain-ollama` - Required for using local models with Ollama
  ```bash
  pip install langchain-ollama
  ```
- `langchain-openai` - Required for OpenAI models
  ```bash
  pip install langchain-openai
  ```
- `langchain-anthropic` - Required for Anthropic models
  ```bash
  pip install langchain-anthropic
  ```

## 🤝 Contributing

Contributions are welcome! Please follow these steps:

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## 📜 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 👨‍💻 Author

- **Hemang Gour** - [GitHub](https://github.com/Hemanggour)

## 🙏 Acknowledgments

- Built with [LangChain](https://python.langchain.com/)
- Default model: [Google Gemini](https://ai.google.dev/)
- Inspired by the need for more powerful AI system agents
