import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from ics_builder import build_ics
from parser import Event


def test_single_event_ics_structure():
    ev = Event(
        title="城市音乐节",
        start=datetime(2026, 8, 15, 19, 0),
        end=datetime(2026, 8, 15, 21, 0),
        location="人民广场",
        description="活动说明",
    )
    ics = build_ics([ev])
    assert ics.startswith("BEGIN:VCALENDAR")
    assert "BEGIN:VEVENT" in ics
    assert "END:VEVENT" in ics
    assert "END:VCALENDAR" in ics
    assert "DTSTART:20260815T190000" in ics
    assert "DTEND:20260815T210000" in ics
    assert "DTSTART;TZID=" not in ics
    assert "SUMMARY:城市音乐节" in ics
    assert "LOCATION:人民广场" in ics
    assert "DESCRIPTION:活动说明" in ics
    assert "UID:" in ics


def test_build_ics_with_client_timezone():
    ev = Event(title="A", start=datetime(2026, 8, 15, 17, 0), end=datetime(2026, 8, 15, 19, 0))
    ics = build_ics([ev], tzid="America/New_York")
    assert "DTSTART;TZID=America/New_York:20260815T170000" in ics
    assert "DTEND;TZID=America/New_York:20260815T190000" in ics


def test_multiple_events_combined():
    ev1 = Event(title="A", start=datetime(2026, 8, 1, 10, 0), end=datetime(2026, 8, 1, 12, 0))
    ev2 = Event(title="B", start=datetime(2026, 8, 2, 10, 0), end=datetime(2026, 8, 2, 12, 0))
    ics = build_ics([ev1, ev2])
    assert ics.count("BEGIN:VEVENT") == 2


def test_empty_fields_omitted():
    ev = Event(title="只有标题", start=datetime(2026, 8, 1, 10, 0))
    ics = build_ics([ev])
    assert "LOCATION" not in ics
    assert "DESCRIPTION" not in ics
