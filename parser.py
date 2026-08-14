from dataclasses import dataclass, field
from datetime import date, datetime, time, timedelta
import re

@dataclass
class Event:
    title: str = ""
    start: datetime | None = None
    end: datetime | None = None
    location: str = ""
    description: str = ""
    warnings: list[str] = field(default_factory=list)

CHINESE_WEEKDAYS = {"一": 0, "二": 1, "三": 2, "四": 3, "五": 4, "六": 5, "日": 6, "天": 6}

MONTHS_EN = {
    "jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
    "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12,
}

_PLACEHOLDER_YEAR = 2000


def _safe_date(year: int, month: int, day: int) -> date | None:
    try:
        return date(year, month, day)
    except ValueError:
        return None


def _find_dates(text: str) -> list[tuple[date, int, int]]:
    found: list[tuple[date, int, int]] = []
    for m in re.finditer(r"(\d{4})\s*年\s*(\d{1,2})\s*月\s*(\d{1,2})\s*[日号]?", text):
        d = _safe_date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
        if d:
            found.append((d, m.start(), m.end()))
    for m in re.finditer(r"(?<!\d)(\d{1,2})\s*月\s*(\d{1,2})\s*[日号]?(?!\d)", text):
        d = _safe_date(_PLACEHOLDER_YEAR, int(m.group(1)), int(m.group(2)))
        if d:
            found.append((d, m.start(), m.end()))
    for m in re.finditer(r"(?<!\d)(\d{4})[/.\-](\d{1,2})[/.\-](\d{1,2})(?!\d)", text):
        d = _safe_date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
        if d:
            found.append((d, m.start(), m.end()))
    for m in re.finditer(r"(?<!\d)(\d{1,2})/(\d{1,2})(?!\d)", text):
        d = _safe_date(_PLACEHOLDER_YEAR, int(m.group(1)), int(m.group(2)))
        if d:
            found.append((d, m.start(), m.end()))
    for m in re.finditer(r"(?<!\d)(\d{1,2})[/.\-](\d{1,2})[/.\-](\d{4})(?!\d)", text):
        d = _safe_date(int(m.group(3)), int(m.group(1)), int(m.group(2)))
        if d:
            found.append((d, m.start(), m.end()))
    for m in re.finditer(r"(?<!\d)(\d{1,2})[/.\-](\d{1,2})[/.\-](\d{2})(?!\d)", text):
        yy = int(m.group(3))
        year = 2000 + yy if yy < 70 else 1900 + yy
        d = _safe_date(year, int(m.group(1)), int(m.group(2)))
        if d:
            found.append((d, m.start(), m.end()))
    en_pattern = (
        r"(?<![A-Za-z])([A-Za-z]{3,9})\s+(\d{1,2}),?\s+(\d{4})(?!\d)"
        r"|(?<!\d)(\d{1,2})\s+([A-Za-z]{3,9})\s+(\d{4})(?!\d)"
        r"|(?<![A-Za-z])([A-Za-z]{3,9})\s+(\d{1,2})(?!\d)"
    )
    for m in re.finditer(en_pattern, text):
        if m.group(1) and m.group(2) and m.group(3):
            mon = MONTHS_EN.get(m.group(1).lower()[:3])
            if mon:
                d = _safe_date(int(m.group(3)), mon, int(m.group(2)))
                if d:
                    found.append((d, m.start(), m.end()))
        elif m.group(4) and m.group(5) and m.group(6):
            mon = MONTHS_EN.get(m.group(5).lower()[:3])
            if mon:
                d = _safe_date(int(m.group(6)), mon, int(m.group(4)))
                if d:
                    found.append((d, m.start(), m.end()))
        elif m.group(7) and m.group(8):
            mon = MONTHS_EN.get(m.group(7).lower()[:3])
            if mon:
                d = _safe_date(_PLACEHOLDER_YEAR, mon, int(m.group(8)))
                if d:
                    found.append((d, m.start(), m.end()))
    return found


def _collect_dates(text: str) -> list[date]:
    return [d for d, _, _ in _find_dates(text)]


