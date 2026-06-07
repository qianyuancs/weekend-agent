from __future__ import annotations

from .data_loader import load_json


def search_activities(intent: dict, weather: dict, limit: int = 8) -> list[dict]:
    activities = load_json("activities.json")
    scored: list[dict] = []
    child_age = intent["people"].get("child_age") or 0
    raining = weather["condition"] == "rain" or weather["rain_probability"] >= 70

    for item in activities:
        score = 40
        tags = set(item["tags"])

        if item["available"]:
            score += 18
        else:
            score -= 35
        disliked = set(intent.get("user_preferences", {}).get("disliked_tags", []))
        if intent["people"]["children"] and item["child_friendly"]:
            score += 20
        if intent["people"]["children"] and child_age < item["min_child_age"]:
            score -= 28
        if item["distance_km"] <= intent["constraints"]["max_distance_km"]:
            score += 12
        else:
            score -= 8
        if raining and item["weather_sensitive"]:
            score -= 32
        if raining and "室内" in tags:
            score += 18
        if "不走远" in intent["preferences"] and item["distance_km"] <= 1.5:
            score += 14
        if any(pref in tags for pref in intent["preferences"]):
            score += 12
        if "社交" in intent["preferences"] and ("朋友互动" in tags or "朋友聚会" in tags):
            score += 12
        if disliked & tags:
            score -= 24

        enriched = {**item, "kind": "activity", "score": score}
        scored.append(enriched)

    return sorted(scored, key=lambda value: value["score"], reverse=True)[:limit]
