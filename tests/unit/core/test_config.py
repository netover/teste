from pathlib import Path
from src.core import config
from src.core.settings import settings

def test_config_paths():
    """
    Tests that the static configuration paths are correctly defined.
    """
    assert isinstance(config.BASE_DIR, Path)
    assert str(config.CONFIG_DIR).endswith("config")
    assert str(config.STATIC_DIR).endswith("static")
    assert str(config.TEMPLATES_DIR).endswith("templates")
    # Test the default layout file path when no override is set
    assert str(config.get_layout_file()).endswith("config/dashboard_layout.json")

def test_layout_file_override(monkeypatch):
    """
    Tests that setting LAYOUT_FILE_OVERRIDE on the settings object
    is correctly picked up by the get_layout_file function.
    """
    test_path = "/tmp/test_layout.json"
    # Patch the settings object directly for a more focused unit test
    monkeypatch.setattr(settings, "LAYOUT_FILE_OVERRIDE", test_path)
    assert config.get_layout_file() == Path(test_path)

def test_settings_defaults():
    """
    Tests that the Pydantic settings object loads with correct default values.
    """
    assert settings.APP_NAME == "HWA Dashboard"
    assert settings.SERVER_PORT == 63136
    assert settings.BASE_URL == f"http://{settings.SERVER_HOST}:{settings.SERVER_PORT}"
    assert isinstance(settings.CORS_ALLOWED_ORIGINS, list)
    assert settings.API_KEY == "default_api_key"