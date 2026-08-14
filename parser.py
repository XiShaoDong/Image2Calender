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
