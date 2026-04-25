import os
from fastapi import FastAPI, BackgroundTasks, Request
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from database import init_db, get_surplus_items, get_stats
from agent import run_agent
from report import generate_esg_report
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(title="FoodFlow AI", version="1.0.0")
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

_last_result: dict = {}

@app.on_event("startup")
async def startup():
    init_db()
    print("🌿 FoodFlow AI started")

@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "stats": get_stats(),
        "surplus": get_surplus_items(),
        "last_result": _last_result
    })

@app.get("/api/stats")
async def api_stats():
    return get_stats()

@app.get("/api/surplus")
async def api_surplus():
    return get_surplus_items()

@app.post("/api/trigger/{location_id}")
async def trigger_rescue(location_id: str, background_tasks: BackgroundTasks):
    location_map = {
        "cornell_statler": {"name": "Cornell Statler Hall", "lat": 42.4467, "lng": -76.4851},
        "cornell_rpcc":    {"name": "Cornell RPCC Dining",  "lat": 42.4534, "lng": -76.4758},
    }
    loc = location_map.get(location_id, {"name": location_id, "lat": 42.4467, "lng": -76.4851})

    def _run():
        global _last_result
        _last_result = run_agent({"location_id": location_id, "location_name": loc["name"],
                                   "lat": loc["lat"], "lng": loc["lng"]})

    background_tasks.add_task(_run)
    return {"status": "agent_started", "location": loc["name"]}

@app.get("/api/report")
async def download_report():
    path = generate_esg_report()
    return FileResponse(path, media_type="application/pdf", filename="FoodFlow_ESG_Report.pdf")

@app.get("/health")
async def health():
    return {"status": "ok", "model": "claude-sonnet-4-6"}
