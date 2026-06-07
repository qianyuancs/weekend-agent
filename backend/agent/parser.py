from __future__ import annotations

import re
from copy import deepcopy
from datetime import datetime, timedelta
from typing import Any

CN_NUMBERS = {
    "一": 1,
    "二": 2,
    "两": 2,
    "三": 3,
    "四": 4,
    "五": 5,
    "六": 6,
    "七": 7,
    "八": 8,
    "九": 9,
    "十": 10,
}

KEYWORD_RULES: dict[str, list[str]] = {
    "distance_near": ["附近", "近一点", "别太远", "不太远", "不远", "少走路", "不想走"],
    "indoor": ["室内", "下雨", "雨天", "太晒", "高温", "商场里"],
    "kid": ["孩子", "小孩", "亲子", "儿童", "5岁", "五岁"],
    "social": ["朋友", "女生", "男生", "社交", "聊天", "聚会"],
    "relax": ["放松", "不累", "轻松", "慢一点", "休息"],
    "art": ["画展", "展览", "美术馆", "艺术", "博物馆"],
    "expo": ["博览会", "展会", "市集", "快闪", "活动"],
    "game": ["游戏", "桌游", "密室", "电玩", "剧本杀"],
    "food_japanese": ["日料", "日本菜", "寿司"],
    "food_hotpot": ["火锅"],
    "budget": ["预算", "便宜", "省钱", "性价比"],
}


def _to_int(value: str | None, default: int) -> int:
    if not value:
        return default
    if value.isdigit():
        return int(value)
    return CN_NUMBERS.get(value, default)


def _has_any(message: str, key: str) -> bool:
    return any(word in message for word in KEYWORD_RULES[key])


def _extract_budget(message: str) -> int:
    match = re.search(r"(?:预算|总价|控制在|不超过|别超过)?\s*(\d{2,5})\s*(?:元|块|以内|以下)", message)
    return int(match.group(1)) if match else 800


def _extract_duration(message: str) -> tuple[int, int]:
    range_match = re.search(r"(\d+)\s*[-到至]\s*(\d+)\s*个?小时", message)
    if range_match:
        return int(range_match.group(1)), int(range_match.group(2))
    single_match = re.search(r"(\d+)\s*个?小时", message)
    if single_match:
        hours = int(single_match.group(1))
        return max(1, hours - 1), hours + 1
    return 4, 6


def _extract_date(message: str, current: datetime) -> str:
    if "明天" in message:
        return (current + timedelta(days=1)).date().isoformat()
    if "后天" in message:
        return (current + timedelta(days=2)).date().isoformat()
    return current.date().isoformat()


def _extract_start_time(message: str) -> str:
    time_match = re.search(r"(\d{1,2})\s*[:点]\s*(\d{0,2})", message)
    if time_match:
        hour = int(time_match.group(1))
        minute = int(time_match.group(2) or 0)
        if any(word in message for word in ["下午", "晚上"]) and hour < 12:
            hour += 12
        return f"{hour:02d}:{minute:02d}"
    if "晚上" in message:
        return "18:00"
    if "上午" in message:
        return "10:00"
    return "14:00"


def _extract_people(message: str) -> dict[str, Any]:
    adults = 1
    children = 0
    child_age = None

    if any(word in message for word in ["老婆", "妻子", "伴侣", "女朋友", "男朋友", "对象"]):
        adults += 1

    friend_match = re.search(r"([一二两三四五六七八九十\d]+)\s*个?(?:朋友|同学|女生|男生)", message)
    if friend_match:
        adults += _to_int(friend_match.group(1), 2)
    elif "朋友" in message:
        adults += 2

    child_match = re.search(r"(\d+)\s*岁", message)
    if _has_any(message, "kid") or child_match:
        children = 1
        child_age = int(child_match.group(1)) if child_match else 5

    people_match = re.search(r"([一二两三四五六七八九十\d]+)\s*个人", message)
    if people_match and children == 0:
        adults = max(adults, _to_int(people_match.group(1), adults))

    return {"adults": adults, "children": children, "child_age": child_age}


