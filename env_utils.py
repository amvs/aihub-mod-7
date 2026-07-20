# env_utils.py
import os
from dotenv import dotenv_values

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


def create_llm(model_provider: str, model_base_url: str = "", deployment_name: str = "", open_ai_api_version: str = "", azure_openai_api_base: str = "", **kwargs):
    """Create an LLM instance based on the model provider and parameters."""
    if model_provider == "groq":
        from langchain_groq import ChatGroq
        return ChatGroq(model=kwargs.get('model', 'llama-3.3-70b-versatile'), temperature = kwargs.get('temperature', 0.0))
    elif model_provider == "openai":
        from langchain_openai import OpenAI
        return OpenAI(base_url=model_base_url)
    elif model_provider == "azure_openai":
        from langchain_openai import AzureChatOpenAI
        return AzureChatOpenAI(
            deployment_name=deployment_name,
            openai_api_version=open_ai_api_version,
            azure_endpoint=azure_openai_api_base
        )
    else:
        raise ValueError(f"Unsupported model provider: {model_provider}")