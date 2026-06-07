from __future__ import annotations

from .data_loader import load_json


def get_weather(date: str, city: str = "北京", force_condition: str | None = None) -> dict:
    if force_condition:
        return {
            "date": date,
            "city": city,
            "condition": force_condition,
            "temperature": 22 if force_condition == "rain" else 26,
            "rain_probability": 85 if force_condition == "rain" else 25,
            "suggestion": "优先选择室内活动和近距离餐厅"
            if force_condition == "rain"
            else "适合短途室内外结合活动",
        }

    for item in load_json("weather.json"):
        if item["date"] == date and item["city"] == city:
            return item

    return {
        "date": date,
        "city": city,
        "condition": "cloudy",
        "temperature": 25,
        "rain_probability": 30,
        "suggestion": "适合短途室内外结合活动",
    }