def keyword_match(message: str) -> dict[str, Any]:
    matched: dict[str, list[str]] = {}
    hit_count = 0
    for name, words in KEYWORD_RULES.items():
        hits = [word for word in words if word in message]
        if hits:
            matched[name] = hits
            hit_count += len(hits)

    preferences: list[str] = ["轻松"]
    if "kid" in matched:
        preferences.append("亲子友好")
    if "distance_near" in matched:
        preferences.extend(["不走远", "距离近"])
    if "indoor" in matched:
        preferences.append("室内")
    if "social" in matched:
        preferences.append("社交")
    if "relax" in matched:
        preferences.append("不费体力")
    if "art" in matched:
        preferences.extend(["画展", "艺术"])
    if "expo" in matched:
        preferences.extend(["博览会", "市集"])
    if "game" in matched:
        preferences.extend(["游戏", "朋友互动"])
    if "food_japanese" in matched:
        preferences.append("日料")
    if "food_hotpot" in matched:
        preferences.append("火锅")
    if "budget" in matched:
        preferences.append("预算友好")

    confidence = min(1.0, round((hit_count * 0.16) + (len(matched) * 0.08), 2))
    return {
        "matched_keywords": matched,
        "hit_count": hit_count,
        "confidence": confidence,
        "preferences": list(dict.fromkeys(preferences)),
    }


def apply_user_preferences(intent: dict[str, Any], user_preferences: dict[str, Any] | None) -> dict[str, Any]:
    if not user_preferences:
        intent["user_preferences"] = {
            "liked_tags": [],
            "disliked_tags": [],
            "food_preferences": [],
            "activity_preferences": [],
            "avoid_crowded": False,
            "require_indoor": False,
        }
        return intent

    liked = user_preferences.get("liked_tags", [])
    disliked = user_preferences.get("disliked_tags", [])
    food = user_preferences.get("food_preferences", [])
    activity = user_preferences.get("activity_preferences", [])

    intent["preferences"] = list(dict.fromkeys(intent["preferences"] + liked + food + activity))
    if user_preferences.get("budget"):
        intent["budget"] = int(user_preferences["budget"])
    if user_preferences.get("max_leg_minutes"):
        intent["constraints"]["max_leg_minutes"] = int(user_preferences["max_leg_minutes"])
    if user_preferences.get("require_indoor"):
        intent["constraints"]["require_indoor"] = True
        intent["preferences"] = list(dict.fromkeys(intent["preferences"] + ["室内"]))
    if user_preferences.get("avoid_crowded"):
        intent["preferences"] = list(dict.fromkeys(intent["preferences"] + ["不排队", "安静"]))

    intent["user_preferences"] = {
        "liked_tags": liked,
        "disliked_tags": disliked,
        "food_preferences": food,
        "activity_preferences": activity,
        "avoid_crowded": bool(user_preferences.get("avoid_crowded")),
        "require_indoor": bool(user_preferences.get("require_indoor")),
        "budget": user_preferences.get("budget"),
        "max_leg_minutes": user_preferences.get("max_leg_minutes"),
    }
    return intent


def _retrieval_mode(keyword_result: dict[str, Any]) -> str:
    return "database" if keyword_result["confidence"] >= 0.55 else "llm_reasoning"


def parse_user_intent(
    message: str,
    location: str,
    current_time: str | None = None,
    user_preferences: dict[str, Any] | None = None,
) -> dict[str, Any]:
    current = (
        datetime.fromisoformat(current_time)
        if current_time
        else datetime.now().replace(hour=9, minute=0, second=0, microsecond=0)
    )
    people = _extract_people(message)
    min_hours, max_hours = _extract_duration(message)
    keyword_result = keyword_match(message)
    preferences = keyword_result["preferences"]
    if people["children"] and "亲子友好" not in preferences:
        preferences.append("亲子友好")

    near = _has_any(message, "distance_near")
    very_near = any(word in message for word in ["不走路", "商场内", "越近越好"])

    intent = {
        "message": message,
        "location": location,
        "city": "北京" if "北京" in location else "北京",
        "date": _extract_date(message, current),
        "start_time": _extract_start_time(message),
        "duration": {"min_hours": min_hours, "max_hours": max_hours},
        "people": people,
        "budget": _extract_budget(message),
        "preferences": list(dict.fromkeys(preferences)),
        "keyword_matches": keyword_result["matched_keywords"],
        "keyword_confidence": keyword_result["confidence"],
        "retrieval_mode": _retrieval_mode(keyword_result),
        "parse_strategy": "keyword_first_database_if_confident_else_llm_reasoning",
        "constraints": {
            "max_leg_minutes": 14 if very_near else 22 if near else 30,
            "max_distance_km": 1.6 if very_near else 2.5 if near else 4.0,
            "require_indoor": "室内" in preferences,
            "meal_required": True,
        },
        "change_flags": [],
        "force_weather": "rain" if _has_any(message, "indoor") and "雨" in message else None,
        "rejected_plan_keys": [],
        "rejected_item_ids": [],
        "approved_item_ids": [],
        "approved_plan_id": None,
        "plan_reject_count": 0,
        "llm_reasoning_count": 0,
        "adjustment_direction": None,
    }
    return apply_user_preferences(intent, user_preferences)


