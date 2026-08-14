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


def _save(config_path: Path, data: dict) -> bool:
    try:
        config_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        return True
    except OSError:
        return False


def get_api_key(config_path: Path = DEFAULT_CONFIG) -> str | None:
    env_key = os.environ.get("OCRSPACE_KEY")
    if env_key:
        return env_key
    return _load(config_path).get("api_key")


def set_api_key(key: str, config_path: Path = DEFAULT_CONFIG) -> bool:
    data = _load(config_path)
    data["api_key"] = key
    return _save(config_path, data)


def get_llm_key(config_path: Path = DEFAULT_CONFIG) -> str | None:
    env_key = os.environ.get("GEMINI_KEY")
    if env_key:
        return env_key
    return _load(config_path).get("llm_key")


def set_llm_key(key: str, config_path: Path = DEFAULT_CONFIG) -> bool:
    data = _load(config_path)
    data["llm_key"] = key
    return _save(config_path, data)


def get_public_mode(config_path: Path = DEFAULT_CONFIG) -> bool:
    if os.environ.get("PUBLIC_MODE") in ("1", "true", "True"):
        return True
    return bool(_load(config_path).get("public_mode", False))


def set_public_mode(enabled: bool, config_path: Path = DEFAULT_CONFIG) -> bool:
    data = _load(config_path)
    data["public_mode"] = enabled
    return _save(config_path, data)


def get_access_code(config_path: Path = DEFAULT_CONFIG) -> str | None:
    env_code = os.environ.get("ACCESS_CODE")
    if env_code:
        return env_code
    code = _load(config_path).get("access_code")
    return code if code else None


def set_access_code(code: str, config_path: Path = DEFAULT_CONFIG) -> bool:
    data = _load(config_path)
    data["access_code"] = code
    return _save(config_path, data)


def get_admin_password(config_path: Path = DEFAULT_CONFIG) -> str | None:
    env_pw = os.environ.get("ADMIN_PASSWORD")
    if env_pw:
        return env_pw
    pw = _load(config_path).get("admin_password")
    return pw if pw else None


def set_admin_password(pw: str, config_path: Path = DEFAULT_CONFIG) -> bool:
    data = _load(config_path)
    data["admin_password"] = pw
    return _save(config_path, data)
