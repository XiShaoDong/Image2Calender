import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest

from config import get_api_key, set_api_key
from ocr import OcrLimitError, ocr_image


def test_env_key_preferred(tmp_path, monkeypatch):
    monkeypatch.setenv("OCRSPACE_KEY", "env-key-123")
    cfg = tmp_path / "config.json"
    set_api_key("file-key", cfg)
    assert get_api_key(cfg) == "env-key-123"


def test_file_key_fallback(tmp_path, monkeypatch):
    monkeypatch.delenv("OCRSPACE_KEY", raising=False)
    cfg = tmp_path / "config.json"
    set_api_key("file-key", cfg)
    assert get_api_key(cfg) == "file-key"


def test_set_api_key_persists(tmp_path):
    cfg = tmp_path / "config.json"
    set_api_key("abc", cfg)
    assert "abc" in cfg.read_text()


def test_ocr_image_network_error_raises():
    with pytest.raises(Exception):
        ocr_image(b"not-an-image", "bad-key")
