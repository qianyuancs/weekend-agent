from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timedelta
from typing import Any
from uuid import uuid4

from backend.agent.llm_adapter import build_item_adjustment_directive, mock_generate_node_candidate
from backend.agent.parser import apply_user_preferences, parse_feedback, parse_user_intent
from backend.agent.validator import validate_plan
from backend.tools.activity_tool import search_activities
from backend.tools.booking_tool import create_booking
from backend.tools.event_search_tool import search_live_events
from backend.tools.order_tool import create_mock_order
from backend.tools.poi_tool import format_poi_detail, get_poi_detail
from backend.tools.restaurant_tool import search_restaurants
from backend.tools.route_tool import estimate_transport_cost, get_route_time
from backend.tools.weather_tool import get_weather


class PlanningAgent:
    def __init__(self) -> None:
        self.sessions: dict[str, dict[str, Any]] = {}

    def create_plan(
        self,
        message: str,
        location: str,
        current_time: str | None = None,
        user_preferences: dict[str, Any] | None = None,
    ) -> dict:
        intent = parse_user_intent(message, location, current_time, user_preferences)
        session_id = uuid4().hex
        response = self._build_response(session_id, intent, change_log=["已完成首次规划"])
        self._save_state(session_id, intent, response, history=[{"role": "user", "content": message}])
        return response

    def replan(self, session_id: str, feedback: str, user_preferences: dict[str, Any] | None = None) -> dict:
        state = self._state(session_id)
        intent, changes = parse_feedback(feedback, state["intent"], user_preferences)
        intent.pop("node_adjustment", None)
        preserve_activity, preserve_restaurant = self._approved_preserve_ids(intent, state.get("recommended_plan"))
        response = self._build_response(
            session_id,
            intent,
            change_log=changes,
            old_state=state,
            preserve_activity_id=preserve_activity,
            preserve_restaurant_id=preserve_restaurant,
        )
        self._save_state(session_id, intent, response, history=state["history"] + [{"role": "user", "content": feedback}])
        return response

    def update_preferences(self, session_id: str, user_preferences: dict[str, Any]) -> dict:
        state = self._state(session_id)
        intent = apply_user_preferences(deepcopy(state["intent"]), user_preferences)
        intent.pop("node_adjustment", None)
        preserve_activity, preserve_restaurant = self._approved_preserve_ids(intent, state.get("recommended_plan"))
        response = self._build_response(
            session_id,
            intent,
            change_log=["已更新用户偏好，并重新校验当前方案"],
            old_state=state,
            preserve_activity_id=preserve_activity,
            preserve_restaurant_id=preserve_restaurant,
        )
        self._save_state(session_id, intent, response, history=state["history"])
        return response

    def act_on_plan(
        self,
        session_id: str,
        plan_id: str,
        action: str,
        item_id: str | None = None,
        item_type: str | None = None,
        adjustment_direction: str | None = None,
        user_preferences: dict[str, Any] | None = None,
    ) -> dict:
        state = self._state(session_id)
        plan = self._find_plan(state["plans"], plan_id)
        intent = apply_user_preferences(deepcopy(state["intent"]), user_preferences or state["intent"].get("user_preferences"))
        if action != "reject_item":
            intent.pop("node_adjustment", None)

        if action == "approve_plan":
            intent["approved_plan_id"] = plan_id
            intent["rejected_plan_keys"] = [
                key for key in intent.get("rejected_plan_keys", []) if key != self._plan_key(plan)
            ]
            response = self._with_selected_plan(state["last_response"], plan_id, ["已赞同整套方案，方案进入待预约状态"])
            self._save_state(session_id, intent, response, history=state["history"])
            return response

        if action == "reject_plan":
            if intent.get("approved_plan_id") == plan_id:
                intent["approved_plan_id"] = None
            intent["rejected_plan_keys"] = list(dict.fromkeys(intent.get("rejected_plan_keys", []) + [self._plan_key(plan)]))
            intent["plan_reject_count"] = int(intent.get("plan_reject_count", 0)) + 1
            preserve_activity, preserve_restaurant = self._approved_preserve_ids(intent, plan)

            if adjustment_direction:
                self._apply_adjustment_direction(intent, adjustment_direction, "plan")
                change_log = [f"已按整体调整方向「{adjustment_direction}」重新推理方案"]
            elif intent["plan_reject_count"] >= 2:
                intent["retrieval_mode"] = "llm_reasoning"
                intent["llm_reasoning_count"] = int(intent.get("llm_reasoning_count", 0)) + 1
                change_log = ["已再次拒绝整套方案，切换到大模型推理路径生成新方案"]
            else:
                intent["retrieval_mode"] = "database"
                change_log = ["已拒绝当前方案，先在预设数据库类别里推出下一套方案"]

            response = self._build_response(
                session_id,
                intent,
                change_log=change_log,
                old_state=state,
                preserve_activity_id=preserve_activity,
                preserve_restaurant_id=preserve_restaurant,
            )
            self._save_state(session_id, intent, response, history=state["history"])
            return response

        if action == "approve_item":
            if item_id:
                intent["approved_item_ids"] = list(dict.fromkeys(intent.get("approved_item_ids", []) + [item_id]))
                intent["rejected_item_ids"] = self._without_id(intent.get("rejected_item_ids", []), item_id)
            response = self._mark_item_feedback(
                state["last_response"],
                plan_id,
                item_id,
                "approved",
                ["已赞同该项目；如果点错了，仍可直接改为拒绝"],
            )
            self._save_state(session_id, intent, response, history=state["history"])
            return response

        if action == "reject_item":
            if item_id:
                intent["approved_item_ids"] = self._without_id(intent.get("approved_item_ids", []), item_id)
                intent["rejected_item_ids"] = list(dict.fromkeys(intent.get("rejected_item_ids", []) + [item_id]))
            if adjustment_direction:
                self._apply_adjustment_direction(intent, adjustment_direction, item_type)
                directive = build_item_adjustment_directive(plan, item_id, item_type, adjustment_direction)
                intent["node_adjustment"] = directive
                self._apply_node_directive(intent, directive)

            preserve_activity, preserve_restaurant = self._approved_preserve_ids(intent, plan)
            if item_type == "restaurant":
                preserve_activity = preserve_activity or plan["activity"]["id"]
                change_log = ["已拒绝该餐厅，保留已赞同项目并重算价格、时间和路线"]
            elif item_type in {"activity", "event"}:
                preserve_restaurant = preserve_restaurant or plan["restaurant"]["id"]
                change_log = ["已拒绝该活动，保留已赞同项目并重算价格、时间和路线"]
            elif item_type == "transport":
                intent["constraints"]["max_leg_minutes"] = max(10, min(intent["constraints"]["max_leg_minutes"], 14))
                intent["constraints"]["max_distance_km"] = min(intent["constraints"]["max_distance_km"], 1.5)
                change_log = ["已拒绝该路段，通勤约束已收紧并重新规划"]
            else:
                change_log = ["已拒绝该项目，Agent 正在寻找替换项"]

            if adjustment_direction:
                directive = intent.get("node_adjustment", {})
                change_log.append(
                    f"调整方向「{adjustment_direction}」已转成节点级模型任务："
                    f"{directive.get('objective', 'open_rewrite')}"
                )

            response = self._build_response(
                session_id,
                intent,
                change_log=change_log,
                old_state=state,
                preserve_activity_id=preserve_activity,
                preserve_restaurant_id=preserve_restaurant,
            )
            self._save_state(session_id, intent, response, history=state["history"])
            return response

        raise ValueError(f"unsupported action: {action}")

    def book_plan(self, session_id: str, plan_id: str) -> dict:
        state = self._state(session_id)
        plan = self._find_plan(state["plans"], plan_id)
        booking = create_booking(plan)
        order = create_mock_order(plan)
        return {"booking": booking, "order": order}

    def poi_detail(self, poi_id: str) -> dict:
        detail = get_poi_detail(poi_id)
        if not detail:
            detail = self._session_poi_detail(poi_id)
        if not detail:
            raise KeyError("poi not found")
        return detail

    def _build_response(
        self,
        session_id: str,
        intent: dict,
        change_log: list[str],
        old_state: dict | None = None,
        preserve_activity_id: str | None = None,
        preserve_restaurant_id: str | None = None,
    ) -> dict:
        weather = get_weather(intent["date"], intent["city"], intent.get("force_weather"))
        mode = intent.get("retrieval_mode", "database")

        local_activities = search_activities(intent, weather)
        live_events = search_live_events(intent, weather)
        restaurants = search_restaurants(intent)

        if mode == "llm_reasoning":
            local_activities, live_events, restaurants = self._mock_llm_reasoning(
                intent,
                local_activities,
                live_events,
                restaurants,
            )

        activities = self._merge_activity_candidates(local_activities, live_events, intent)
        plans = self._compose_plans(
            intent,
            weather,
            activities,
            restaurants,
            old_state,
            preserve_activity_id,
            preserve_restaurant_id,
        )
        recommended = plans[0] if plans else None
        one_plan = [recommended] if recommended else []

        trace = [
            {
                "step": "01",
                "tool": "keyword_database_router",
                "status": "done",
                "detail": "关键词命中率高走数据库召回，命中率低或连续拒绝后走大模型推理",
                "data": {
                    "keyword_confidence": intent.get("keyword_confidence", 0),
                    "retrieval_mode": mode,
                    "matched": intent.get("keyword_matches", {}),
                },
            },
            {
                "step": "02",
                "tool": "candidate_retrieval",
                "status": "done",
                "detail": f"活动候选 {len(activities)} 个，餐厅候选 {len(restaurants)} 个；本次只返回 1 套方案",
                "data": {"activity_top": [item["name"] for item in activities[:3]]},
            },
            {
                "step": "03",
                "tool": "validator",
                "status": "done" if recommended else "warn",
                "detail": "已重算总价、时长、路线、天气、亲子适配和余位",
                "data": {"valid": recommended["valid"] if recommended else False},
            },
        ]
        if intent.get("node_adjustment"):
            trace.insert(
                2,
                {
                    "step": "02B",
                    "tool": "llm_node_adjustment_adapter",
                    "status": "done",
                    "detail": "节点级调整方向已转成结构化模型任务；当前默认使用 Mock LLM 生成/重排候选",
                    "data": {
                        "target_type": intent["node_adjustment"].get("target_type"),
                        "objective": intent["node_adjustment"].get("objective"),
                        "provider": intent["node_adjustment"].get("provider"),
                        "model": intent["node_adjustment"].get("model"),
                    },
                },
            )

        return {
            "session_id": session_id,
            "intent": intent,
            "weather": weather,
            "plans": one_plan,
            "recommended_plan": recommended,
            "trace": trace,
            "change_log": change_log,
            "summary": self._summary(recommended) if recommended else "没有可推荐方案，请放宽距离、预算或时间约束。",
            "suggested_terms": self._suggested_terms(intent),
            "routing": {
                "retrieval_mode": mode,
                "keyword_confidence": intent.get("keyword_confidence", 0),
                "plan_reject_count": intent.get("plan_reject_count", 0),
                "llm_reasoning_count": intent.get("llm_reasoning_count", 0),
            },
        }

    def _compose_plans(
        self,
        intent: dict,
        weather: dict,
        activities: list[dict],
        restaurants: list[dict],
        old_state: dict | None,
        preserve_activity_id: str | None,
        preserve_restaurant_id: str | None,
    ) -> list[dict]:
        rejected_items = set(intent.get("rejected_item_ids", []))
        rejected_plan_keys = set(intent.get("rejected_plan_keys", []))
        approved_items = set(intent.get("approved_item_ids", []))

        activities = [item for item in activities if item["id"] not in rejected_items]
        restaurants = [item for item in restaurants if item["id"] not in rejected_items]

        if preserve_activity_id:
            activities = [item for item in activities if item["id"] == preserve_activity_id] or activities
        if preserve_restaurant_id:
            restaurants = [item for item in restaurants if item["id"] == preserve_restaurant_id] or restaurants

        candidates: list[dict] = []
        fallback_candidates: list[dict] = []
        for activity in activities[:8]:
            for restaurant in restaurants[:8]:
                plan = self._compose_single_plan(intent, weather, activity, restaurant)
                validation = validate_plan(plan, intent, weather)
                plan.update(validation)
                plan["score"] = self._score(plan, activity, restaurant, approved_items, intent, old_state)
                if self._plan_key(plan) in rejected_plan_keys:
                    fallback_candidates.append(plan)
                else:
                    candidates.append(plan)

        ranked = self._rank(candidates, intent, old_state)
        if not ranked:
            ranked = self._rank(fallback_candidates, intent, old_state)
        return ranked

    def _compose_single_plan(self, intent: dict, weather: dict, activity: dict, restaurant: dict) -> dict:
        adults = intent["people"]["adults"]
        children = intent["people"]["children"]
        people_count = adults + children
        current = datetime.fromisoformat(f"{intent['date']}T{intent['start_time']}")
        start = current

        route_1 = get_route_time(intent["location"], activity["area"], activity["distance_km"])
        route_2 = get_route_time(activity["area"], restaurant["area"])
        route_3 = get_route_time(restaurant["area"], intent["location"], restaurant["distance_km"])
        transport_cost = sum(estimate_transport_cost(route["minutes"]) for route in [route_1, route_2, route_3])
        max_leg_minutes = max(route["minutes"] for route in [route_1, route_2, route_3])

        timeline: list[dict] = []

        def add_item(
            item_type: str,
            name: str,
            duration: int,
            note: str,
            cost: int = 0,
            poi: dict | None = None,
            route: dict | None = None,
        ) -> None:
            nonlocal current
            item_id = poi["id"] if poi else f"{item_type}-{len(timeline)}"
            timeline.append(
                {
                    "id": item_id,
                    "time": current.strftime("%H:%M"),
                    "type": item_type,
                    "name": name,
                    "duration_minutes": duration,
                    "duration_label": self._minutes_label(duration),
                    "note": note,
                    "cost": cost,
                    "poi_id": poi["id"] if poi else None,
                    "poi_kind": poi.get("kind") if poi else None,
                    "detail_url": f"/api/poi/{poi['id']}" if poi else None,
                    "actionable": True,
                    "feedback_status": "approved" if item_id in intent.get("approved_item_ids", []) else "pending",
                    "route": route,
                }
            )
            current += timedelta(minutes=duration)

        add_item(
            "transport",
            f"从 {intent['location']} 出发到 {activity['area']}",
            route_1["minutes"],
            f"{route_1['mode']}，预计 {route_1['minutes']} 分钟",
            estimate_transport_cost(route_1["minutes"]),
            route=route_1,
        )
        activity_cost = activity["adult_price"] * adults + activity["child_price"] * children
        add_item(
            activity.get("kind", "activity"),
            activity["name"],
            activity["duration_minutes"],
            f"{activity['category']}，{', '.join(activity['tags'][:3])}",
            activity_cost,
            poi=activity,
        )
        break_minutes, break_cost, break_note = self._break_node(intent, people_count)
        add_item("break", "甜品/休息缓冲", break_minutes, break_note, break_cost)
        add_item(
            "transport",
            f"前往 {restaurant['area']}",
            route_2["minutes"],
            f"{route_2['mode']}，预计 {route_2['minutes']} 分钟",
            estimate_transport_cost(route_2["minutes"]),
            route=route_2,
        )
        meal_cost = round(restaurant["avg_price"] * (adults + children * 0.6))
        add_item(
            "restaurant",
            restaurant["name"],
            90,
            f"{restaurant['category']}，等待约 {restaurant['wait_minutes']} 分钟",
            meal_cost,
            poi=restaurant,
        )
        add_item(
            "transport",
            f"返回 {intent['location']}",
            route_3["minutes"],
            f"{route_3['mode']}，预计 {route_3['minutes']} 分钟",
            estimate_transport_cost(route_3["minutes"]),
            route=route_3,
        )

        total_minutes = round((current - start).total_seconds() / 60)
        total_cost = activity_cost + break_cost + meal_cost + transport_cost
        plan_id = uuid4().hex[:10]

        return {
            "id": plan_id,
            "plan_key": f"{activity['id']}::{restaurant['id']}",
            "title": self._title(activity, weather, intent),
            "reason": self._reason(intent, activity, restaurant, weather),
            "activity": deepcopy(activity),
            "restaurant": deepcopy(restaurant),
            "timeline": timeline,
            "total_cost": total_cost,
            "total_minutes": total_minutes,
            "total_duration": self._minutes_label(total_minutes),
            "max_leg_minutes": max_leg_minutes,
            "transport_cost": transport_cost,
            "next_actions": ["预约活动", "预订餐厅", "发送给家人"],
            "feedback_status": "pending",
        }

    def _break_node(self, intent: dict, people_count: int) -> tuple[int, int, str]:
        directive = intent.get("node_adjustment") or {}
        if directive.get("target_type") != "break":
            return 45, 22 * people_count, "给孩子和大人留出恢复时间，也方便朋友聊天"

        objective = directive.get("objective")
        if objective == "cheaper":
            return 30, 8 * people_count, "按低成本方向改为便利店饮品/商场座椅短休"
        if objective in {"quiet", "kid_friendly"}:
            return 45, 18 * people_count, "按调整方向选择更安静、适合孩子恢复体力的休息点"
        return 35, 15 * people_count, "按节点级调整方向缩短休息并降低额外消费"

    def _mock_llm_reasoning(
        self,
        intent: dict,
        local_activities: list[dict],
        live_events: list[dict],
        restaurants: list[dict],
    ) -> tuple[list[dict], list[dict], list[dict]]:
        direction = intent.get("adjustment_direction") or ""
        node_directive = intent.get("node_adjustment") or {}
        llm_tags = ["新鲜感", "低决策成本", "更贴近用户反馈"]
        if any(word in direction for word in ["艺术", "展", "博览"]):
            intent["preferences"] = list(dict.fromkeys(intent["preferences"] + ["画展", "博览会", "艺术"]))
        if any(word in direction for word in ["安静", "不吵"]):
            intent["preferences"] = list(dict.fromkeys(intent["preferences"] + ["安静", "不排队"]))
        if any(word in direction for word in ["孩子", "亲子"]):
            intent["preferences"] = list(dict.fromkeys(intent["preferences"] + ["亲子友好"]))
        wants_cheaper = self._wants_cheaper(intent)
        wants_closer = self._wants_closer(intent)

        def boost(items: list[dict]) -> list[dict]:
            boosted = []
            for index, item in enumerate(items):
                score = item["score"] + max(0, 18 - index * 2)
                tags = set(item.get("tags", []))
                if tags & set(intent["preferences"]):
                    score += 18
                if wants_cheaper:
                    score += self._cheap_item_bonus(item)
                if wants_closer:
                    score -= round(item.get("distance_km", 0) * 8)
                boosted.append({**item, "score": score, "llm_reason": "mock_llm_rerank", "llm_tags": llm_tags})
            return sorted(boosted, key=lambda value: value["score"], reverse=True)

        local_activities = boost(local_activities)
        live_events = boost(live_events)
        restaurants = boost(restaurants)

        generated = mock_generate_node_candidate(node_directive, intent) if node_directive else None
        if generated and generated.get("kind") == "restaurant":
            restaurants = [generated] + [item for item in restaurants if item["id"] != generated["id"]]
        elif generated and generated.get("kind") == "event":
            live_events = [generated] + [item for item in live_events if item["id"] != generated["id"]]
        elif generated:
            local_activities = [generated] + [item for item in local_activities if item["id"] != generated["id"]]

        return local_activities, live_events, restaurants

    def _apply_adjustment_direction(self, intent: dict, direction: str, item_type: str | None) -> None:
        intent["adjustment_direction"] = direction
        intent["retrieval_mode"] = "llm_reasoning"
        intent["llm_reasoning_count"] = int(intent.get("llm_reasoning_count", 0)) + 1
        if item_type == "restaurant":
            intent["change_flags"] = list(dict.fromkeys(intent.get("change_flags", []) + ["换餐厅"]))
        elif item_type in {"activity", "event"}:
            intent["change_flags"] = list(dict.fromkeys(intent.get("change_flags", []) + ["换活动"]))
        if "便宜" in direction or "预算" in direction:
            intent["budget"] = max(300, round(intent["budget"] * 0.82))
            intent["preferences"] = list(dict.fromkeys(intent["preferences"] + ["预算友好"]))
        if "近" in direction or "少走" in direction or "少打车" in direction or "减少打车" in direction:
            intent["constraints"]["max_leg_minutes"] = 14
            intent["constraints"]["max_distance_km"] = 1.5
        if "室内" in direction or "下雨" in direction:
            intent["constraints"]["require_indoor"] = True
            intent["preferences"] = list(dict.fromkeys(intent["preferences"] + ["室内"]))
        intent["preferences"] = list(dict.fromkeys(intent["preferences"] + [direction]))

    def _apply_node_directive(self, intent: dict, directive: dict) -> None:
        objective = directive.get("objective")
        target_type = directive.get("target_type")
        if target_type == "restaurant":
            intent["change_flags"] = list(dict.fromkeys(intent.get("change_flags", []) + ["换餐厅"]))
        if target_type == "activity":
            intent["change_flags"] = list(dict.fromkeys(intent.get("change_flags", []) + ["换活动"]))
        if target_type == "route":
            intent["constraints"]["max_leg_minutes"] = min(intent["constraints"]["max_leg_minutes"], 12)
            intent["constraints"]["max_distance_km"] = min(intent["constraints"]["max_distance_km"], 1.2)
            intent["preferences"] = list(dict.fromkeys(intent["preferences"] + ["不走远", "距离近"]))
        if objective == "cheaper":
            intent["preferences"] = list(dict.fromkeys(intent["preferences"] + ["预算友好"]))
        elif objective == "japanese":
            intent["preferences"] = list(dict.fromkeys(intent["preferences"] + ["日料"]))
        elif objective == "art":
            intent["preferences"] = list(dict.fromkeys(intent["preferences"] + ["画展", "博览会", "艺术"]))
        elif objective == "indoor":
            intent["constraints"]["require_indoor"] = True
            intent["preferences"] = list(dict.fromkeys(intent["preferences"] + ["室内"]))
        elif objective == "kid_friendly":
            intent["preferences"] = list(dict.fromkeys(intent["preferences"] + ["亲子友好"]))
        elif objective == "quiet":
            intent["preferences"] = list(dict.fromkeys(intent["preferences"] + ["安静", "不排队"]))

    def _merge_activity_candidates(self, local_activities: list[dict], live_events: list[dict], intent: dict) -> list[dict]:
        prefer_events = any(tag in intent.get("preferences", []) for tag in ["画展", "博览会", "艺术", "市集"])
        merged = live_events + local_activities if prefer_events else local_activities + live_events
        seen: set[str] = set()
        result = []
        for item in merged:
            if item["id"] not in seen:
                seen.add(item["id"])
                result.append(item)
        return sorted(result, key=lambda item: item["score"], reverse=True)

    def _approved_preserve_ids(self, intent: dict, plan: dict | None) -> tuple[str | None, str | None]:
        if not plan:
            return None, None
        approved = set(intent.get("approved_item_ids", []))
        activity_id = plan.get("activity", {}).get("id")
        restaurant_id = plan.get("restaurant", {}).get("id")
        return (
            activity_id if activity_id in approved else None,
            restaurant_id if restaurant_id in approved else None,
        )

    def _rank(self, plans: list[dict], intent: dict, old_state: dict | None) -> list[dict]:
        if not plans:
            return []

        if self._wants_cheaper(intent):
            previous_cost = self._previous_total_cost(old_state)
            cheaper = [plan for plan in plans if previous_cost is not None and plan["total_cost"] < previous_cost]
            valid_cheaper = [plan for plan in cheaper if plan["valid"]]
            valid_plans = [plan for plan in plans if plan["valid"]]
            pool = valid_cheaper or cheaper or valid_plans or plans
            return sorted(pool, key=lambda plan: (1 if plan["valid"] else 0, -plan["total_cost"], plan["score"]), reverse=True)

        if self._wants_closer(intent):
            return sorted(
                plans,
                key=lambda plan: (1 if plan["valid"] else 0, -plan["max_leg_minutes"], -plan["transport_cost"], plan["score"]),
                reverse=True,
            )

        return sorted(plans, key=lambda plan: (1 if plan["valid"] else 0, plan["score"], -plan["total_cost"]), reverse=True)

    def _score(
        self,
        plan: dict,
        activity: dict,
        restaurant: dict,
        approved_items: set[str],
        intent: dict,
        old_state: dict | None,
    ) -> int:
        score = activity["score"] + restaurant["score"]
        if plan["valid"]:
            score += 100
        if activity["id"] in approved_items:
            score += 100
        if restaurant["id"] in approved_items:
            score += 100
        score -= len(plan["issues"]) * 35
        score -= max(0, plan["max_leg_minutes"] - 18) * 2
        score -= max(0, plan["total_cost"] - intent.get("budget", 800)) // 10
        if self._wants_cheaper(intent):
            previous_cost = self._previous_total_cost(old_state)
            score -= plan["total_cost"] // 8
            if previous_cost is not None and plan["total_cost"] < previous_cost:
                score += 90
        if self._wants_closer(intent):
            score -= plan["max_leg_minutes"] * 3
        return score

    def _wants_cheaper(self, intent: dict) -> bool:
        direction = intent.get("adjustment_direction") or ""
        return any(word in direction for word in ["便宜", "预算", "省钱", "低价", "少花"])

    def _wants_closer(self, intent: dict) -> bool:
        direction = intent.get("adjustment_direction") or ""
        return any(word in direction for word in ["近", "少走", "少打车", "减少打车"])

    def _previous_total_cost(self, old_state: dict | None) -> int | None:
        if not old_state:
            return None
        previous_plan = old_state.get("recommended_plan") or {}
        previous_cost = previous_plan.get("total_cost")
        return previous_cost if isinstance(previous_cost, int) else None

    def _cheap_item_bonus(self, item: dict) -> int:
        tags = set(item.get("tags", []))
        bonus = 0
        if "预算友好" in tags or "免费" in tags:
            bonus += 36
        if "avg_price" in item:
            bonus += max(0, 180 - int(item["avg_price"])) // 3
        else:
            item_cost = int(item.get("adult_price", 0)) + int(item.get("child_price", 0))
            bonus += max(0, 180 - item_cost) // 3
        return bonus

    def _title(self, activity: dict, weather: dict, intent: dict) -> str:
        if intent.get("retrieval_mode") == "llm_reasoning":
            return "推理重组方案"
        if activity.get("kind") == "event":
            return "展览灵感探索方案"
        if weather["condition"] == "rain":
            return "雨天室内亲子方案"
        if activity["distance_km"] <= 0.8:
            return "商圈内轻松方案"
        return "亲子轻松社交方案"

    def _reason(self, intent: dict, activity: dict, restaurant: dict, weather: dict) -> str:
        parts = [
            f"{activity['name']}适合{intent['people'].get('child_age') or 5}岁孩子参与",
            f"{restaurant['name']}支持{intent['people']['adults'] + intent['people']['children']}人用餐",
            "价格、时长和路线会随节点替换自动重算",
        ]
        if intent.get("retrieval_mode") == "llm_reasoning":
            parts.append("本轮由大模型推理路径重排候选")
        if activity.get("kind") == "event":
            parts.append("活动来自预留搜索接口，可替换为真实检索源")
        if weather["condition"] == "rain":
            parts.append("雨天优先选择室内节点")
        return "；".join(parts)

    def _suggested_terms(self, intent: dict) -> list[str]:
        base = ["不太远", "预算500以内", "下雨改室内", "换成日料", "想看画展", "加一个博览会", "更适合孩子"]
        if intent["people"]["children"]:
            base.insert(0, "亲子友好")
        return list(dict.fromkeys(base))[:8]

    def _summary(self, plan: dict) -> str:
        return (
            f"推荐「{plan['title']}」，总时长 {plan['total_duration']}，"
            f"预计 {plan['total_cost']} 元，最长单段通勤 {plan['max_leg_minutes']} 分钟。"
        )

    def _with_selected_plan(self, response: dict, plan_id: str, change_log: list[str]) -> dict:
        next_response = deepcopy(response)
        selected = self._find_plan(next_response["plans"], plan_id)
        selected["feedback_status"] = "approved"
        next_response["plans"] = [selected]
        next_response["recommended_plan"] = selected
        next_response["change_log"] = change_log
        next_response["summary"] = f"已确认「{selected['title']}」，可以继续预约或微调单个项目。"
        return next_response

    def _mark_item_feedback(
        self,
        response: dict,
        plan_id: str,
        item_id: str | None,
        status: str,
        change_log: list[str],
    ) -> dict:
        next_response = deepcopy(response)
        item_name = item_id or "该项目"
        for plan in next_response["plans"]:
            if plan["id"] != plan_id:
                continue
            for item in plan["timeline"]:
                if item["id"] == item_id:
                    item["feedback_status"] = status
                    item_name = item["name"]
        recommended = next_response.get("recommended_plan")
        if recommended and recommended.get("id") == plan_id:
            for item in recommended["timeline"]:
                if item["id"] == item_id:
                    item["feedback_status"] = status
                    item_name = item["name"]
        next_response["change_log"] = change_log
        if recommended:
            status_text = "赞同" if status == "approved" else "拒绝"
            next_response["summary"] = f"已将「{item_name}」标记为{status_text}，该状态可继续修改。"
        return next_response

    def _session_poi_detail(self, poi_id: str) -> dict | None:
        for state in self.sessions.values():
            plans = list(state.get("plans") or [])
            recommended = state.get("recommended_plan")
            if recommended:
                plans.append(recommended)
            for plan in plans:
                for key in ["activity", "restaurant"]:
                    poi = plan.get(key)
                    if poi and poi.get("id") == poi_id:
                        return format_poi_detail(poi)
        return None

    def _save_state(self, session_id: str, intent: dict, response: dict, history: list[dict]) -> None:
        self.sessions[session_id] = {
            "intent": intent,
            "plans": response["plans"],
            "recommended_plan": response["recommended_plan"],
            "history": history,
            "last_response": response,
        }

    def _state(self, session_id: str) -> dict:
        if session_id not in self.sessions:
            raise KeyError("session not found")
        return self.sessions[session_id]

    @staticmethod
    def _find_plan(plans: list[dict], plan_id: str) -> dict:
        plan = next((item for item in plans if item["id"] == plan_id), None)
        if not plan:
            raise KeyError("plan not found")
        return plan

    @staticmethod
    def _plan_key(plan: dict) -> str:
        return plan.get("plan_key") or f"{plan['activity']['id']}::{plan['restaurant']['id']}"

    @staticmethod
    def _without_id(values: list[str], item_id: str) -> list[str]:
        return [value for value in values if value != item_id]

    @staticmethod
    def _minutes_label(minutes: int) -> str:
        hours, remain = divmod(minutes, 60)
        if hours and remain:
            return f"{hours}小时{remain}分钟"
        if hours:
            return f"{hours}小时"
        return f"{remain}分钟"
