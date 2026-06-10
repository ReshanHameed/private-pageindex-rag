from pathlib import Path

from private_pageindex.config import Settings, get_settings, reset_settings


def test_settings_defaults_are_local_private_values():
    settings = Settings()

    assert settings.ollama_base_url == "http://localhost:11434"
    assert settings.ollama_model == "gemma4:e4b"
    assert settings.data_dir == Path("data")
    assert settings.max_tree_prompt_chars == 45000
    assert settings.max_page_chars == 12000
    assert settings.tree_max_pages_per_node == 10


def test_settings_accept_environment_style_overrides(monkeypatch):
    monkeypatch.setenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434")
    monkeypatch.setenv("OLLAMA_MODEL", "mistral:latest")
    monkeypatch.setenv("DATA_DIR", "local-data")
    monkeypatch.setenv("MAX_TREE_PROMPT_CHARS", "1000")
    monkeypatch.setenv("MAX_PAGE_CHARS", "500")
    monkeypatch.setenv("TREE_MAX_PAGES_PER_NODE", "3")

    settings = Settings()

    assert settings.ollama_base_url == "http://127.0.0.1:11434"
    assert settings.ollama_model == "mistral:latest"
    assert settings.data_dir == Path("local-data")
    assert settings.max_tree_prompt_chars == 1000
    assert settings.max_page_chars == 500
    assert settings.tree_max_pages_per_node == 3


def test_get_settings_returns_same_instance():
    reset_settings()
    first = get_settings()
    second = get_settings()

    assert first is second


def test_reset_settings_clears_cache():
    reset_settings()
    first = get_settings()
    reset_settings()
    after_reset = get_settings()

    # Both return Settings with the same defaults, but they are
    # different object instances because the cache was cleared.
    assert first is not after_reset
    assert first.ollama_base_url == after_reset.ollama_base_url


def test_get_settings_picks_up_env_overrides_after_reset(monkeypatch):
    reset_settings()
    monkeypatch.setenv("OLLAMA_MODEL", "llama3:latest")

    reset_settings()
    settings = get_settings()

    assert settings.ollama_model == "llama3:latest"
    reset_settings()  # clean up for other tests
