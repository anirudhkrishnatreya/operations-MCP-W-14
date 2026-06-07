import os
from typing import Optional


def ensure_env(var_name: str, default: Optional[str] = None) -> str:
    """
    Proactively check if the requested environment variable exists.
    Throws a ValueError if it is missing or empty.
    """
    val = os.getenv(var_name, default)
    if not val or not val.strip():
        raise ValueError(f"Environment variable '{var_name}' is missing or empty.")
    return val.strip()