def _parse_relative_date(text: str, base_date: date) -> date | None:
    if "今天" in text:
        return base_date
    if "明天" in text:
        return base_date.fromordinal(base_date.toordinal() + 1)
    if "后天" in text:
        return base_date.fromordinal(base_date.toordinal() + 2)
    m = re.search(r"(?:本周|这周)\s*周?([一二三四五六日天])", text)
    if m:
        target = CHINESE_WEEKDAYS[m.group(1)]
        return base_date.fromordinal(base_date.toordinal() + (target - base_date.weekday()) % 7)
    m = re.search(r"(?:下周|下星期)\s*周?([一二三四五六日天])", text)
    if m:
        target = CHINESE_WEEKDAYS[m.group(1)]
        days = 7 + (target - base_date.weekday()) % 7
        return base_date.fromordinal(base_date.toordinal() + days)
    return None


def _infer_year(d: date, base_date: date) -> tuple[date, list[str]]:
    warnings: list[str] = []
    if d.year == _PLACEHOLDER_YEAR:
        d = d.replace(year=base_date.year)
        if d < base_date:
            d = d.replace(year=base_date.year + 1)
            warnings.append(f"日期 {d.month}月{d.day}日 已过，推断为明年 {d.year} 年")
        else:
            warnings.append(f"图上没有年份，使用 {base_date.year} 年")
    elif d.year > base_date.year + 1:
        warnings.append(f"日期 {d} 年份可疑")
    return d, warnings


def extract_date(text: str, base_date: date) -> tuple[date, list[str]] | None:
    warnings: list[str] = []
    candidates = _collect_dates(text)
    rel = _parse_relative_date(text, base_date)
    if rel:
        candidates.append(rel)
    if not candidates:
        return None
    seen: dict[tuple[int, int], date] = {}
    for c in candidates:
        key = (c.month, c.day)
        if key not in seen or c.year != _PLACEHOLDER_YEAR:
            seen[key] = c
    candidates = list(seen.values())
    result = None
    for c in candidates:
        if c.year != _PLACEHOLDER_YEAR:
            result = c
            break
    if result is None:
        result = candidates[0]
    result, year_warns = _infer_year(result, base_date)
    warnings.extend(year_warns)
    if len(candidates) > 1:
        warnings.append(f"识别到多个候选日期，已取第一个: {[str(c) for c in candidates]}")
    return result, warnings


_PERIODS = {"凌晨": 0, "上午": 0, "早上": 0, "中午": 12, "下午": 12, "晚上": 12}


def _hour_of_period(period: str, hour: int) -> int:
    if hour == 12:
        return 12
    return hour + (_PERIODS.get(period, 0) if period else 0)


def extract_time(text: str) -> tuple[time, time | None] | None:
    m = re.search(r"(\d{1,2}):(\d{2})\s*[-~—]\s*(\d{1,2}):(\d{2})", text)
    if m:
        return time(int(m.group(1)), int(m.group(2))), time(int(m.group(3)), int(m.group(4)))
    m = re.search(r"(?<!\d)(\d{1,2}):(\d{2})([ \t]*(?:am|pm|[ap]))?(?!\d)", text, re.IGNORECASE)
    if m:
        hour, minute = int(m.group(1)), int(m.group(2))
        suffix = (m.group(3) or "").strip().lower()
        if suffix in ("pm", "p") and hour < 12:
            hour += 12
        if suffix in ("am", "a") and hour == 12:
            hour = 0
        return time(hour, minute), None
    m = re.search(r"(\d{1,2})\s*(?:点|时)\s*(?:半|(\d{1,2})\s*分)?", text)
    if m:
        period_match = re.search(r"(凌晨|早上|上午|中午|下午|晚上)\s*(\d{1,2})\s*(?:点|时)", text)
        period = period_match.group(1) if period_match else ""
        hour = int(m.group(1))
        minute = int(m.group(2)) if m.group(2) else (30 if "半" in m.group(0) else 0)
        return time(_hour_of_period(period, hour), minute), None
    return None


_LOCATION_KEYWORDS = ("地点", "地址", "location", "venue", "@")


def _extract_title(text: str, lines: list[dict] | None) -> str:
    if lines:
        candidates = [l for l in lines if l.get("text") and not re.search(r"\d", l["text"])]
        if candidates:
            max_h = max(l.get("height", 0) for l in candidates)
            top = [l for l in candidates if l.get("height", 0) >= max_h * 0.8]
            return top[0]["text"].strip()
    for line in text.splitlines():
        line = line.strip()
        if line and not re.search(r"(\d{1,2}[:：]\d{2})|(\d+\s*月)|(月|日|号)", line):
            return line
    return text.strip().splitlines()[0].strip() if text.strip() else ""


