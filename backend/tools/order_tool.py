from __future__ import annotations

from datetime import datetime
from uuid import uuid4


def create_mock_order(plan: dict) -> dict:
    return {
        "order_id": f"MT-DEMO-{uuid4().hex[:8].upper()}",
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "amount": plan["total_cost"],
        "status": "mock_paid",
        "actions": ["活动票锁座", "餐厅预约", "行程发送给家人"],
    }
