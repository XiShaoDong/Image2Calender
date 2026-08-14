from datetime import datetime
import json
from pathlib import Path

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from config import get_api_key, get_llm_key, set_api_key, set_llm_key, DEFAULT_CONFIG
from llm import LlmUnavailableError, parse_with_llm
from ocr import OcrApiError, OcrLimitError, ocr_image
from parser import Event, parse_events
from ics_builder import build_ics

app = FastAPI(title="poster2ics")
STATIC_DIR = Path(__file__).parent / "static"
_last_events: list[Event] = []


class EventPayload(BaseModel):
    title: str = ""
    start: str | None = None
    end: str | None = None
    location: str = ""
    description: str = ""


class ConfigPayload(BaseModel):
    key: str | None = None
    llm_key: str | None = None


def _needs_llm(events: list[Event]) -> bool:
    return any(
        not e.start or not e.title or any("多个候选" in w for w in e.warnings)
        for e in events
    )


def _parse_with_fallback(text: str, lines: list[dict] | None) -> tuple[list[Event], str]:
    events = parse_events(text, lines=lines)
    llm_key = get_llm_key(DEFAULT_CONFIG)
    if llm_key and _needs_llm(events):
        try:
            llm_events = parse_with_llm(text, llm_key)
            if llm_events:
                return llm_events, "llm"
        except LlmUnavailableError:
            pass
    return events, "regex"


def _parse_dt(s: str | None) -> datetime | None:
    if not s:
        return None
    try:
        d = datetime.fromisoformat(s.replace("Z", "+00:00"))
    except ValueError:
        return None
    return d.replace(tzinfo=None) if d.tzinfo else d


@app.get("/")
def index():
    return FileResponse(STATIC_DIR / "index.html")


@app.post("/api/ocr")
async def api_ocr(files: list[UploadFile] = File(...)):
    key = get_api_key(DEFAULT_CONFIG)
    if not key:
        raise HTTPException(400, "未设置 OCR API key，请在页面右上角设置或配置环境变量 OCRSPACE_KEY")
    items = []
    for f in files:
        data = await f.read()
        item = {"filename": f.filename or "image.jpg", "text": "", "events": [], "source": "regex", "error": None}
        try:
            result = ocr_image(data, key)
            evs, source = _parse_with_fallback(result.text, result.lines)
            item["text"] = result.text
            item["events"] = [e.__dict__ for e in evs]
            item["source"] = source
        except OcrLimitError as e:
            item["error"] = str(e)
        except OcrApiError as e:
            item["error"] = str(e)
        items.append(item)
    return {"items": items}


@app.post("/api/ics")
def api_ics(payloads: list[EventPayload]):
    global _last_events
    events = []
    for p in payloads:
        ev = Event(
            title=p.title,
            start=_parse_dt(p.start),
            end=_parse_dt(p.end),
            location=p.location,
            description=p.description,
        )
        if ev.start:
            events.append(ev)
    _last_events = events
    return _ics_response(events)


@app.get("/api/ics")
def api_ics_get(e: str | None = None):
    events = _last_events
    if e:
        try:
            payloads = json.loads(e)
            parsed = []
            for p in payloads:
                ev = Event(
                    title=str(p.get("title") or ""),
                    start=_parse_dt(p.get("start")),
                    end=_parse_dt(p.get("end")),
                    location=str(p.get("location") or ""),
                    description=str(p.get("description") or ""),
                )
                if ev.start:
                    parsed.append(ev)
            if parsed:
                events = parsed
        except (json.JSONDecodeError, AttributeError, TypeError):
            pass
    return _ics_response(events)


def _ics_response(events: list[Event]) -> Response:
    return Response(
        content=build_ics(events),
        media_type="text/calendar",
        headers={"Content-Disposition": "attachment; filename=events.ics"},
    )


@app.get("/api/config")
def api_config_get():
    return {
        "has_key": bool(get_api_key(DEFAULT_CONFIG)),
        "ocr_key": get_api_key(DEFAULT_CONFIG),
        "llm_key": get_llm_key(DEFAULT_CONFIG),
    }


@app.post("/api/config")
def api_config_set(payload: ConfigPayload):
    ok = True
    if payload.key is not None:
        ok = set_api_key(payload.key, DEFAULT_CONFIG) and ok
    if payload.llm_key is not None:
        ok = set_llm_key(payload.llm_key, DEFAULT_CONFIG) and ok
    return {"ok": ok}


if not STATIC_DIR.exists():
    STATIC_DIR.mkdir()
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
