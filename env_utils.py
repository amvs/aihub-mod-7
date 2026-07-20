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

    if parsed['MODEL_BASE_URL'] and parsed['MODEL_PROVIDER'] != "openai":
        print(f"Warning: MODEL_BASE_URL is set but MODEL_PROVIDER is {parsed['MODEL_PROVIDER']}. MODEL_BASE_URL is only used with 'openai' provider.")



