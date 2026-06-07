from __future__ import annotations

from datetime import datetime
from uuid import uuid4


def check_availability(item: dict, people_count: int) -> dict:
    enough_capacity = item.get("capacity_left", 0) >= people_count
    available = bool(item.get("available")) and enough_capacity
    return {
        "item_id": item["id"],
        "available": available,
        "capacity_left": item.get("capacity_left", 0),
        "wait_minutes": item.get("wait_minutes", 0),
        "booking_required": item.get("booking_required", False),
        "reason": "可预约" if available else "余位不足或当前不可预约",
    }


def create_booking(plan: dict) -> dict:
    confirmation = f"BK-{datetime.now().strftime('%m%d%H%M')}-{uuid4().hex[:6].upper()}"
    return {
        "confirmation_id": confirmation,
        "status": "confirmed",
        "plan_id": plan["id"],
        "title": plan["title"],
        "reserved_items": [
            item["name"]
            for item in plan["timeline"]
            if item["type"] in {"activity", "event", "restaurant"}
        ],
        "message": "已完成 Mock 预约，演示环境不会产生真实订单。",
    }
