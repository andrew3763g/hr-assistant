import os

from backend.app.config import Settings


def test_cors_allow_origins_comma_list(monkeypatch):
    monkeypatch.delenv("CORS_ALLOW_ORIGINS", raising=False)
    settings = Settings(CORS_ALLOW_ORIGINS="https://a.example, https://b.example")
    assert settings.CORS_ALLOW_ORIGINS == ["https://a.example", "https://b.example"]


def test_cors_allow_origins_json_list(monkeypatch):
    monkeypatch.delenv("CORS_ALLOW_ORIGINS", raising=False)
    settings = Settings(CORS_ALLOW_ORIGINS='["https://one.example", "https://two.example"]')
    assert settings.CORS_ALLOW_ORIGINS == ["https://one.example", "https://two.example"]


def test_cors_allow_origins_empty_string(monkeypatch):
    monkeypatch.delenv("CORS_ALLOW_ORIGINS", raising=False)
    settings = Settings(CORS_ALLOW_ORIGINS="   ")
    assert settings.CORS_ALLOW_ORIGINS == []


def test_cors_allow_origins_default(monkeypatch):
    monkeypatch.delenv("CORS_ALLOW_ORIGINS", raising=False)
    settings = Settings(_env_file=None)
    assert settings.CORS_ALLOW_ORIGINS == ["*"]
