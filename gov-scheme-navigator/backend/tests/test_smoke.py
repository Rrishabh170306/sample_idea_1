from app.core.config import get_settings


def test_settings_defaults() -> None:
    settings = get_settings()
    assert settings.app_name == "AI Government Scheme Navigator"
    assert settings.api_prefix == "/api/v1"
