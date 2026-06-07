from __future__ import annotations

from .data_loader import load_json


def search_live_events(intent: dict, weather: dict, limit: int = 8) -> list[dict]:
    """Mock search-engine adapter.

    In production this function can call a real search API, activity feed, or Meituan event index.
    The return shape intentionally matches activity_tool.search_activities so the planner can
    compose exhibitions, expos, and normal venues through the same planning path.
    """

    events = load_json("exhibitions.json")
    scored: list[dict] = []
    raining = weather["condition"] == "rain" or weather["rain_probability"] >= 70
    child_age = intent["people"].get("child_age") or 0
    preferences = set(intent.get("preferences", []))
    disliked = set(intent.get("user_preferences", {}).get("disliked_tags", []))

    for item in events:
        tags = set(item["tags"])
        score = 42
        if item["available"]:
            score += 18
        if preferences & tags:
            score += 20
        if {"画展", "博览会", "艺术", "市集"} & preferences:
            score += 18
        if intent["people"]["children"] and item["child_friendly"]:
            score += 14
        if intent["people"]["children"] and child_age < item["min_child_age"]:
            score -= 24
        if raining and not item["weather_sensitive"]:
            score += 14
        if item["distance_km"] <= intent["constraints"]["max_distance_km"]:
            score += 10
        else:
            score -= 8
        if disliked & tags:
            score -= 24

        enriched = {
            **item,
            "kind": "event",
            "score": score,
            "search_provider": "mock_search_adapter",
            "future_api": "/api/search/events?query=...",
        }
        scored.append(enriched)

    return sorted(scored, key=lambda value: value["score"], reverse=True)[:limit]
