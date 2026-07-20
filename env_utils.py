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


def create_llm(
    model_provider: str = None, 
    model_base_url: str = None, 
    deployment_name: str = None, 
    open_ai_api_version: str = None, 
    azure_openai_api_base: str = None, 
    model: str = "llama-3.3-70b-versatile",
    temperature: float = 0.0
):
    """Create an LLM instance, automatically falling back to environment variables."""
    
    # 1. Fall back to environment variables if not explicitly passed
    model_provider = model_provider or os.getenv("MODEL_PROVIDER", "groq")
    model_base_url = model_base_url or os.getenv("MODEL_BASE_URL", "")
    deployment_name = deployment_name or os.getenv("DEPLOYMENT_NAME", "")
    open_ai_api_version = open_ai_api_version or os.getenv("OPENAI_API_VERSION", "")
    azure_openai_api_base = azure_openai_api_base or os.getenv("AZURE_OPENAI_API_BASE", "")

    # 2. Return configured model with model & temperature applied consistently
    if model_provider == "groq":
        from langchain_groq import ChatGroq
        return ChatGroq(model=model, temperature=temperature)
        
    elif model_provider == "openai":
        from langchain_openai import ChatOpenAI  # Swapped from legacy OpenAI to ChatOpenAI
        return ChatOpenAI(
            model=model,
            temperature=temperature,
            base_url=model_base_url if model_base_url else None
        )
        
    elif model_provider == "azure_openai":
        from langchain_openai import AzureChatOpenAI
        return AzureChatOpenAI(
            model=model,
            temperature=temperature,
            deployment_name=deployment_name,
            openai_api_version=open_ai_api_version,
            azure_endpoint=azure_openai_api_base
        )
        
    else:
        raise ValueError(f"Unsupported model provider: {model_provider}")