def load_model(model: str, **model_kwargs):
    """
    Returns the LLM instance for the specified model.
    """
    model = model.lower()

    provider, model_name = model.split(":", 1)

    common_params = {}
    model_kwargs = {}

    if "temperature" in model_kwargs:
        common_params["temperature"] = model_kwargs["temperature"]

    if "top_p" in model_kwargs:
        common_params["top_p"] = model_kwargs["top_p"]

    # provider-specific extras
    if "safety_settings" in model_kwargs:  
        model_kwargs["safety_settings"] = model_kwargs["safety_settings"]


    if provider == "openai":
        try:
            from langchain_openai import ChatOpenAI
        except ImportError:
            raise ImportError(
                "langchain-openai is not installed. Install it with:\n"
                "pip install langchain-openai"
            )
        return ChatOpenAI(
            model=model_name,
            **common_params,
            model_kwargs=model_kwargs
        )

    elif provider == "gemini":
        try:
            from langchain_google_genai import ChatGoogleGenerativeAI
        except ImportError:
            raise ImportError(
                "langchain-google-genai is not installed. Install it with:\n"
                "pip install langchain-google-genai"
            )
        return ChatGoogleGenerativeAI(
            model=model_name,
            **common_params,
            model_kwargs=model_kwargs
        )

    elif provider == "anthropic":
        try:
            from langchain_anthropic import ChatAnthropic
        except ImportError:
            raise ImportError(
                "langchain-anthropic is not installed. Install it with:\n"
                "pip install langchain-anthropic"
            )
        return ChatAnthropic(
            model=model_name,
            **common_params,
            model_kwargs=model_kwargs
        )

    else:
        raise ValueError(f"Unsupported model: {model}")
