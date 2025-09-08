import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.core import config
from pathlib import Path


def test_config_paths():
    """
    Tests that the configuration paths are correctly defined.
    """
    assert isinstance(config.BASE_DIR, Path)
    assert str(config.CONFIG_DIR).endswith("config")
    assert str(config.CONFIG_FILE).endswith("config.ini")
    assert str(config.LAYOUT_FILE).endswith("dashboard_layout.json")
    assert str(config.STATIC_DIR).endswith("static")
    assert str(config.TEMPLATES_DIR).endswith("templates")


def test_config_constants():
    """
    Tests that the application constants are defined.
    """
    assert config.APP_NAME == "HWA Dashboard"
    assert isinstance(config.SERVER_PORT, int)
    assert config.BASE_URL == f"http://localhost:{config.SERVER_PORT}"
    assert isinstance(config.CORS_ALLOWED_ORIGINS, list)
