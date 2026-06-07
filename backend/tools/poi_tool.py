from __future__ import annotations

from .data_loader import load_json


def _all_pois() -> list[dict]:
    restaurants = [{**item, "kind": "restaurant"} for item in load_json("restaurants.json")]
    activities = [{**item, "kind": "activity"} for item in load_json("activities.json")]
    events = [{**item, "kind": "event"} for item in load_json("exhibitions.json")]
    return restaurants + activities + events


def get_poi_detail(poi_id: str) -> dict | None:
    poi = next((item for item in _all_pois() if item["id"] == poi_id), None)
    if not poi:
        return None
    return format_poi_detail(poi)


def format_poi_detail(poi: dict) -> dict:
    kind_name = {"restaurant": "餐厅", "activity": "玩乐场馆", "event": "展览活动"}[poi["kind"]]
    base_price = poi.get("avg_price") or poi.get("adult_price") or 0
    rating_seed = sum(ord(char) for char in poi["name"]) % 8
    rating = round(4.2 + rating_seed / 10, 1)

    return {
        "id": poi["id"],
        "kind": poi["kind"],
        "kind_name": kind_name,
        "name": poi["name"],
        "category": poi["category"],
        "area": poi["area"],
        "distance_km": poi["distance_km"],
        "price": base_price,
        "rating": min(rating, 4.9),
        "open_time": poi["open_time"],
        "available": poi["available"],
        "capacity_left": poi.get("capacity_left", 0),
        "wait_minutes": poi.get("wait_minutes", 0),
        "tags": poi.get("tags", []),
        "booking_required": poi.get("booking_required", False),
        "child_friendly": poi.get("child_friendly", False),
        "mock_meituan_url": f"/mock/meituan/{poi['id']}",
        "future_real_url_field": "meituan_deeplink",
        "hero": {
            "title": poi["name"],
            "subtitle": f"{poi['area']} · {kind_name}",
            "tone": "mint" if poi["kind"] == "restaurant" else "sunset" if poi["kind"] == "event" else "sky",
        },
        "coupons": [
            {"title": "周末双人立减券", "price": max(9, round(base_price * 0.82)), "note": "Mock 团购券"},
            {"title": "到店预约保留位", "price": 0, "note": "演示环境不产生真实订单"},
        ],
        "reviews": [
            {"user": "本地生活体验官", "text": "位置方便，适合临时周末安排，动线比较顺。"},
            {"user": "亲子用户", "text": "孩子不容易无聊，大人也有坐下来休息的空间。"},
        ],
    }
