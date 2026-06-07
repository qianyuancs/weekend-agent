from __future__ import annotations

import os
from typing import Any


def build_item_adjustment_directive(
    plan: dict,
    item_id: str | None,
    item_type: str | None,
    direction: str | None,
) -> dict[str, Any]:
    """Normalize a node-level natural-language edit into a structured LLM task.

    The default provider is a mock/rule implementation so the demo can run without a key.
    A real LLM integration can replace this function's internals while keeping the planner
    contract stable.
    """

    timeline_item = next((item for item in plan.get("timeline", []) if item.get("id") == item_id), None)
    normalized_direction = (direction or "替换成更合适的项目").strip()
    target_type = _target_type(item_type, timeline_item)
    current_poi = _current_poi(plan, target_type)

    return {
        "provider": os.getenv("LLM_PROVIDER", "mock"),
        "model": os.getenv("LLM_MODEL", "mock-node-adjuster"),
        "api_key_env": "LLM_API_KEY",
        "mode": "mock_rules_until_api_key_configured",
        "target_type": target_type,
        "item_id": item_id,
        "item_type": item_type,
        "objective": _objective(normalized_direction),
        "direction": normalized_direction,
        "preserve_other_nodes": True,
        "current": {
            "id": current_poi.get("id") or item_id,
            "name": current_poi.get("name") or timeline_item.get("name") if timeline_item else item_id,
            "area": current_poi.get("area"),
            "distance_km": current_poi.get("distance_km"),
            "node_cost": timeline_item.get("cost") if timeline_item else None,
            "duration_minutes": timeline_item.get("duration_minutes") if timeline_item else None,
            "price": current_poi.get("avg_price") or current_poi.get("adult_price"),
        },
        "prompt": _prompt(target_type, normalized_direction, current_poi, timeline_item),
    }


def mock_generate_node_candidate(directive: dict[str, Any], intent: dict) -> dict | None:
    target_type = directive.get("target_type")
    objective = directive.get("objective")
    current = directive.get("current", {})
    area = current.get("area") or intent.get("location") or "朝阳大悦城"
    close_area = intent.get("location") or area
    close_distance = min(float(current.get("distance_km") or 1.2), 0.6)

    if target_type == "restaurant":
        if objective == "japanese":
            return _restaurant(
                "llm-r-japanese-budget",
                "平价亲子寿司食堂",
                "日料",
                area,
                min(close_distance + 0.3, 1.2),
                68,
                ["日料", "预算友好", "亲子友好", "可预约", "LLM生成"],
                ["日料", "寿司", "儿童套餐"],
            )
        if objective == "kid_friendly":
            return _restaurant(
                "llm-r-kid-menu",
                "儿童套餐小饭堂",
                "亲子简餐",
                close_area,
                close_distance,
                62,
                ["亲子友好", "儿童餐", "预算友好", "出餐快", "LLM生成"],
                ["儿童餐", "简餐"],
            )
        if objective == "quiet":
            return _restaurant(
                "llm-r-quiet-bistro",
                "安静小桌轻食馆",
                "轻食西餐",
                area,
                min(close_distance + 0.4, 1.3),
                72,
                ["安静聊天", "预算友好", "可预约", "轻松", "LLM生成"],
                ["西餐", "轻食"],
            )
        return _restaurant(
            "llm-r-cheap-family-set",
            "美团团购家庭简餐",
            "团购简餐",
            close_area if objective in {"cheaper", "closer"} else area,
            close_distance,
            58,
            ["预算友好", "亲子友好", "可预约", "出餐快", "LLM生成"],
            ["简餐", "儿童餐"],
        )

    if target_type == "activity":
        if objective in {"art", "indoor"}:
            return _activity(
                "llm-e-art-mini",
                "社区艺术快闪小展",
                "画展",
                close_area,
                close_distance,
                25,
                0,
                80,
                ["画展", "艺术", "室内", "亲子友好", "预算友好", "LLM生成"],
                "event",
            )
        if objective == "kid_friendly":
            return _activity(
                "llm-a-kid-science",
                "亲子科学小实验站",
                "室内亲子",
                close_area,
                close_distance,
                35,
                20,
                85,
                ["亲子友好", "室内", "互动", "预算友好", "LLM生成"],
                "activity",
            )
        return _activity(
            "llm-a-free-mall-quest",
            "商场免费探索任务",
            "室内探索",
            close_area,
            close_distance,
            0,
            0,
            70,
            ["免费", "预算友好", "亲子友好", "不走远", "室内", "LLM生成"],
            "activity",
        )

    return None


