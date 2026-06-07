import { useState } from "react";
import { Car, Check, Coffee, Store, ThumbsDown, Ticket, Utensils, X } from "lucide-react";

import type { TimelineItem } from "../lib/types";

const iconMap = {
  transport: Car,
  activity: Ticket,
  event: Store,
  break: Coffee,
  restaurant: Utensils,
};

const adjustmentOptions = [
  "更近一点",
  "更便宜",
  "更适合孩子",
  "更室内",
  "更安静",
  "更有艺术感",
  "更适合社交",
  "换成日料",
];

type PlanTimelineProps = {
  planId: string;
  items: TimelineItem[];
  busy: boolean;
  onOpenPoi: (poiId: string) => void;
  onOpenRide: (item: TimelineItem) => void;
  onItemAction: (
    planId: string,
    item: TimelineItem,
    action: "approve_item" | "reject_item",
    adjustmentDirection?: string,
  ) => void;
};

export function PlanTimeline({ planId, items, busy, onOpenPoi, onOpenRide, onItemAction }: PlanTimelineProps) {
  const [directions, setDirections] = useState<Record<string, string>>({});

  return (
    <div className="timeline-list">
      <datalist id="adjustment-options">
        {adjustmentOptions.map((option) => (
          <option value={option} key={option} />
        ))}
      </datalist>

      {items.map((item) => {
        const Icon = iconMap[item.type];
        const canOpen = Boolean(item.poi_id) || item.type === "transport";
        const direction = directions[item.id] ?? "";
        return (
          <div className="timeline-row" key={item.id}>
            <div className="timeline-stamp">
              <span>{item.time}</span>
              <div className="timeline-icon">
                <Icon size={16} aria-hidden="true" />
              </div>
            </div>

            <div className="timeline-card">
              <button
                className="timeline-main"
                type="button"
                onClick={() => {
                  if (item.type === "transport") {
                    onOpenRide(item);
                    return;
                  }
                  if (item.poi_id) {
                    onOpenPoi(item.poi_id);
                  }
                }}
                disabled={!canOpen}
              >
                <div className="timeline-title">
                  <span>{item.name}</span>
                  <strong>{item.duration_label}</strong>
                </div>
                <p>{item.note}</p>
                <div className="timeline-cost">预计 {item.cost} 元</div>
              </button>

              <div className="item-actions">
                <button
                  className={`mini-action approve ${item.feedback_status === "approved" ? "active" : ""}`}
                  type="button"
                  onClick={() => onItemAction(planId, item, "approve_item")}
                  disabled={busy}
                  title={item.feedback_status === "approved" ? "已赞同；仍可改点拒绝" : "赞同此项目"}
                >
                  <Check size={14} aria-hidden="true" />
                  赞同
                </button>
                <input
                  className="adjust-input"
                  list="adjustment-options"
                  value={direction}
                  placeholder="调整方向"
                  onChange={(event) => setDirections({ ...directions, [item.id]: event.target.value })}
                  onKeyDown={(event) => {
                    if (event.key === "Enter" && direction.trim()) {
                      event.preventDefault();
                      onItemAction(planId, item, "reject_item", direction.trim());
                    }
                  }}
                  disabled={busy}
                />
                <button
                  className={`mini-action reject ${item.feedback_status === "rejected" ? "active" : ""}`}
                  type="button"
                  onClick={() => onItemAction(planId, item, "reject_item", direction || undefined)}
                  disabled={busy}
                  title={item.feedback_status === "approved" ? "改为拒绝并替换" : "拒绝此项目并替换"}
                >
                  {item.feedback_status === "rejected" ? (
                    <X size={14} aria-hidden="true" />
                  ) : (
                    <ThumbsDown size={14} aria-hidden="true" />
                  )}
                  拒绝
                </button>
              </div>
            </div>
          </div>
        );
      })}
    </div>
  );
}
