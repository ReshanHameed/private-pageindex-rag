from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime settings for the local-only PageIndex RAG app."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    ollama_base_url: str = Field(default="http://localhost:11434")
    ollama_model: str = Field(default="gemma4:e4b")
    data_dir: Path = Field(default=Path("data"))
    max_tree_prompt_chars: int = Field(default=45000)
    max_page_chars: int = Field(default=12000)
    tree_max_pages_per_node: int = Field(default=10)
    tree_prompt_compact_threshold: int = Field(
        default=4000,
        description=(
            "When the full tree prompt (titles + summaries) exceeds this many "
            "characters, switch to compact mode (titles + page ranges only). "
            "Keeps the LLM selection prompt small enough for local models to "
            "reason about reliably."
        ),
    )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return a cached singleton Settings instance.

    The first call reads ``.env`` and environment variables.  Subsequent
    calls return the same object without re-reading the filesystem.
    """
    return Settings()


def reset_settings() -> None:
    """Clear the cached settings singleton.

    Useful in tests that need to override environment variables between
    test cases.
    """
    get_settings.cache_clear()
