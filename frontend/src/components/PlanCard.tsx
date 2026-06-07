import { useState } from "react";
import { CalendarCheck, CheckCircle2, Clock3, Route, ThumbsDown, ThumbsUp, Wallet } from "lucide-react";

import type { Plan, TimelineItem } from "../lib/types";
import { PlanTimeline } from "./PlanTimeline";

type PlanCardProps = {
  plan: Plan;
  selected: boolean;
  busy: boolean;
  onSelect: () => void;
  onBook: () => void;
  onPlanAction: (planId: string, action: "approve_plan" | "reject_plan", adjustmentDirection?: string) => void;
  onOpenRide: (item: TimelineItem) => void;
  onItemAction: (
    planId: string,
    item: TimelineItem,
    action: "approve_item" | "reject_item",
    adjustmentDirection?: string,
  ) => void;
  onOpenPoi: (poiId: string) => void;
};

const planAdjustmentOptions = [
  "整体更近一点",
  "整体更便宜",
  "更适合孩子",
  "多一点展览",
  "尽量室内",
  "节奏更松弛",
  "餐厅换口味",
  "减少打车",
];

export function PlanCard({
  plan,
  selected,
  busy,
  onSelect,
  onBook,
  onPlanAction,
  onItemAction,
  onOpenPoi,
  onOpenRide,
}: PlanCardProps) {
  const [planDirection, setPlanDirection] = useState("");

  const rejectPlan = () => {
    onPlanAction(plan.id, "reject_plan", planDirection.trim() || undefined);
  };

  return (
    <article className={`plan-card ${selected ? "selected" : ""}`}>
      <div className="plan-topline">
        <div>
          <p className="eyebrow">{plan.valid ? "Recommended" : "Backup"}</p>
          <h2>{plan.title}</h2>
        </div>
        <button className="icon-text-button" type="button" onClick={onSelect}>
          <CheckCircle2 size={18} aria-hidden="true" />
          {selected ? "当前方案" : "设为主方案"}
        </button>
      </div>

      <p className="reason">{plan.reason}</p>

      <div className="metric-grid">
        <div>
          <Clock3 size={18} aria-hidden="true" />
          <span>{plan.total_duration}</span>
        </div>
        <div>
          <Wallet size={18} aria-hidden="true" />
          <span>{plan.total_cost} 元</span>
        </div>
        <div>
          <Route size={18} aria-hidden="true" />
          <span>最长 {plan.max_leg_minutes} 分钟</span>
        </div>
      </div>

      <PlanTimeline
        planId={plan.id}
        items={plan.timeline}
        busy={busy}
        onOpenPoi={onOpenPoi}
        onOpenRide={onOpenRide}
        onItemAction={onItemAction}
      />

      <div className="plan-actions">
        <datalist id="plan-adjustment-options">
          {planAdjustmentOptions.map((option) => (
            <option value={option} key={option} />
          ))}
        </datalist>
        <button
          className={`decision-button approve ${plan.feedback_status === "approved" ? "active" : ""}`}
          type="button"
          onClick={() => onPlanAction(plan.id, "approve_plan")}
          disabled={busy}
          title={plan.feedback_status === "approved" ? "已赞同；仍可改点拒绝" : "赞同整套方案"}
        >
          <ThumbsUp size={18} aria-hidden="true" />
          赞同
        </button>
        <input
          className="plan-adjust-input"
          list="plan-adjustment-options"
          value={planDirection}
          placeholder="整体调整方向"
          onChange={(event) => setPlanDirection(event.target.value)}
          onKeyDown={(event) => {
            if (event.key === "Enter" && planDirection.trim()) {
              event.preventDefault();
              rejectPlan();
            }
          }}
          disabled={busy}
        />
        <button
          className={`decision-button reject ${plan.feedback_status === "rejected" ? "active" : ""}`}
          type="button"
          onClick={rejectPlan}
          disabled={busy}
          title={plan.feedback_status === "approved" ? "改为拒绝并重规划" : "拒绝整套方案"}
        >
          <ThumbsDown size={18} aria-hidden="true" />
          拒绝
        </button>
      </div>

      <button className="booking-button" type="button" onClick={onBook} disabled={!selected || busy}>
        <CalendarCheck size={18} aria-hidden="true" />
        Mock 预约/下单
      </button>
    </article>
  );
}
