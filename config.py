import json
import os
from pathlib import Path

DEFAULT_CONFIG = Path(__file__).parent / "config.json"


def _load(config_path: Path) -> dict:
    if config_path.exists():
        try:
            return json.loads(config_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return {}
    return {}


def _save(config_path: Path, data: dict) -> None:
    config_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def get_api_key(config_path: Path = DEFAULT_CONFIG) -> str | None:
    env_key = os.environ.get("OCRSPACE_KEY")
    if env_key:
        return env_key
    return _load(config_path).get("api_key")


def set_api_key(key: str, config_path: Path = DEFAULT_CONFIG) -> None:
    data = _load(config_path)
    data["api_key"] = key
    _save(config_path, data)
