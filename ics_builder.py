from datetime import datetime
from uuid import uuid4

from parser import Event

TZID = "Asia/Shanghai"


def _dt(value: datetime) -> str:
    return value.strftime("%Y%m%dT%H%M%S")


def _fold(line: str) -> str:
    if len(line) <= 75:
        return line
    return line[:75] + "\r\n " + line[75:]


def build_ics(events: list[Event]) -> str:
    parts = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//poster2ics//Image Calendar Import//CN",
        "CALSCALE:GREGORIAN",
    ]
    for ev in events:
        parts.append("BEGIN:VEVENT")
        parts.append(f"UID:{uuid4()}@poster2ics")
        if ev.start:
            parts.append(f"DTSTART;TZID={TZID}:{_dt(ev.start)}")
        if ev.end:
            parts.append(f"DTEND;TZID={TZID}:{_dt(ev.end)}")
        if ev.title:
            parts.append(_fold(f"SUMMARY:{ev.title}"))
        if ev.location:
            parts.append(_fold(f"LOCATION:{ev.location}"))
        if ev.description:
            parts.append(_fold(f"DESCRIPTION:{ev.description.replace(chr(10), '\\n')}"))
        parts.append("END:VEVENT")
    parts.append("END:VCALENDAR")
    return "\r\n".join(parts) + "\r\n"
