def load_model(model: str, **model_kwargs):
    """
    Returns the LLM instance for the specified model.
    """
    model = model.lower()

    provider, model_name = model.split(":", 1)

    if provider == "openai":
        try:
            from langchain_openai import ChatOpenAI
        except ImportError:
            raise ImportError(
                "langchain-openai is not installed. Install it with:\n"
                "pip install langchain-openai"
            )
        return ChatOpenAI(model=model_name, **model_kwargs)

    elif provider == "gemini":
        try:
            from langchain_google_genai import ChatGoogleGenerativeAI
        except ImportError:
            raise ImportError(
                "langchain-google-genai is not installed. Install it with:\n"
                "pip install langchain-google-genai"
            )
        return ChatGoogleGenerativeAI(model=model_name, **model_kwargs)

    elif provider == "anthropic":
        try:
            from langchain_anthropic import ChatAnthropic
        except ImportError:
            raise ImportError(
                "langchain-anthropic is not installed. Install it with:\n"
                "pip install langchain-anthropic"
            )
        return ChatAnthropic(model=model_name, **model_kwargs)

    else:
        raise ValueError(f"Unsupported model: {model}")
