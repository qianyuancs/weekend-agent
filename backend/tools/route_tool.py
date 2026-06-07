from __future__ import annotations

from .data_loader import load_json


def get_route_time(origin: str, destination: str, distance_km: float | None = None) -> dict:
    if origin == destination:
        return {"from": origin, "to": destination, "minutes": 6, "mode": "步行"}

    routes = load_json("routes.json")
    for route in routes:
        if route["from"] == origin and route["to"] == destination:
            return route
        if route["from"] == destination and route["to"] == origin:
            return {
                "from": origin,
                "to": destination,
                "minutes": route["minutes"],
                "mode": route["mode"],
            }

    minutes = max(8, round((distance_km or 2.0) * 8 + 6))
    return {"from": origin, "to": destination, "minutes": minutes, "mode": "打车"}


def estimate_transport_cost(minutes: int) -> int:
    return max(12, round(minutes * 1.8))
