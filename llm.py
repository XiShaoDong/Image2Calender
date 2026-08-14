import json
import re
from datetime import datetime

import requests

from parser import Event

GEMINI_ENDPOINT = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent"


class LlmUnavailableError(Exception):
    pass


def _build_prompt(text: str, base_date: datetime) -> str:
    return (
        "你是日历事件解析器。从下面的 OCR 文本中提取所有活动/预约事件，只返回 JSON。\n"
        f"今天是 {base_date.strftime('%Y-%m-%d')}（本地时区）。\n"
        '格式：{"events": [{"title": "...", "start": "YYYY-MM-DDTHH:MM:SS", '
        '"end": "YYYY-MM-DDTHH:MM:SS 或 null", "location": "... 或空串", "description": "... 或空串"}]}\n'
        "规则：\n"
        "- start/end 使用本地时区 ISO 格式 YYYY-MM-DDTHH:MM:SS\n"
        "- 文本没有年份时用今年；日期已过则推断明年\n"
        "- 没有结束时间时 end 为 null\n"
        "- 无法确定的字段填空串或 null\n"
        "- 从一段文本中提取出多个事件时全部返回\n"
        "OCR 文本：\n"
        f"{text}"
    )


def _extract_json(raw: str) -> dict | None:
    raw = raw.strip()
    m = re.search(r"```(?:json)?\s*(.*?)```", raw, re.S)
    if m:
        raw = m.group(1).strip()
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return None
    return data if isinstance(data, dict) else None


def _parse_events_from(data: dict, text: str, base_date: datetime) -> list[Event]:
    raw_events = data.get("events")
    if not isinstance(raw_events, list):
        return []
    events: list[Event] = []
    for item in raw_events:
        if not isinstance(item, dict):
            continue
        try:
            start = datetime.fromisoformat(str(item.get("start", ""))) if item.get("start") else None
        except ValueError:
            continue
        if not start:
            continue
        end = None
        if item.get("end"):
            try:
                end = datetime.fromisoformat(str(item["end"]))
            except ValueError:
                end = None
        events.append(Event(
            title=str(item.get("title") or "").strip(),
            start=start,
            end=end,
            location=str(item.get("location") or "").strip(),
            description=str(item.get("description") or text),
        ))
    return events


def parse_with_llm(text: str, api_key: str, base_date: datetime | None = None) -> list[Event]:
    if base_date is None:
        base_date = datetime.now()
    payload = {
        "contents": [{"parts": [{"text": _build_prompt(text, base_date)}]}],
        "generationConfig": {
            "responseMimeType": "application/json",
            "temperature": 0.2,
        },
    }
    try:
        resp = requests.post(
            f"{GEMINI_ENDPOINT}?key={api_key}",
            json=payload,
            timeout=60,
        )
        resp.raise_for_status()
        data = resp.json()
    except requests.RequestException as e:
        raise LlmUnavailableError(f"LLM 请求失败: {e}") from e
    try:
        candidates = data.get("candidates") or []
        raw_text = candidates[0]["content"]["parts"][0]["text"]
    except (KeyError, IndexError, TypeError) as e:
        raise LlmUnavailableError(f"LLM 响应格式异常: {data}") from e
    parsed = _extract_json(raw_text)
    if parsed is None:
        raise LlmUnavailableError("LLM 输出不是合法 JSON")
    events = _parse_events_from(parsed, text, base_date)
    if not events:
        raise LlmUnavailableError("LLM 未解析出有效事件")
    return events
