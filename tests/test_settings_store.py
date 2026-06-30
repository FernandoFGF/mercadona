"""Tests del settings_store."""
import pytest

from core import settings_store


def test_defaults_when_no_file(tmp_data_dir):
    assert settings_store.get("gemini_model") == settings_store.DEFAULTS["gemini_model"]
    assert settings_store.get("gemini_temperature") == 0.6
    assert settings_store.get("appearance_mode") == "dark"


def test_persisted_overrides_default(tmp_data_dir, monkeypatch):
    monkeypatch.delenv("GEMINI_MODEL", raising=False)
    monkeypatch.delenv("MERCADONA_WAREHOUSE", raising=False)
    monkeypatch.delenv("MERCADONA_MAX_EUR", raising=False)
    settings_store.set_value("gemini_model", "gemini-1.5-pro")
    settings_store.set_value("gemini_temperature", 0.9)
    assert settings_store.get("gemini_model") == "gemini-1.5-pro"
    assert settings_store.get("gemini_temperature") == 0.9


def test_env_overrides_persisted(tmp_data_dir, monkeypatch):
    settings_store.set_value("gemini_model", "from-json")
    monkeypatch.setenv("GEMINI_MODEL", "from-env")
    assert settings_store.get("gemini_model") == "from-env"


def test_env_overrides_default(tmp_data_dir, monkeypatch):
    monkeypatch.setenv("MERCADONA_WAREHOUSE", "bcn1")
    assert settings_store.get("mercadona_warehouse") == "bcn1"


def test_unknown_key_raises():
    with pytest.raises(KeyError):
        settings_store.get("no_existe")


def test_set_unknown_raises():
    with pytest.raises(KeyError):
        settings_store.set_value("no_existe", 1)


def test_persisted_keys_filtered(tmp_data_dir):
    settings_store.save({"gemini_model": "x", "GEMINI_API_KEY": "secret", "otro": 1})
    s = settings_store.load()
    assert "gemini_model" in s
    assert "GEMINI_API_KEY" not in s
    assert "otro" not in s


def test_save_load_roundtrip(tmp_data_dir):
    settings_store.set_value("appearance_mode", "light")
    settings_store.set_value("gemini_temperature", 0.3)
    s = settings_store.load()
    assert s["appearance_mode"] == "light"
    assert s["gemini_temperature"] == 0.3
