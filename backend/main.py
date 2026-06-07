from __future__ import annotations

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from backend.agent.planner import PlanningAgent
from backend.schemas.plan import (
    BookingRequest,
    PlanActionRequest,
    PlanRequest,
    PreferenceUpdateRequest,
    RideOptionsRequest,
    ReplanRequest,
)
from backend.tools.event_search_tool import search_live_events
from backend.tools.ride_tool import get_ride_options
from backend.tools.weather_tool import get_weather

app = FastAPI(title="Weekend Agent API", version="0.2.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

agent = PlanningAgent()


@app.get("/api/health")
def health() -> dict:
    return {"ok": True, "service": "weekend-agent", "version": "0.2.0"}


@app.post("/api/plan")
def create_plan(request: PlanRequest) -> dict:
    return {
        "ok": True,
        "data": agent.create_plan(
            message=request.message,
            location=request.location,
            current_time=request.current_time,
            user_preferences=request.user_preferences,
        ),
    }


@app.post("/api/replan")
def replan(request: ReplanRequest) -> dict:
    try:
        data = agent.replan(request.session_id, request.feedback, request.user_preferences)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"ok": True, "data": data}


@app.post("/api/action")
def plan_action(request: PlanActionRequest) -> dict:
    try:
        data = agent.act_on_plan(
            session_id=request.session_id,
            plan_id=request.plan_id,
            action=request.action,
            item_id=request.item_id,
            item_type=request.item_type,
            adjustment_direction=request.adjustment_direction,
            user_preferences=request.user_preferences,
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"ok": True, "data": data}


@app.post("/api/preferences")
def update_preferences(request: PreferenceUpdateRequest) -> dict:
    try:
        data = agent.update_preferences(request.session_id, request.user_preferences)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"ok": True, "data": data}


@app.get("/api/poi/{poi_id}")
def poi_detail(poi_id: str) -> dict:
    try:
        data = agent.poi_detail(poi_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"ok": True, "data": data}


@app.get("/api/search/events")
def search_events(query: str = "北京 周末 画展 博览会", city: str = "北京") -> dict:
    weather = get_weather("2026-05-24", city)
    intent = {
        "preferences": query.split(),
        "people": {"adults": 2, "children": 0, "child_age": None},
        "constraints": {"max_distance_km": 4.0},
        "user_preferences": {"disliked_tags": []},
    }
    return {"ok": True, "data": {"provider": "mock_search_adapter", "items": search_live_events(intent, weather)}}


@app.post("/api/ride/options")
def ride_options(request: RideOptionsRequest) -> dict:
    return {
        "ok": True,
        "data": get_ride_options(
            origin=request.origin,
            destination=request.destination,
            minutes=request.minutes,
            mode=request.mode,
        ),
    }


@app.post("/api/book")
def book(request: BookingRequest) -> dict:
    try:
        data = agent.book_plan(request.session_id, request.plan_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"ok": True, "data": data}
