from dataclasses import dataclass
from datetime import date
import json
import requests

from config import _load, _save, DEFAULT_CONFIG

OCR_ENDPOINT = "https://api.ocr.space/parse/image"
DAILY_LIMIT = 500


class OcrLimitError(Exception):
    pass


class OcrApiError(Exception):
    pass


@dataclass
class OcrResult:
    text: str
    lines: list[dict]


def _today_usage(config_path=DEFAULT_CONFIG) -> int:
    data = _load(config_path)
    usage = data.get("usage", {})
    if usage.get("date") != date.today().isoformat():
        return 0
    return int(usage.get("count", 0))


def _bump_usage(config_path=DEFAULT_CONFIG) -> None:
    data = _load(config_path)
    usage = data.get("usage", {})
    if usage.get("date") != date.today().isoformat():
        usage = {"date": date.today().isoformat(), "count": 0}
    usage["count"] = int(usage.get("count", 0)) + 1
    data["usage"] = usage
    _save(config_path, data)


def ocr_image(image_bytes: bytes, api_key: str, config_path=DEFAULT_CONFIG) -> OcrResult:
    if _today_usage(config_path) >= DAILY_LIMIT:
        raise OcrLimitError(f"今日 OCR 用量已达 {DAILY_LIMIT} 次上限，请明天再试")
    try:
        resp = requests.post(
            OCR_ENDPOINT,
            headers={"apikey": api_key},
            files={"file": ("image.jpg", image_bytes, "image/jpeg")},
            data={
                "language": "auto",
                "OCREngine": "1",
                "isOverlayRequired": "true",
                "scale": "true",
            },
            timeout=60,
        )
        resp.raise_for_status()
    except requests.RequestException as e:
        raise OcrApiError(f"OCR 请求失败: {e}") from e
    data = resp.json()
    if data.get("IsErroredOnProcessing") or not data.get("ParsedResults"):
        raise OcrApiError(f"OCR 处理失败: {data.get('ErrorMessage')}")
    result = data["ParsedResults"][0]
    if result.get("FileParseExitCode") != 1:
        raise OcrApiError(f"OCR 解析失败: {result.get('ErrorMessage')}")
    _bump_usage(config_path)
    lines = []
    overlay = result.get("TextOverlay") or {}
    for line in overlay.get("Lines") or []:
        words = " ".join(w.get("WordText", "") for w in line.get("Words", []))
        lines.append({"text": words, "height": line.get("MaxHeight", 0)})
    return OcrResult(text=result.get("ParsedText", "").strip(), lines=lines)
