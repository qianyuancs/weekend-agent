from __future__ import annotations


def get_ride_options(origin: str, destination: str, minutes: int, mode: str = "打车") -> dict:
    base_price = max(12, round(minutes * 1.8))
    is_walk = "步行" in mode or minutes <= 8
    options = [
        {
            "id": "express",
            "name": "快车",
            "eta_minutes": 4,
            "price": base_price,
            "tag": "最快应答",
            "selected": True,
        },
        {
            "id": "comfort",
            "name": "优享",
            "eta_minutes": 6,
            "price": round(base_price * 1.35),
            "tag": "舒适车型",
            "selected": False,
        },
        {
            "id": "premier",
            "name": "专车",
            "eta_minutes": 8,
            "price": round(base_price * 1.9),
            "tag": "安静空间",
            "selected": False,
        },
        {
            "id": "six_seat",
            "name": "六座商务",
            "eta_minutes": 10,
            "price": round(base_price * 2.4),
            "tag": "适合多人",
            "selected": False,
        },
    ]

    if is_walk:
        options.insert(
            0,
            {
                "id": "walk",
                "name": "步行",
                "eta_minutes": 0,
                "price": 0,
                "tag": "距离较近",
                "selected": True,
            },
        )
        options = [{**item, "selected": item["id"] == "walk"} for item in options]

    return {
        "origin": origin,
        "destination": destination,
        "mode": mode,
        "estimated_minutes": minutes,
        "recommended_option": options[0],
        "options": options,
        "mock_didi_url": f"/mock/didi?from={origin}&to={destination}",
        "future_real_url_field": "didi_deeplink",
        "future_api": "/api/ride/options",
        "notice": "演示环境只生成 Mock 车型和价格，不会真实叫车。",
    }
