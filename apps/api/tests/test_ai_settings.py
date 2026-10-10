from app.core.config import Settings


def _clear_gemini_environment(monkeypatch):
    for name in (
        "GEMINI_API_KEY",
        "CONTENT_STUDIO_GEMINI",
        "GEMINI_KEY",
        "GOOGLE_API_KEY",
        "GEMINI_MODEL",
    ):
        monkeypatch.delenv(name, raising=False)


def test_content_studio_gemini_system_variable_is_supported(tmp_path, monkeypatch):
    _clear_gemini_environment(monkeypatch)
    monkeypatch.setenv("CONTENT_STUDIO_GEMINI", "system-gemini-test-key")

    settings = Settings(_env_file=tmp_path / "missing.env")

    assert settings.GEMINI_API_KEY == "system-gemini-test-key"


def test_preferred_content_studio_key_precedes_compatibility_alias(tmp_path, monkeypatch):
    _clear_gemini_environment(monkeypatch)
    monkeypatch.setenv("GEMINI_API_KEY", "process-gemini-test-key")
    monkeypatch.setenv("CONTENT_STUDIO_GEMINI", "system-alias-test-key")

    settings = Settings(_env_file=tmp_path / "missing.env")

    assert settings.GEMINI_API_KEY == "system-alias-test-key"


def test_process_gemini_key_precedes_dotenv_value(tmp_path, monkeypatch):
    _clear_gemini_environment(monkeypatch)
    env_file = tmp_path / ".env"
    env_file.write_text("GEMINI_API_KEY=dotenv-gemini-test-key\n", encoding="utf-8")
    monkeypatch.setenv("GEMINI_API_KEY", "process-gemini-test-key")

    settings = Settings(_env_file=env_file)

    assert settings.GEMINI_API_KEY == "process-gemini-test-key"


def test_empty_dotenv_placeholder_does_not_suppress_process_key(tmp_path, monkeypatch):
    _clear_gemini_environment(monkeypatch)
    env_file = tmp_path / ".env"
    env_file.write_text("GEMINI_API_KEY=\n", encoding="utf-8")
    monkeypatch.setenv("CONTENT_STUDIO_GEMINI", "system-gemini-test-key")

    settings = Settings(_env_file=env_file)

    assert settings.GEMINI_API_KEY == "system-gemini-test-key"


def test_dotenv_gemini_key_is_used_when_process_credentials_are_absent(
    tmp_path, monkeypatch
):
    _clear_gemini_environment(monkeypatch)
    env_file = tmp_path / ".env"
    env_file.write_text("GEMINI_API_KEY=dotenv-gemini-test-key\n", encoding="utf-8")

    settings = Settings(_env_file=env_file)

    assert settings.GEMINI_API_KEY == "dotenv-gemini-test-key"


def test_legacy_gemini_aliases_remain_supported(tmp_path, monkeypatch):
    for alias in ("GEMINI_KEY", "GOOGLE_API_KEY"):
        _clear_gemini_environment(monkeypatch)
        monkeypatch.setenv(alias, "legacy-gemini-test-key")

        settings = Settings(_env_file=tmp_path / "missing.env")

        assert settings.GEMINI_API_KEY == "legacy-gemini-test-key"


def test_gemini_credential_is_none_when_no_supported_source_is_configured(
    tmp_path, monkeypatch
):
    _clear_gemini_environment(monkeypatch)

    settings = Settings(_env_file=tmp_path / "missing.env")

    assert settings.GEMINI_API_KEY is None
    assert settings.GEMINI_MODEL == "gemini-3.8-flash"
    assert not hasattr(settings, "OPENAI_API_KEY")
    assert not hasattr(settings, "QWEN_API_KEY")
