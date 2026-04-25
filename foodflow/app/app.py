import time
import json
from fastapi import FastAPI, BackgroundTasks, Request
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from dotenv import load_dotenv
from pathlib import Path

from foodflow.core.settings import get_settings

# Keep using existing demo modules for now (we'll refactor them next).
from database import init_db, get_surplus_items, get_stats, get_last_rescue, get_recent_running_rescue, cleanup_stale_running_rescues
from database import get_rescue, get_rescues, get_pickups, get_inventory, get_volunteers, reset_demo_state, set_all_volunteers_available
from agent import run_agent
from report import generate_esg_report

# Force-load `.env` so the UI always reflects current keys.
load_dotenv(dotenv_path=Path(__file__).resolve().parents[2] / ".env", override=True)

settings = get_settings()

app = FastAPI(title=settings.app_name, version=settings.version)
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")


@app.on_event("startup")
async def startup():
    init_db()
    try:
        cleaned = cleanup_stale_running_rescues(max_age_seconds=90)
        if cleaned:
            print(f"🧹 Cleaned {cleaned} stale running rescues")
    except Exception as e:
        print(f"[WARN] Failed to cleanup stale rescues: {e}")
    print("🌿 FoodFlow AI started")


@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    last_rescue = get_last_rescue()
    last_result = None
    if last_rescue and last_rescue.get("result_json"):
        try:
            last_result = json.loads(last_rescue["result_json"])
        except Exception:
            last_result = {"raw": last_rescue["result_json"]}

    return templates.TemplateResponse(request, "dashboard.html", {
        "request": request,
        "stats": get_stats(),
        "surplus": get_surplus_items(),
        "last_rescue": last_rescue,
        "last_result": last_result,
        "demo_token": settings.demo_token,
        "llm_ready": bool(settings.anthropic_api_key),
    })


@app.get("/api/stats")
async def api_stats():
    return get_stats()


@app.get("/api/surplus")
async def api_surplus():
    return get_surplus_items()


@app.post("/api/trigger/{location_id}")
async def trigger_rescue(location_id: str, background_tasks: BackgroundTasks, request: Request):
    if settings.demo_token:
        provided = request.headers.get("x-demo-token") or request.query_params.get("token")
        if provided != settings.demo_token:
            return JSONResponse(status_code=401, content={"error": "unauthorized"})
    elif not settings.anthropic_api_key:
        return JSONResponse(status_code=400, content={"error": "Missing ANTHROPIC_API_KEY"})

    location_map = {
        "cornell_statler": {"name": "Cornell Statler Hall", "lat": 42.4467, "lng": -76.4851},
        "cornell_rpcc":    {"name": "Cornell RPCC Dining",  "lat": 42.4534, "lng": -76.4758},
    }
    loc = location_map.get(location_id, {"name": location_id, "lat": 42.4467, "lng": -76.4851})

    existing = get_recent_running_rescue(location_id, window_seconds=120)
    if existing:
        return {"status": "already_running", "location": loc["name"], "rescue_id": existing["rescue_id"]}

    rescue_id = f"rescue_{location_id}_{int(time.time())}"

    def _run():
        run_agent({
            "rescue_id": rescue_id,
            "location_id": location_id,
            "location_name": loc["name"],
            "lat": loc["lat"],
            "lng": loc["lng"],
        })

    background_tasks.add_task(_run)
    return {"status": "agent_started", "location": loc["name"], "rescue_id": rescue_id}


@app.get("/api/report")
async def download_report(request: Request):
    if settings.demo_token:
        provided = request.headers.get("x-demo-token") or request.query_params.get("token")
        if provided != settings.demo_token:
            return JSONResponse(status_code=401, content={"error": "unauthorized"})

    path = generate_esg_report()
    return FileResponse(path, media_type="application/pdf", filename="FoodFlow_ESG_Report.pdf")


@app.get("/health")
async def health():
    return {"status": "ok", "anthropic_configured": bool(settings.anthropic_api_key)}


@app.get("/api/rescues/{rescue_id}")
async def api_rescue(rescue_id: str):
    r = get_rescue(rescue_id)
    if not r:
        return JSONResponse(status_code=404, content={"error": "not_found"})
    return r


def _require_demo_token(request: Request):
    if not settings.demo_token:
        return None
    provided = request.headers.get("x-demo-token") or request.query_params.get("token")
    if provided != settings.demo_token:
        return JSONResponse(status_code=401, content={"error": "unauthorized"})
    return None


@app.post("/api/admin/reset")
async def api_admin_reset(request: Request):
    auth = _require_demo_token(request)
    if auth:
        return auth
    return reset_demo_state()


@app.post("/api/admin/volunteers/reset")
async def api_admin_reset_volunteers(request: Request):
    auth = _require_demo_token(request)
    if auth:
        return auth
    return set_all_volunteers_available()


@app.get("/ops", response_class=HTMLResponse)
async def ops_dashboard(request: Request, rescue_id: str | None = None):
    selected = get_rescue(rescue_id) if rescue_id else None
    selected_result = None
    if selected and selected.get("result_json"):
        try:
            selected_result = json.loads(selected["result_json"])
        except Exception:
            selected_result = {"raw": selected["result_json"]}
    return templates.TemplateResponse(request, "ops.html", {
        "request": request,
        "rescues": get_rescues(100),
        "pickups": get_pickups(200),
        "inventory": get_inventory(100),
        "volunteers": get_volunteers(),
        "selected": selected,
        "selected_result": selected_result,
        "demo_token": settings.demo_token,
    })


@app.get("/pitch", response_class=HTMLResponse)
async def pitch(request: Request):
    last_rescue = get_last_rescue()
    last_result = None
    if last_rescue and last_rescue.get("result_json"):
        try:
            last_result = json.loads(last_rescue["result_json"])
        except Exception:
            last_result = {"raw": last_rescue["result_json"]}

    return templates.TemplateResponse(request, "pitch.html", {
        "request": request,
        "model_name": settings.anthropic_model,
        "stats": get_stats(),
        "surplus": get_surplus_items(),
        "last_rescue": last_rescue,
        "last_result": last_result or {},
        "demo_token": settings.demo_token,
    })