def _objective(direction: str) -> str:
    if any(word in direction for word in ["便宜", "预算", "省钱", "低价", "少花"]):
        return "cheaper"
    if any(word in direction for word in ["近", "少走", "少打车", "减少打车"]):
        return "closer"
    if any(word in direction for word in ["日料", "寿司", "日本"]):
        return "japanese"
    if any(word in direction for word in ["艺术", "画展", "展览", "博览"]):
        return "art"
    if any(word in direction for word in ["室内", "下雨", "雨天"]):
        return "indoor"
    if any(word in direction for word in ["孩子", "亲子", "儿童"]):
        return "kid_friendly"
    if any(word in direction for word in ["安静", "不吵"]):
        return "quiet"
    if any(word in direction for word in ["社交", "朋友", "聊天"]):
        return "social"
    return "open_rewrite"


def _target_type(item_type: str | None, timeline_item: dict | None) -> str:
    raw_type = item_type or (timeline_item or {}).get("type") or ""
    if raw_type == "restaurant":
        return "restaurant"
    if raw_type in {"activity", "event"}:
        return "activity"
    if raw_type == "transport":
        return "route"
    if raw_type == "break":
        return "break"
    return "activity"


def _current_poi(plan: dict, target_type: str) -> dict:
    if target_type == "restaurant":
        return plan.get("restaurant", {})
    if target_type == "activity":
        return plan.get("activity", {})
    return {}


def _prompt(target_type: str, direction: str, current_poi: dict, timeline_item: dict | None) -> str:
    current_name = current_poi.get("name") or (timeline_item or {}).get("name") or "当前节点"
    return (
        f"请只替换周末本地生活行程中的一个{target_type}节点；"
        f"当前节点是「{current_name}」；用户调整方向是「{direction}」。"
        "输出结构化候选，保留其他已赞同节点，并允许后续重算价格、时间和路线。"
    )


def _restaurant(
    item_id: str,
    name: str,
    category: str,
    area: str,
    distance_km: float,
    avg_price: int,
    tags: list[str],
    cuisine: list[str],
) -> dict:
    return {
        "id": item_id,
        "name": name,
        "category": category,
        "area": area,
        "distance_km": round(distance_km, 1),
        "avg_price": avg_price,
        "open_time": "10:00-22:00",
        "available": True,
        "wait_minutes": 8,
        "capacity_left": 12,
        "tags": tags,
        "cuisine": cuisine,
        "weather_safe": True,
        "child_friendly": True,
        "booking_required": True,
        "kind": "restaurant",
        "score": 140,
        "llm_reason": "mock_llm_generated_node",
    }


def _activity(
    item_id: str,
    name: str,
    category: str,
    area: str,
    distance_km: float,
    adult_price: int,
    child_price: int,
    duration_minutes: int,
    tags: list[str],
    kind: str,
) -> dict:
    return {
        "id": item_id,
        "name": name,
        "category": category,
        "area": area,
        "distance_km": round(distance_km, 1),
        "duration_minutes": duration_minutes,
        "adult_price": adult_price,
        "child_price": child_price,
        "open_time": "10:00-21:30",
        "available": True,
        "capacity_left": 36,
        "tags": tags,
        "min_child_age": 3,
        "weather_sensitive": False,
        "child_friendly": True,
        "booking_required": False,
        "kind": kind,
        "score": 142,
        "source": "mock_llm_adapter",
        "search_query": "LLM node adjustment candidate",
        "llm_reason": "mock_llm_generated_node",
    }
