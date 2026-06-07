import { BadgeCheck, CalendarCheck, ChevronRight, MapPin, Star, Ticket, X } from "lucide-react";

import type { PoiDetail } from "../lib/types";

type PoiDetailPanelProps = {
  detail: PoiDetail | null;
  loading: boolean;
  onClose: () => void;
};

export function PoiDetailPanel({ detail, loading, onClose }: PoiDetailPanelProps) {
  if (!detail && !loading) {
    return (
      <section className="panel poi-panel empty" id="poi-detail">
        <p className="eyebrow">Meituan Mock</p>
        <h2>点击行程节点查看详情</h2>
        <p className="muted-copy">餐厅、场馆、画展和博览会都会在这里打开类美团详情页；后续可把接口替换为真实 deeplink。</p>
      </section>
    );
  }

  if (loading || !detail) {
    return (
      <section className="panel poi-panel" id="poi-detail">
        <p className="eyebrow">Meituan Mock</p>
        <h2>正在加载详情</h2>
      </section>
    );
  }

  return (
    <section className="panel poi-panel" id="poi-detail">
      <div className={`poi-hero ${detail.hero.tone}`}>
        <button className="close-button" type="button" onClick={onClose} title="关闭详情">
          <X size={18} aria-hidden="true" />
        </button>
        <p>{detail.kind_name}</p>
        <h2>{detail.hero.title}</h2>
        <span>{detail.hero.subtitle}</span>
      </div>

      <div className="poi-meta">
        <div>
          <Star size={16} aria-hidden="true" />
          <strong>{detail.rating}</strong>
          <span>评分</span>
        </div>
        <div>
          <MapPin size={16} aria-hidden="true" />
          <strong>{detail.distance_km}km</strong>
          <span>{detail.area}</span>
        </div>
        <div>
          <Ticket size={16} aria-hidden="true" />
          <strong>{detail.price}元起</strong>
          <span>{detail.category}</span>
        </div>
      </div>

      <div className="poi-tags">
        {detail.tags.slice(0, 8).map((tag) => (
          <span key={tag}>{tag}</span>
        ))}
      </div>

      <div className="poi-section">
        <h3>团购/预约</h3>
        {detail.coupons.map((coupon) => (
          <button className="coupon-row" type="button" key={coupon.title}>
            <div>
              <strong>{coupon.title}</strong>
              <span>{coupon.note}</span>
            </div>
            <b>{coupon.price === 0 ? "预约" : `${coupon.price}元`}</b>
            <ChevronRight size={16} aria-hidden="true" />
          </button>
        ))}
      </div>

      <div className="poi-section">
        <h3>接口占位</h3>
        <div className="api-placeholder">
          <BadgeCheck size={16} aria-hidden="true" />
          <span>{detail.mock_meituan_url}</span>
        </div>
        <div className="api-placeholder soft">
          <CalendarCheck size={16} aria-hidden="true" />
          <span>未来字段：{detail.future_real_url_field}</span>
        </div>
      </div>

      <div className="poi-section">
        <h3>用户评价</h3>
        {detail.reviews.map((review) => (
          <div className="review-row" key={review.user}>
            <strong>{review.user}</strong>
            <p>{review.text}</p>
          </div>
        ))}
      </div>
    </section>
  );
}
