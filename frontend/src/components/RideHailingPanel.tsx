import { Car, ChevronRight, Clock3, MapPin, ShieldCheck, X } from "lucide-react";

import type { RideOptions } from "../lib/types";

type RideHailingPanelProps = {
  detail: RideOptions | null;
  loading: boolean;
  onClose: () => void;
};

export function RideHailingPanel({ detail, loading, onClose }: RideHailingPanelProps) {
  if (!detail && !loading) {
    return null;
  }

  if (loading || !detail) {
    return (
      <section className="panel ride-panel">
        <p className="eyebrow">Didi Mock</p>
        <h2>正在加载车型</h2>
      </section>
    );
  }

  return (
    <section className="panel ride-panel">
      <div className="ride-heading">
        <div>
          <p className="eyebrow">Didi Mock</p>
          <h2>选择车型与价格</h2>
        </div>
        <button className="plain-icon-button" type="button" onClick={onClose} title="关闭打车面板">
          <X size={18} aria-hidden="true" />
        </button>
      </div>

      <div className="ride-route">
        <div>
          <MapPin size={16} aria-hidden="true" />
          <span>{detail.origin}</span>
        </div>
        <ChevronRight size={16} aria-hidden="true" />
        <div>
          <MapPin size={16} aria-hidden="true" />
          <span>{detail.destination}</span>
        </div>
      </div>

      <div className="ride-summary">
        <div>
          <Clock3 size={17} aria-hidden="true" />
          <strong>{detail.estimated_minutes} 分钟</strong>
          <span>预计行程</span>
        </div>
        <div>
          <Car size={17} aria-hidden="true" />
          <strong>{detail.recommended_option.price} 元起</strong>
          <span>{detail.recommended_option.name}</span>
        </div>
      </div>

      <div className="ride-options">
        {detail.options.map((option) => (
          <button className={`ride-option ${option.selected ? "selected" : ""}`} type="button" key={option.id}>
            <div>
              <strong>{option.name}</strong>
              <span>{option.tag} · {option.eta_minutes ? `${option.eta_minutes} 分钟接驾` : "无需等待"}</span>
            </div>
            <b>{option.price === 0 ? "0元" : `${option.price}元`}</b>
          </button>
        ))}
      </div>

      <button
        className="booking-button"
        type="button"
        onClick={() => window.open(detail.mock_didi_url, "_blank", "noopener,noreferrer")}
      >
        <Car size={18} aria-hidden="true" />
        打开滴滴 Mock
      </button>

      <div className="api-placeholder soft">
        <ShieldCheck size={16} aria-hidden="true" />
        <span>接口：{detail.future_api}；未来字段：{detail.future_real_url_field}</span>
      </div>
      <p className="ride-notice">{detail.notice}</p>
    </section>
  );
}
