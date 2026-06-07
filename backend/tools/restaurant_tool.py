from __future__ import annotations

from .data_loader import load_json


def search_restaurants(intent: dict, limit: int = 8) -> list[dict]:
    restaurants = load_json("restaurants.json")
    scored: list[dict] = []
    budget = intent.get("budget") or 800
    people_count = intent["people"]["adults"] + intent["people"]["children"]
    max_meal_cost = budget * 0.68

    disliked = set(intent.get("user_preferences", {}).get("disliked_tags", []))
    for item in restaurants:
        score = 40
        tags = set(item["tags"]) | set(item.get("cuisine", []))

        if item["available"]:
            score += 18
        else:
            score -= 35
        if intent["people"]["children"] and item["child_friendly"]:
            score += 18
        if item["avg_price"] * people_count <= max_meal_cost:
            score += 12
        else:
            score -= 14
        if item["distance_km"] <= intent["constraints"]["max_distance_km"]:
            score += 12
        else:
            score -= 8
        if "日料" in intent["preferences"] and "日料" in tags:
            score += 24
        if "预算友好" in item["tags"] and budget <= 500:
            score += 16
        if any(pref in tags for pref in intent["preferences"]):
            score += 10
        if item["wait_minutes"] <= 20:
            score += 8
        if "换餐厅" in intent.get("change_flags", []):
            score += 4
        if intent.get("user_preferences", {}).get("avoid_crowded") and item["wait_minutes"] > 20:
            score -= 18
        if disliked & tags:
            score -= 24

        enriched = {**item, "kind": "restaurant", "score": score}
        scored.append(enriched)

    return sorted(scored, key=lambda value: value["score"], reverse=True)[:limit]
