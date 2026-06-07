from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class PlanRequest(BaseModel):
    message: str = Field(..., min_length=2)
    location: str = "北京朝阳大悦城"
    current_time: str | None = None
    user_preferences: dict[str, Any] | None = None


class ReplanRequest(BaseModel):
    session_id: str
    feedback: str = Field(..., min_length=1)
    user_preferences: dict[str, Any] | None = None


class PlanActionRequest(BaseModel):
    session_id: str
    plan_id: str
    action: str = Field(..., pattern="^(approve_plan|reject_plan|approve_item|reject_item)$")
    item_id: str | None = None
    item_type: str | None = None
    adjustment_direction: str | None = None
    user_preferences: dict[str, Any] | None = None


class PreferenceUpdateRequest(BaseModel):
    session_id: str
    user_preferences: dict[str, Any] = Field(default_factory=dict)


class BookingRequest(BaseModel):
    session_id: str
    plan_id: str


class RideOptionsRequest(BaseModel):
    origin: str
    destination: str
    minutes: int = Field(..., ge=1)
    mode: str = "打车"


class ApiResponse(BaseModel):
    ok: bool = True
    data: dict[str, Any]


class TraceStep(BaseModel):
    step: str
    tool: str
    status: str = "done"
    detail: str
    data: dict[str, Any] | None = None