def _extract_location(text: str) -> str:
    for line in text.splitlines():
        line = line.strip()
        if any(kw.lower() in line.lower() for kw in _LOCATION_KEYWORDS):
            line = re.sub(r"^(地点|地址|location|venue)\s*[:：]\s*", "", line, flags=re.IGNORECASE)
            line = line.lstrip("@").strip()
            if line:
                return line
    return ""


def _date_time_rows(text: str, base_date: date) -> list[tuple[date, time | None, time | None, str]]:
    dates = _find_dates(text)
    if not dates:
        return []
    rows: list[tuple[date, time | None, time | None, str]] = []
    for i, (d, ds, de) in enumerate(dates):
        next_start = dates[i + 1][1] if i + 1 < len(dates) else len(text)
        seg = text[de:next_start]
        d2, _ = _infer_year(d, base_date)
        t: time | None = None
        t_end: time | None = None
        rm = re.search(r"(\d{1,2}):(\d{2})\s*[-~—]\s*(\d{1,2}):(\d{2})", seg)
        if rm:
            t = time(int(rm.group(1)), int(rm.group(2)))
            t_end = time(int(rm.group(3)), int(rm.group(4)))
        else:
            tm = re.search(r"(?<!\d)(\d{1,2}):(\d{2})([ \t]*(?:am|pm|[ap]))?(?!\d)", seg, re.IGNORECASE)
            if tm:
                hour, minute = int(tm.group(1)), int(tm.group(2))
                suffix = (tm.group(3) or "").strip().lower()
                if suffix in ("pm", "p") and hour < 12:
                    hour += 12
                elif suffix in ("am", "a") and hour == 12:
                    hour = 0
                t = time(hour, minute)
        rows.append((d2, t, t_end, seg))
    return rows


def _row_title(seg: str, location: str) -> str:
    keep: list[str] = []
    loc_compact = location.replace(" ", "").lower()
    for raw in seg.splitlines():
        line = raw.strip()
        if not line:
            continue
        line = re.sub(r"^\d{1,2}(?=\s|$)\s*", "", line)
        line = re.sub(r"^(mon|tue|wed|thu|fri|sat|sun)\w*\s*", "", line, flags=re.IGNORECASE)
        line = re.sub(r"^\d{1,2}:\d{2}[ap]?m?\s*", "", line, flags=re.IGNORECASE)
        if not line:
            continue
        if any(kw in line.lower() for kw in _LOCATION_KEYWORDS):
            continue
        if loc_compact and line.replace(" ", "").lower() in loc_compact:
            continue
        keep.append(line)
    return " ".join(keep)


def parse_event(text: str, lines: list[dict] | None = None, base_date: datetime | None = None) -> Event:
    if base_date is None:
        base_date = datetime.now()
    warnings: list[str] = []
    start = end = None
    date_info = extract_date(text, base_date.date())
    if date_info:
        d, date_warns = date_info
        warnings.extend(date_warns)
        time_info = extract_time(text)
        if time_info:
            t, t_end = time_info
            start = datetime.combine(d, t)
            if t_end:
                end = datetime.combine(d, t_end)
        else:
            start = datetime.combine(d, time(0, 0))
            warnings.append("没有识别到时间，默认 0:00 开始")
    else:
        warnings.append("没有识别到日期，需要手动填写")
    if start and not end:
        end = start + timedelta(hours=2)
    return Event(
        title=_extract_title(text, lines),
        start=start,
        end=end,
        location=_extract_location(text),
        description=text,
        warnings=warnings,
    )


def parse_events(text: str, lines: list[dict] | None = None, base_date: datetime | None = None) -> list[Event]:
    if base_date is None:
        base_date = datetime.now()
    rows = _date_time_rows(text, base_date.date())
    dated = [(d, t, t_end, seg) for d, t, t_end, seg in rows if t]
    if len(dated) < 2:
        return [parse_event(text, lines, base_date)]
    location = _extract_location(text)
    events: list[Event] = []
    for d, t, t_end, seg in dated:
        start = datetime.combine(d, t)
        end = datetime.combine(d, t_end) if t_end else start + timedelta(hours=2)
        title = _row_title(seg, location) or _extract_title(text, lines)
        events.append(Event(
            title=title,
            start=start,
            end=end,
            location=location,
            description=seg.strip(),
        ))
    return events
