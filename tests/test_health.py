import os
import pytest

def test_project_health():
    """
    Basic health check to ensure core directories and files exist.
    """
    assert os.path.exists("app.py"), "Main entry point app.py is missing"
    assert os.path.exists("pages"), "Pages directory is missing"
    assert os.path.exists("requirements.txt"), "Requirements file is missing"
    assert os.path.exists("config.py"), "Config file is missing"