def parse_feedback(
    feedback: str,
    old_intent: dict[str, Any],
    user_preferences: dict[str, Any] | None = None,
) -> tuple[dict[str, Any], list[str]]:
    intent = deepcopy(old_intent)
    changes: list[str] = []
    intent["message"] = f"{old_intent['message']}；追加要求：{feedback}"

    keyword_result = keyword_match(feedback)
    if keyword_result["matched_keywords"]:
        intent["keyword_matches"] = {
            **intent.get("keyword_matches", {}),
            **keyword_result["matched_keywords"],
        }
        intent["keyword_confidence"] = max(intent.get("keyword_confidence", 0), keyword_result["confidence"])

    budget_match = re.search(r"(\d{2,5})\s*(?:元|块|以内|以下)", feedback)
    if budget_match:
        intent["budget"] = int(budget_match.group(1))
        changes.append(f"预算调整为 {intent['budget']} 元以内")
    elif "便宜" in feedback or "预算" in feedback:
        intent["budget"] = max(300, round(intent["budget"] * 0.72))
        changes.append(f"预算收紧到约 {intent['budget']} 元")

    if _has_any(feedback, "distance_near"):
        intent["constraints"]["max_leg_minutes"] = 14
        intent["constraints"]["max_distance_km"] = 1.5
        intent["preferences"] = list(dict.fromkeys(intent["preferences"] + ["不走远", "距离近"]))
        changes.append("距离约束收紧为单段通勤 14 分钟以内")

    if "下雨" in feedback or "雨天" in feedback or "雨" in feedback:
        intent["force_weather"] = "rain"
        intent["constraints"]["require_indoor"] = True
        intent["preferences"] = list(dict.fromkeys(intent["preferences"] + ["室内"]))
        changes.append("天气切换为雨天，优先室内活动")

    if "换餐厅" in feedback or "餐厅" in feedback:
        intent["change_flags"] = list(dict.fromkeys(intent.get("change_flags", []) + ["换餐厅"]))
        changes.append("保留活动结构，优先替换餐厅")

    if "日料" in feedback or "日本菜" in feedback:
        intent["preferences"] = list(dict.fromkeys(intent["preferences"] + ["日料"]))
        intent["change_flags"] = list(dict.fromkeys(intent.get("change_flags", []) + ["换餐厅"]))
        changes.append("餐饮偏好调整为日料")

    if _has_any(feedback, "art") or _has_any(feedback, "expo"):
        intent["preferences"] = list(dict.fromkeys(intent["preferences"] + ["画展", "博览会", "艺术"]))
        intent["change_flags"] = list(dict.fromkeys(intent.get("change_flags", []) + ["换活动"]))
        changes.append("活动偏好增加展览/博览会，触发活动检索接口")

    if keyword_result["confidence"] < 0.35 and feedback:
        intent["retrieval_mode"] = "llm_reasoning"
        intent["llm_reasoning_count"] = int(intent.get("llm_reasoning_count", 0)) + 1
        changes.append("新增表达命中率较低，切换到大模型推理式重规划")

    intent = apply_user_preferences(intent, user_preferences or intent.get("user_preferences"))
    return intent, changes or ["已根据新反馈更新约束并重新校验方案"]
