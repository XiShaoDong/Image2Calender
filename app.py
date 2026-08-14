import hmac
from datetime import datetime
import json
from pathlib import Path
import re

from fastapi import FastAPI, File, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from config import (
    get_access_code,
    get_admin_password,
    get_api_key,
    get_llm_key,
    get_public_mode,
    set_access_code,
    set_api_key,
    set_llm_key,
    set_public_mode,
    DEFAULT_CONFIG,
)
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
    access_code: str | None = None
    public_mode: bool | None = None


def _access_ok(request: Request) -> bool:
    code = get_access_code(DEFAULT_CONFIG)
    if get_public_mode(DEFAULT_CONFIG) or not code:
        return True
    supplied = request.headers.get("x-access-code") or request.query_params.get("code")
    if not supplied:
        return False
    return hmac.compare_digest(supplied, code)


def _validate_access_code(code: str) -> str | None:
    if len(code) < 8:
        return "访问码至少 8 位"
    if not re.search(r"[A-Za-z]", code):
        return "访问码必须包含字母"
    if not re.search(r"\d", code):
        return "访问码必须包含数字"
    return None


def _require_access(request: Request) -> None:
    if not _access_ok(request):
        raise HTTPException(403, "需要访问码才能使用此服务")


def _admin_ok(request: Request) -> bool:
    pw = get_admin_password(DEFAULT_CONFIG)
    if not pw:
        return True
    supplied = request.headers.get("x-admin-password") or request.query_params.get("admin")
    return bool(supplied) and hmac.compare_digest(supplied, pw)


def _require_admin(request: Request) -> None:
    if not _admin_ok(request):
        raise HTTPException(403, "需要管理员密码")


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
async def api_ocr(request: Request, files: list[UploadFile] = File(...)):
    _require_access(request)
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
def api_ics(request: Request, payloads: list[EventPayload]):
    _require_access(request)
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
def api_ics_get(request: Request, e: str | None = None):
    _require_access(request)
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
def api_config_get(request: Request):
    _require_access(request)
    admin = _admin_ok(request)
    return {
        "has_key": bool(get_api_key(DEFAULT_CONFIG)),
        "ocr_key": get_api_key(DEFAULT_CONFIG) if admin else None,
        "llm_key": get_llm_key(DEFAULT_CONFIG) if admin else None,
        "public_mode": get_public_mode(DEFAULT_CONFIG),
        "access_code_set": bool(get_access_code(DEFAULT_CONFIG)),
        "admin_required": bool(get_admin_password(DEFAULT_CONFIG)),
    }


@app.post("/api/config")
def api_config_set(request: Request, payload: ConfigPayload):
    _require_admin(request)
    ok = True
    if payload.key is not None:
        ok = set_api_key(payload.key, DEFAULT_CONFIG) and ok
    if payload.llm_key is not None:
        ok = set_llm_key(payload.llm_key, DEFAULT_CONFIG) and ok
    if payload.access_code is not None:
        if not payload.access_code:
            ok = set_access_code("", DEFAULT_CONFIG) and ok
        else:
            err = _validate_access_code(payload.access_code)
            if err:
                raise HTTPException(400, err)
            ok = set_access_code(payload.access_code, DEFAULT_CONFIG) and ok
    if payload.public_mode is not None:
        ok = set_public_mode(payload.public_mode, DEFAULT_CONFIG) and ok
    return {"ok": ok}


if not STATIC_DIR.exists():
    STATIC_DIR.mkdir()
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
