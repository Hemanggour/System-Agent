class LLMFactory:
    """
    A factory class to create and return LangChain LLM instances
    for different providers without forcing unused dependencies.
    """

    def __init__(self, config: dict):
        """
        Initialize with provider-specific configurations.
        """
        self.config = config

    def get_llm(self, provider: str):
        """
        Returns the LLM instance for the specified provider.
        """
        provider = provider.lower()

        if provider == "openai":
            try:
                from langchain_openai import ChatOpenAI
            except ImportError:
                raise ImportError(
                    "langchain-openai is not installed. Install it with:\n"
                    "pip install langchain-openai"
                )
            return ChatOpenAI(model=self.config.get("model"))

        elif provider == "gemini":
            try:
                from langchain_google_genai import ChatGoogleGenerativeAI
            except ImportError:
                raise ImportError(
                    "langchain-google-genai is not installed. Install it with:\n"
                    "pip install langchain-google-genai"
                )
            return ChatGoogleGenerativeAI(model=self.config.get("model"))

        elif provider == "anthropic":
            try:
                from langchain_anthropic import ChatAnthropic
            except ImportError:
                raise ImportError(
                    "langchain-anthropic is not installed. Install it with:\n"
                    "pip install langchain-anthropic"
                )
            return ChatAnthropic(model=self.config.get("model"))

        else:
            raise ValueError(f"Unsupported LLM provider: {provider}")
