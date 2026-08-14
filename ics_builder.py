from datetime import datetime
from uuid import uuid4

from parser import Event


def _dt(value: datetime) -> str:
    return value.strftime("%Y%m%dT%H%M%S")


def _fold(line: str) -> str:
    if len(line) <= 75:
        return line
    return line[:75] + "\r\n " + line[75:]


def _dt_line(prop: str, value: datetime, tzid: str | None) -> str:
    if tzid:
        return f"{prop};TZID={tzid}:{_dt(value)}"
    return f"{prop}:{_dt(value)}"


def build_ics(events: list[Event], tzid: str | None = None) -> str:
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
            parts.append(_dt_line("DTSTART", ev.start, tzid))
        if ev.end:
            parts.append(_dt_line("DTEND", ev.end, tzid))
        if ev.title:
            parts.append(_fold(f"SUMMARY:{ev.title}"))
        if ev.location:
            parts.append(_fold(f"LOCATION:{ev.location}"))
        if ev.description:
            parts.append(_fold(f"DESCRIPTION:{ev.description.replace(chr(10), '\\n')}"))
        parts.append("END:VEVENT")
    parts.append("END:VCALENDAR")
    return "\r\n".join(parts) + "\r\n"
