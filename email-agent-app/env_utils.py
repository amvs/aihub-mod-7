# env_utils.py
import os
from dotenv import dotenv_values
import yaml
from typing import Any, Dict

def summarize_value(value: str) -> str:
    """Return masked form: ****last4 or boolean string."""
    lower = value.lower()
    if lower in ("true", "false"):
        return lower
    return "****" + value[-4:] if len(value) > 4 else "****" + value

def doublecheck_env(file_path: str):
    """Check environment variables against a .env file and print summaries."""
    if not os.path.exists(file_path):
        print(f"Did not find file {file_path}.")
        print("This is used to double check the key settings for the notebook.")
        print("This is just a check and is not required.\n")
        return

    parsed = dotenv_values(file_path)
    for key in parsed.keys():
        current = os.getenv(key)
        if current is not None:
            print(f"{key}={summarize_value(current)}")
        else:
            print(f"{key}=<not set>")

    if parsed['MODEL_PROVIDER'] not in ("groq", "openai", "azure_openai"):
        print(f"Warning: MODEL_PROVIDER is set to {parsed['MODEL_PROVIDER']}, which is not a valid option.")


def llm_factory(config_path: str = "config.yml") -> Any:
    """
    Creates and returns a LangChain Chat Model instance.
    
    This function automatically reads non-sensitive settings (provider, model, 
    endpoints) from the centralized config.yml, while relying on system 
    environment variables strictly for API keys.
    """
    if not os.path.exists(config_path):
        raise FileNotFoundError(f"Configuration file not found at: {config_path}")

    # 1. Load configuration parameters from YAML
    with open(config_path, "r") as file:
        config = yaml.safe_load(file)

    llm_config: Dict[str, Any] = config.get("llm", {})
    
    provider = llm_config.get("vendor", "groq").lower()
    model = llm_config.get("model", "llama-3.3-70b-versatile")
    temperature = float(llm_config.get("temperature", 0.0))

    # 2. Return configured model with secrets automatically loaded from local environment
    if provider == "groq":
        from langchain_groq import ChatGroq
        # ChatGroq automatically fetches GROQ_API_KEY from environment
        llm =  ChatGroq(
            model=model, 
            temperature=temperature
        )

    elif provider == "openai":
        from langchain_openai import ChatOpenAI
        # ChatOpenAI automatically fetches OPENAI_API_KEY from environment
        llm_config = llm_config | config.get('openai', {})  # Merge any OpenAI-specific settings
        base_url = llm_config.get("openai_base_url")
        llm = ChatOpenAI(
            model=model,
            temperature=temperature,
            base_url=base_url if base_url else None
        )

    elif provider == "azure_openai":
        from langchain_openai import AzureChatOpenAI
        # AzureChatOpenAI automatically fetches AZURE_OPENAI_API_KEY from environment
        llm_config = llm_config | config.get('azure', {})  # Merge any Azure-specific settings
        llm = AzureChatOpenAI(
            model=model,
            temperature=temperature,
            azure_deployment=llm_config.get("deployment_name"),
            openai_api_version=llm_config.get("api_version"),
            azure_endpoint=llm_config.get("azure_endpoint")
        )
    else:
        raise ValueError(f"Unsupported model provider vendor: {provider}")

    try:
        llm.invoke('hello world')  # Test invocation to ensure the model is set up correctly
    except Exception as e:
        raise RuntimeError(f"Failed to invoke the model. Please check your API key and configuration. Error: {e}")
    return llm