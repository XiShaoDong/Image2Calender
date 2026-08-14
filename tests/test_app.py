import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from fastapi.testclient import TestClient

from app import app


def _event_payload():
    return {
        "title": "测试活动",
        "start": "2026-08-15T19:00:00",
        "end": "2026-08-15T21:00:00",
        "location": "人民广场",
        "description": "说明",
    }


def test_root_serves_page():
    client = TestClient(app)
    resp = client.get("/")
    assert resp.status_code == 200
    assert "text/html" in resp.headers["content-type"]


def test_ics_endpoint_returns_calendar():
    client = TestClient(app)
    resp = client.post("/api/ics", json=[_event_payload()])
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("text/calendar")
    assert "attachment; filename=events.ics" in resp.headers["content-disposition"]
    assert "BEGIN:VCALENDAR" in resp.text
    assert "城市音乐节" not in resp.text  # 确保是测试事件
    assert "测试活动" in resp.text


def test_ics_endpoint_skips_missing_dates():
    client = TestClient(app)
    payload = _event_payload()
    payload["start"] = None
    payload["end"] = None
    resp = client.post("/api/ics", json=[payload])
    assert resp.status_code == 200
    assert "DTSTART" not in resp.text


def test_config_get():
    client = TestClient(app)
    resp = client.get("/api/config")
    assert resp.status_code == 200
    assert "has_key" in resp.json()


def test_config_post_saves(tmp_path, monkeypatch):
    monkeypatch.setattr("app.DEFAULT_CONFIG", tmp_path / "c.json")
    client = TestClient(app)
    resp = client.post("/api/config", json={"key": "abc-123"})
    assert resp.status_code == 200
    assert (tmp_path / "c.json").exists()
