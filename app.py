from datetime import datetime
from pathlib import Path

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from config import get_api_key, set_api_key, DEFAULT_CONFIG
from ocr import OcrApiError, OcrLimitError, ocr_image
from parser import Event, parse_events
from ics_builder import build_ics

app = FastAPI(title="poster2ics")
STATIC_DIR = Path(__file__).parent / "static"


class EventPayload(BaseModel):
    title: str = ""
    start: str | None = None
    end: str | None = None
    location: str = ""
    description: str = ""


class ConfigPayload(BaseModel):
    key: str


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
        item = {"filename": f.filename or "image.jpg", "text": "", "events": [], "error": None}
        try:
            result = ocr_image(data, key)
            evs = parse_events(result.text, lines=result.lines)
            item["text"] = result.text
            item["events"] = [e.__dict__ for e in evs]
        except OcrLimitError as e:
            item["error"] = str(e)
        except OcrApiError as e:
            item["error"] = str(e)
        items.append(item)
    return {"items": items}


@app.post("/api/ics")
def api_ics(payloads: list[EventPayload]):
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
    content = build_ics(events)
    return Response(
        content=content,
        media_type="text/calendar",
        headers={"Content-Disposition": "attachment; filename=events.ics"},
    )


@app.get("/api/config")
def api_config_get():
    return {"has_key": bool(get_api_key(DEFAULT_CONFIG))}


@app.post("/api/config")
def api_config_set(payload: ConfigPayload):
    set_api_key(payload.key, DEFAULT_CONFIG)
    return {"ok": True}


if not STATIC_DIR.exists():
    STATIC_DIR.mkdir()
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
