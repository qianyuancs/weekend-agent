import type { AgentData, BookingResult, PoiDetail, RideOptions, UserPreferences } from "./types";

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? "http://127.0.0.1:8000";

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, options);
  if (!response.ok) {
    const text = await response.text();
    throw new Error(text || `Request failed: ${response.status}`);
  }

  const json = await response.json();
  return json.data as T;
}

async function post<T>(path: string, payload: unknown): Promise<T> {
  return request<T>(path, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
}

export function createPlan(
  message: string,
  location: string,
  userPreferences: UserPreferences,
): Promise<AgentData> {
  return post<AgentData>("/api/plan", {
    message,
    location,
    current_time: "2026-05-30 09:00",
    user_preferences: userPreferences,
  });
}

export function replan(
  sessionId: string,
  feedback: string,
  userPreferences: UserPreferences,
): Promise<AgentData> {
  return post<AgentData>("/api/replan", {
    session_id: sessionId,
    feedback,
    user_preferences: userPreferences,
  });
}

export function updatePreferences(
  sessionId: string,
  userPreferences: UserPreferences,
): Promise<AgentData> {
  return post<AgentData>("/api/preferences", {
    session_id: sessionId,
    user_preferences: userPreferences,
  });
}

export function planAction(payload: {
  sessionId: string;
  planId: string;
  action: "approve_plan" | "reject_plan" | "approve_item" | "reject_item";
  itemId?: string;
  itemType?: string;
  adjustmentDirection?: string;
  userPreferences: UserPreferences;
}): Promise<AgentData> {
  return post<AgentData>("/api/action", {
    session_id: payload.sessionId,
    plan_id: payload.planId,
    action: payload.action,
    item_id: payload.itemId,
    item_type: payload.itemType,
    adjustment_direction: payload.adjustmentDirection,
    user_preferences: payload.userPreferences,
  });
}

export function getPoiDetail(poiId: string): Promise<PoiDetail> {
  return request<PoiDetail>(`/api/poi/${poiId}`);
}

export function getRideOptions(payload: {
  origin: string;
  destination: string;
  minutes: number;
  mode: string;
}): Promise<RideOptions> {
  return post<RideOptions>("/api/ride/options", payload);
}

export function bookPlan(sessionId: string, planId: string): Promise<BookingResult> {
  return post<BookingResult>("/api/book", {
    session_id: sessionId,
    plan_id: planId,
  });
}
