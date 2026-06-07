"""
Centralized LLM logic (model initialization, API calls, context management).
"""

import litellm
from crewai import LLM
from config import ensure_env

# Apply global LLM settings
litellm.drop_params = True


def get_llama_instant() -> LLM:
    """
    Llama 3.1 8b on Groq — fast, for research/retrieval tasks.
    """
    return LLM(
        model="groq/llama-3.1-8b-instant",
        api_key=ensure_env("GROQ_API_KEY"),
        temperature=0.1,
        drop_params=True,
    )


def get_llama_versatile() -> LLM:
    """
    Llama 3.3 70b on Groq — highly capable, for report writing.
    """
    return LLM(
        model="groq/llama-3.3-70b-versatile",
        api_key=ensure_env("GROQ_API_KEY"),
        temperature=0.3,
        drop_params=True,
    )
