import { useMemo, useState } from "react";
import { CalendarDays, CloudRain, Compass, Loader2, ReceiptText } from "lucide-react";

import { ChatPanel } from "./components/ChatPanel";
import { PlanCard } from "./components/PlanCard";
import { PoiDetailPanel } from "./components/PoiDetailPanel";
import { RideHailingPanel } from "./components/RideHailingPanel";
import { bookPlan, createPlan, getPoiDetail, getRideOptions, planAction, replan, updatePreferences } from "./lib/api";
import type { AgentData, BookingResult, PoiDetail, RideOptions, TimelineItem, UserPreferences } from "./lib/types";

type Message = {
  role: "user" | "assistant";
  content: string;
};

const initialPrompt =
  "今天下午想带老婆、5岁孩子和两个朋友出去玩4-6小时，不想太远，预算800以内，想要一个餐厅和一个活动。";

const defaultPreferences: UserPreferences = {
  liked_tags: ["亲子友好", "轻松"],
  disliked_tags: [],
  food_preferences: [],
  activity_preferences: [],
  avoid_crowded: true,
  require_indoor: false,
  budget: 800,
  max_leg_minutes: 22,
};

export default function App() {
  const [messages, setMessages] = useState<Message[]>([
    {
      role: "assistant",
      content: "把周末目标发给我。我会先看关键词命中率，高命中走数据库，低命中或连续否定后走推理路径。",
    },
  ]);
  const [input, setInput] = useState(initialPrompt);
  const [location, setLocation] = useState("北京朝阳大悦城");
  const [preferences, setPreferences] = useState<UserPreferences>(defaultPreferences);
  const [data, setData] = useState<AgentData | null>(null);
  const [booking, setBooking] = useState<BookingResult | null>(null);
  const [poiDetail, setPoiDetail] = useState<PoiDetail | null>(null);
  const [rideDetail, setRideDetail] = useState<RideOptions | null>(null);
  const [poiLoading, setPoiLoading] = useState(false);
  const [rideLoading, setRideLoading] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const selectedPlan = useMemo(() => data?.recommended_plan ?? null, [data]);

  function applyData(nextData: AgentData) {
    setData(nextData);
    setMessages((prev) => [...prev, { role: "assistant", content: nextData.summary }]);
  }

  async function submit(value?: string) {
    const text = (value ?? input).trim();
    if (!text || loading) return;

    setError(null);
    setBooking(null);
    setLoading(true);
    setMessages((prev) => [...prev, { role: "user", content: text }]);

    try {
      const nextData = data?.session_id
        ? await replan(data.session_id, text, preferences)
        : await createPlan(text, location, preferences);
      applyData(nextData);
      setInput("");
    } catch (err) {
      const message = err instanceof Error ? err.message : "请求失败";
      setError(message);
      setMessages((prev) => [...prev, { role: "assistant", content: "后端暂时没有响应，请确认 API 服务已启动。" }]);
    } finally {
      setLoading(false);
    }
  }

  async function handleApplyPreferences() {
    if (!data?.session_id || loading) return;
    setLoading(true);
    setError(null);
    try {
      const nextData = await updatePreferences(data.session_id, preferences);
      applyData(nextData);
    } catch (err) {
      setError(err instanceof Error ? err.message : "偏好更新失败");
    } finally {
      setLoading(false);
    }
  }

  async function handlePlanAction(
    planId: string,
    action: "approve_plan" | "reject_plan",
    adjustmentDirection?: string,
  ) {
    if (!data?.session_id || loading) return;
    setLoading(true);
    setBooking(null);
    setError(null);
    try {
      const nextData = await planAction({
        sessionId: data.session_id,
        planId,
        action,
        adjustmentDirection,
        userPreferences: preferences,
      });
      applyData(nextData);
    } catch (err) {
      setError(err instanceof Error ? err.message : "方案反馈失败");
    } finally {
      setLoading(false);
    }
  }

  async function handleItemAction(
    planId: string,
    item: TimelineItem,
    action: "approve_item" | "reject_item",
    adjustmentDirection?: string,
  ) {
    if (!data?.session_id || loading) return;
    setLoading(true);
    setBooking(null);
    setError(null);
    try {
      const nextData = await planAction({
        sessionId: data.session_id,
        planId,
        action,
        itemId: item.id,
        itemType: item.poi_kind ?? item.type,
        adjustmentDirection,
        userPreferences: preferences,
      });
      applyData(nextData);
    } catch (err) {
      setError(err instanceof Error ? err.message : "项目反馈失败");
    } finally {
      setLoading(false);
    }
  }

  async function handleOpenPoi(poiId: string) {
    setPoiLoading(true);
    setError(null);
    try {
      const detail = await getPoiDetail(poiId);
      setPoiDetail(detail);
      setRideDetail(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "详情加载失败");
    } finally {
      setPoiLoading(false);
    }
  }

  async function handleOpenRide(item: TimelineItem) {
    if (!item.route) return;
    setRideLoading(true);
    setError(null);
    try {
      const detail = await getRideOptions({
        origin: item.route.from,
        destination: item.route.to,
        minutes: item.route.minutes,
        mode: item.route.mode,
      });
      setRideDetail(detail);
      setPoiDetail(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "打车选项加载失败");
    } finally {
      setRideLoading(false);
    }
  }

  async function handleBooking() {
    if (!data?.session_id || !selectedPlan || loading) return;
    setLoading(true);
    setError(null);
    try {
      const result = await bookPlan(data.session_id, selectedPlan.id);
      setBooking(result);
    } catch (err) {
      setError(err instanceof Error ? err.message : "预约失败");
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="app-shell fixed-shell">
      <ChatPanel
        messages={messages}
        input={input}
        location={location}
        loading={loading}
        hasSession={Boolean(data?.session_id)}
        suggestedTerms={data?.suggested_terms ?? []}
        preferences={preferences}
        onInputChange={setInput}
        onLocationChange={setLocation}
        onSubmit={submit}
        onPreferencesChange={setPreferences}
        onApplyPreferences={handleApplyPreferences}
      />

      <section className="workspace single-plan-workspace">
        <div className="status-strip">
          <div>
            <CalendarDays size={18} aria-hidden="true" />
            <span>{data ? `${data.intent.date} ${data.intent.start_time}` : "等待规划"}</span>
          </div>
          <div>
            <CloudRain size={18} aria-hidden="true" />
            <span>
              {data
                ? `${data.weather.temperature}℃ / 降雨 ${data.weather.rain_probability}%`
                : "天气待查询"}
            </span>
          </div>
          <div>
            <ReceiptText size={18} aria-hidden="true" />
            <span>{data ? `预算 ${data.intent.budget} 元` : "预算待解析"}</span>
          </div>
        </div>

        {data && (
          <div className="routing-strip">
            <Compass size={16} aria-hidden="true" />
            <span>{data.routing.retrieval_mode === "database" ? "数据库召回" : "大模型推理"}</span>
            <b>命中率 {Math.round(data.routing.keyword_confidence * 100)}%</b>
            <b>否定 {data.routing.plan_reject_count} 次</b>
          </div>
        )}

        {error && <div className="error-banner">{error}</div>}

        {loading && (
          <div className="loading-line">
            <Loader2 size={18} aria-hidden="true" />
            Agent 正在更新方案
          </div>
        )}

        <div className="plan-list fixed-plan-list">
          {selectedPlan ? (
            <PlanCard
              key={selectedPlan.id}
              plan={selectedPlan}
              selected
              busy={loading}
              onSelect={() => undefined}
              onBook={handleBooking}
              onPlanAction={handlePlanAction}
              onItemAction={handleItemAction}
              onOpenPoi={handleOpenPoi}
              onOpenRide={handleOpenRide}
            />
          ) : (
            <div className="empty-state">
              <h2>一次只生成一套方案。</h2>
              <p>你可以否定整套方案，或只否定其中一个项目；被赞同的项目会在后续更新中保留。</p>
            </div>
          )}
        </div>
      </section>

      <aside className="side-rail fixed-side">
        {rideDetail || rideLoading ? (
          <RideHailingPanel detail={rideDetail} loading={rideLoading} onClose={() => setRideDetail(null)} />
        ) : (
          <PoiDetailPanel detail={poiDetail} loading={poiLoading} onClose={() => setPoiDetail(null)} />
        )}

        {booking && (
          <section className="panel booking-panel" id="order">
            <p className="eyebrow">Mock Order</p>
            <h2>{booking.booking.title}</h2>
            <dl>
              <div>
                <dt>预约号</dt>
                <dd>{booking.booking.confirmation_id}</dd>
              </div>
              <div>
                <dt>订单号</dt>
                <dd>{booking.order.order_id}</dd>
              </div>
              <div>
                <dt>金额</dt>
                <dd>{booking.order.amount} 元</dd>
              </div>
            </dl>
            <p>{booking.booking.message}</p>
          </section>
        )}
      </aside>
    </main>
  );
}
