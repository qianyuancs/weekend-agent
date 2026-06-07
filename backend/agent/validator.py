from __future__ import annotations

from backend.tools.booking_tool import check_availability


def _check(label: str, passed: bool, detail: str, warn: bool = False) -> dict:
    status = "pass" if passed else "warn" if warn else "fail"
    return {"label": label, "status": status, "detail": detail}


def validate_plan(plan: dict, intent: dict, weather: dict) -> dict:
    people_count = intent["people"]["adults"] + intent["people"]["children"]
    activity = plan["activity"]
    restaurant = plan["restaurant"]
    min_minutes = intent["duration"]["min_hours"] * 60
    max_minutes = intent["duration"]["max_hours"] * 60
    max_leg = intent["constraints"]["max_leg_minutes"]

    activity_availability = check_availability(activity, people_count)
    restaurant_availability = check_availability(restaurant, people_count)
    raining = weather["condition"] == "rain" or weather["rain_probability"] >= 70
    child_age = intent["people"].get("child_age") or 99

    checks = [
        _check(
            "预算",
            plan["total_cost"] <= intent["budget"],
            f"预计 {plan['total_cost']} 元 / 预算 {intent['budget']} 元",
        ),
        _check(
            "时长",
            min_minutes <= plan["total_minutes"] <= max_minutes,
            f"预计 {plan['total_duration']} / 目标 {intent['duration']['min_hours']}-{intent['duration']['max_hours']} 小时",
            warn=plan["total_minutes"] < min_minutes + 20,
        ),
        _check(
            "通勤",
            plan["max_leg_minutes"] <= max_leg,
            f"最长单段 {plan['max_leg_minutes']} 分钟 / 限制 {max_leg} 分钟",
        ),
        _check(
            "亲子适配",
            not intent["people"]["children"]
            or (activity["child_friendly"] and restaurant["child_friendly"] and child_age >= activity["min_child_age"]),
            "活动和餐厅均适合儿童" if activity["child_friendly"] and restaurant["child_friendly"] else "存在不适合儿童的节点",
        ),
        _check(
            "天气",
            not (raining and activity["weather_sensitive"]),
            "雨天已选择室内/不受天气影响的活动" if raining else weather["suggestion"],
        ),
        _check(
            "活动余位",
            activity_availability["available"],
            activity_availability["reason"],
        ),
        _check(
            "餐厅余位",
            restaurant_availability["available"],
            restaurant_availability["reason"],
        ),
    ]

    issues = [check["detail"] for check in checks if check["status"] == "fail"]
    warnings = [check["detail"] for check in checks if check["status"] == "warn"]
    return {"valid": not issues, "checks": checks, "issues": issues, "warnings": warnings}
