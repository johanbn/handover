"""
Provides
    Secrets:
        Lazy-loaded secrets manager class.
    secrets:
        Pre-defined instance of Secrets.
"""
import os
from pathlib import Path
from typing import Optional

class Secrets:
    """
    Lazy-loaded secrets manager.

    - Secret name = filename without extension (lowercased)
    - Value = file content (stripped)
    - Directory is taken from os.environ["SECRET_DIR"]
    - Raises Exceptions when either SECRET_DIR or the secret is missing.
    """

    _instance: Optional["Secrets"] = None
    _loaded: dict[str, str] = {}

    def __new__(cls) -> "Secrets":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    @classmethod
    def get(cls, name: str, raise_if_missing: bool = False) -> str:
        """
        Get a secret value by name.
        
        If the secret doesn't exist:
            and raise_if_missing is True -> raises KeyError
            and raise_if_missing is False -> returns empty string.
        """
        lower_name = name.lower()
        cls._load_if_needed() # Lazy load on first access

        if lower_name in cls._loaded:
            return cls._loaded[lower_name]
        
        if not raise_if_missing:
            return ""
        
        dir_path = cls._get_secrets_dir()
        raise KeyError(
            f"Secret '{name}' (looked for '{lower_name}') not found in  {dir_path}. "
            f"Available: {', '.join(cls._loaded_keys()) or 'none'}"
        )
    
    @classmethod
    def get_or_raise(cls, name: str) -> str:
        """Alias for get() that always raises if missing."""
        return cls.get(name, raise_if_missing=True)
    
    @classmethod
    def exists(cls, name: str) -> bool:
        """Check if a secret exists."""
        lower_name = name.lower()
        cls._load_if_needed()
        return lower_name in cls._loaded
    
    @classmethod
    def _load_if_needed(cls) -> None:
        if cls._loaded:
            return
        
        secrets_dir = cls._get_secrets_dir()
        path = Path(secrets_dir)

        if not path.is_dir():
            if os.getenv("SECRET_DIR") is not None:
                raise RuntimeError(
                    f"SECRET_DIR is set to '{secrets_dir}' but directory does not exist."
                )
            return
        
        for file_path in path.iterdir():
            if file_path.is_file():
                key = file_path.stem.lower() # excludes file extensions
                try:
                    value = file_path.read_text(encoding="utf-8").strip()
                    if value:
                        cls._loaded[key] = value
                except Exception as e:
                    raise RuntimeError(f"Failed to read secret file {file_path}: {e}") from e
    
    @staticmethod
    def _get_secrets_dir() -> str:
        return os.getenv("SECRET_DIR", ".secrets")

secrets = Secrets()
'''
Defined singleton instance of Secrets for ease of use.
'''
