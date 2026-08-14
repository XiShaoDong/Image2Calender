from dataclasses import dataclass, field
from datetime import datetime

@dataclass
class Event:
    title: str = ""
    start: datetime | None = None
    end: datetime | None = None
    location: str = ""
    description: str = ""
    warnings: list[str] = field(default_factory=list)

from datetime import date

CHINESE_WEEKDAYS = {"一": 0, "二": 1, "三": 2, "四": 3, "五": 4, "六": 5, "日": 6, "天": 6}

MONTHS_EN = {
    "jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
    "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12,
}


def _collect_dates(text: str) -> list[date]:
    import re
    dates: list[date] = []
    for m in re.finditer(r"(\d{4})\s*年\s*(\d{1,2})\s*月\s*(\d{1,2})\s*[日号]?", text):
        dates.append(date(int(m.group(1)), int(m.group(2)), int(m.group(3))))
    for m in re.finditer(r"(?<!\d)(\d{1,2})\s*月\s*(\d{1,2})\s*[日号]?(?!\d)", text):
        dates.append(date(2000, int(m.group(1)), int(m.group(2))))
    for m in re.finditer(r"(?<!\d)(\d{4})[/.\-](\d{1,2})[/.\-](\d{1,2})(?!\d)", text):
        dates.append(date(int(m.group(1)), int(m.group(2)), int(m.group(3))))
    for m in re.finditer(r"(?<!\d)(\d{1,2})/(\d{1,2})(?!\d)", text):
        dates.append(date(2000, int(m.group(1)), int(m.group(2))))
    en_pattern = (
        r"(?<![A-Za-z])([A-Za-z]{3,9})\s+(\d{1,2}),?\s+(\d{4})(?!\d)"
        r"|(?<!\d)(\d{1,2})\s+([A-Za-z]{3,9})\s+(\d{4})(?!\d)"
        r"|(?<![A-Za-z])([A-Za-z]{3,9})\s+(\d{1,2})(?!\d)"
    )
    for m in re.finditer(en_pattern, text):
        if m.group(1) and m.group(2) and m.group(3):
            dates.append(date(int(m.group(3)), MONTHS_EN[m.group(1).lower()[:3]], int(m.group(2))))
        elif m.group(4) and m.group(5) and m.group(6):
            dates.append(date(int(m.group(6)), MONTHS_EN[m.group(5).lower()[:3]], int(m.group(4))))
        elif m.group(7) and m.group(8):
            dates.append(date(2000, MONTHS_EN[m.group(7).lower()[:3]], int(m.group(8))))
    return dates


def _parse_relative_date(text: str, base_date: date) -> date | None:
    import re
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
        if key not in seen or c.year != 2000:
            seen[key] = c
    candidates = list(seen.values())
    result = None
    for c in candidates:
        if c.year != 2000:
            result = c
            break
    if result is None:
        result = candidates[0]
    if result.year == 2000:
        result = result.replace(year=base_date.year)
        if result < base_date:
            result = result.replace(year=base_date.year + 1)
            warnings.append(f"日期 {result.month}月{result.day}日 已过，推断为明年 {result.year} 年")
        else:
            warnings.append(f"图上没有年份，使用 {base_date.year} 年")
    elif result.year > base_date.year + 1:
        warnings.append(f"日期 {result} 年份可疑")
    elif result.year == base_date.year and result < base_date:
        result = result.replace(year=base_date.year + 1)
        warnings.append(f"日期 {result} 已过，推断为明年 {result.year} 年")
    if len(candidates) > 1:
        warnings.append(f"识别到多个候选日期，已取第一个: {[str(c) for c in candidates]}")
    return result, warnings


from datetime import time

_PERIODS = {"凌晨": 0, "上午": 0, "早上": 0, "中午": 12, "下午": 12, "晚上": 12}


def _hour_of_period(period: str, hour: int) -> int:
    if hour == 12:
        return 12
    return hour + (_PERIODS.get(period, 0) if period else 0)


def extract_time(text: str) -> tuple[time, time | None] | None:
    import re
    m = re.search(r"(\d{1,2}):(\d{2})\s*[-~—]\s*(\d{1,2}):(\d{2})", text)
    if m:
        return time(int(m.group(1)), int(m.group(2))), time(int(m.group(3)), int(m.group(4)))
    m = re.search(r"(?<!\d)(\d{1,2}):(\d{2})\s*(?:am|pm)?(?!\d)", text, re.IGNORECASE)
    if m:
        hour, minute = int(m.group(1)), int(m.group(2))
        suffix = re.search(r"(\d{1,2}):(\d{2})\s*(am|pm)", text, re.IGNORECASE)
        if suffix and suffix.group(3).lower() == "pm" and hour < 12:
            hour += 12
        if suffix and suffix.group(3).lower() == "am" and hour == 12:
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


import re
from datetime import datetime, timedelta

_LOCATION_KEYWORDS = ("地点", "地址", "venue", "@")


def _extract_title(text: str, lines: list[dict] | None) -> str:
    if lines:
        candidates = [l for l in lines if l.get("text") and not re.search(r"\d", l["text"])]
        if candidates:
            best = max(candidates, key=lambda l: l.get("height", 0))
            return best["text"].strip()
    for line in text.splitlines():
        line = line.strip()
        if line and not re.search(r"(\d{1,2}[:：]\d{2})|(\d+\s*月)|(月|日|号)", line):
            return line
    return text.strip().splitlines()[0].strip() if text.strip() else ""


def _extract_location(text: str) -> str:
    for line in text.splitlines():
        line = line.strip()
        if any(kw.lower() in line.lower() for kw in _LOCATION_KEYWORDS):
            line = re.sub(r"^(地点|地址|venue)\s*[:：]\s*", "", line, flags=re.IGNORECASE)
            line = line.lstrip("@").strip()
            if line:
                return line
    return ""


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
