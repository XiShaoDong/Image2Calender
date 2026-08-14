import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest

import llm


class _FakeResp:
    def __init__(self, body):
        self._body = body

    def raise_for_status(self):
        pass

    def json(self):
        return self._body


def test_parse_with_llm_ok(monkeypatch):
    body = {
        "candidates": [{"content": {"parts": [{"text": (
            '{"events": [{"title": "演唱会", "start": "2026-08-15T19:00:00", '
            '"end": "2026-08-15T21:00:00", "location": "人民广场", "description": ""}]}'
        )}]}}]
    }
    monkeypatch.setattr(llm.requests, "post", lambda *a, **k: _FakeResp(body))
    evs = llm.parse_with_llm("演唱会 8月15日 19:00", "fake-key", base_date=datetime(2026, 7, 1))
    assert len(evs) == 1
    assert evs[0].title == "演唱会"
    assert evs[0].start == datetime(2026, 8, 15, 19, 0)
    assert evs[0].end == datetime(2026, 8, 15, 21, 0)
    assert evs[0].location == "人民广场"


def test_parse_fences_stripped(monkeypatch):
    body = {
        "candidates": [{"content": {"parts": [{"text": (
            '```json\n{"events": [{"title": "A", "start": "2026-08-15T19:00:00"} ]}\n```'
        )}]}}]
    }
    monkeypatch.setattr(llm.requests, "post", lambda *a, **k: _FakeResp(body))
    evs = llm.parse_with_llm("A", "k", base_date=datetime(2026, 7, 1))
    assert len(evs) == 1 and evs[0].title == "A"


def test_parse_skips_invalid_events(monkeypatch):
    body = {
        "candidates": [{"content": {"parts": [{"text": (
            '{"events": ['
            '{"title": "坏日期", "start": "not-a-date"},'
            '{"title": "无开始", "start": null},'
            '{"title": "好事件", "start": "2026-08-15T19:00:00"}'
            "]}"
        )}]}}]
    }
    monkeypatch.setattr(llm.requests, "post", lambda *a, **k: _FakeResp(body))
    evs = llm.parse_with_llm("x", "k", base_date=datetime(2026, 7, 1))
    assert len(evs) == 1
    assert evs[0].title == "好事件"


def test_description_defaults_to_raw_text(monkeypatch):
    body = {
        "candidates": [{"content": {"parts": [{"text": (
            '{"events": [{"title": "A", "start": "2026-08-15T19:00:00"}]}'
        )}]}}]
    }
    monkeypatch.setattr(llm.requests, "post", lambda *a, **k: _FakeResp(body))
    evs = llm.parse_with_llm("原始文本", "k", base_date=datetime(2026, 7, 1))
    assert evs[0].description == "原始文本"


def test_description_kept_empty_for_multiple_events(monkeypatch):
    body = {
        "candidates": [{"content": {"parts": [{"text": (
            '{"events": [{"title": "A", "start": "2026-08-15T19:00:00"}, '
            '{"title": "B", "start": "2026-08-16T10:00:00"}]}'
        )}]}}]
    }
    monkeypatch.setattr(llm.requests, "post", lambda *a, **k: _FakeResp(body))
    evs = llm.parse_with_llm("整篇文本", "k", base_date=datetime(2026, 7, 1))
    assert len(evs) == 2
    assert evs[0].description == ""
    assert evs[1].description == ""


def test_llm_description_used_when_provided(monkeypatch):
    body = {
        "candidates": [{"content": {"parts": [{"text": (
            '{"events": [{"title": "A", "start": "2026-08-15T19:00:00", "description": "专属描述"}]}'
        )}]}}]
    }
    monkeypatch.setattr(llm.requests, "post", lambda *a, **k: _FakeResp(body))
    evs = llm.parse_with_llm("整篇文本", "k", base_date=datetime(2026, 7, 1))
    assert evs[0].description == "专属描述"


def test_network_error_raises_unavailable(monkeypatch):
    def boom(*a, **k):
        raise llm.requests.RequestException("boom")
    monkeypatch.setattr(llm.requests, "post", boom)
    with pytest.raises(llm.LlmUnavailableError):
        llm.parse_with_llm("x", "k")


def test_bad_json_raises_unavailable(monkeypatch):
    body = {"candidates": [{"content": {"parts": [{"text": "not json"}]}}]}
    monkeypatch.setattr(llm.requests, "post", lambda *a, **k: _FakeResp(body))
    with pytest.raises(llm.LlmUnavailableError):
        llm.parse_with_llm("x", "k")


def test_empty_events_raises_unavailable(monkeypatch):
    body = {"candidates": [{"content": {"parts": [{"text": '{"events": []}'}]}}]}
    monkeypatch.setattr(llm.requests, "post", lambda *a, **k: _FakeResp(body))
    with pytest.raises(llm.LlmUnavailableError):
        llm.parse_with_llm("x", "k")


def test_missing_candidates_raises_unavailable(monkeypatch):
    monkeypatch.setattr(llm.requests, "post", lambda *a, **k: _FakeResp({}))
    with pytest.raises(llm.LlmUnavailableError):
        llm.parse_with_llm("x", "k")


def test_prompt_contains_ocr_text(monkeypatch):
    captured = {}

    def fake_post(url, **kwargs):
        captured["prompt"] = kwargs["json"]["contents"][0]["parts"][0]["text"]
        return _FakeResp({"candidates": [{"content": {"parts": [{"text": '{"events": [{"title": "A", "start": "2026-08-15T19:00:00"}]}'}]}}]})

    monkeypatch.setattr(llm.requests, "post", fake_post)
    llm.parse_with_llm("特殊文本 XYZ123", "k", base_date=datetime(2026, 7, 1))
    assert "特殊文本 XYZ123" in captured["prompt"]
    assert "2026-07-01" in captured["prompt"]
