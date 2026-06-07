import { MapPin, Plus, Search, Send, SlidersHorizontal } from "lucide-react";

import type { UserPreferences } from "../lib/types";

type Message = {
  role: "user" | "assistant";
  content: string;
};

type ChatPanelProps = {
  messages: Message[];
  input: string;
  location: string;
  loading: boolean;
  hasSession: boolean;
  suggestedTerms: string[];
  preferences: UserPreferences;
  onInputChange: (value: string) => void;
  onLocationChange: (value: string) => void;
  onSubmit: (value?: string) => void;
  onPreferencesChange: (value: UserPreferences) => void;
  onApplyPreferences: () => void;
};

const starterPrompt =
  "今天下午想带老婆、5岁孩子和两个朋友出去玩4-6小时，不想太远，预算800以内，想要一个餐厅和一个活动。";

const fallbackTerms = ["亲子友好", "不太远", "画展", "博览会", "预算500以内", "下雨改室内", "换成日料"];
const preferenceTags = ["亲子友好", "画展", "博览会", "游戏", "日料", "预算友好", "安静", "拍照"];

function toggleValue(values: string[], value: string) {
  return values.includes(value) ? values.filter((item) => item !== value) : [...values, value];
}

export function ChatPanel({
  messages,
  input,
  location,
  loading,
  hasSession,
  suggestedTerms,
  preferences,
  onInputChange,
  onLocationChange,
  onSubmit,
  onPreferencesChange,
  onApplyPreferences,
}: ChatPanelProps) {
  const quickTerms = suggestedTerms.length ? suggestedTerms : fallbackTerms;

  return (
    <section className="panel chat-panel">
      <div className="panel-heading">
        <div>
          <p className="eyebrow">Planning Agent</p>
          <h1>本地生活规划台</h1>
        </div>
        <SlidersHorizontal size={20} aria-hidden="true" />
      </div>

      <label className="location-field">
        <MapPin size={18} aria-hidden="true" />
        <input
          value={location}
          onChange={(event) => onLocationChange(event.target.value)}
          aria-label="出发地点"
        />
      </label>

      <div className="term-box">
        <div className="term-title">
          <Search size={16} aria-hidden="true" />
          <span>推荐词汇</span>
        </div>
        <div className="quick-row compact">
          {quickTerms.map((term) => (
            <button
              className="ghost-button"
              type="button"
              key={term}
              onClick={() => onInputChange(input ? `${input}，${term}` : term)}
              disabled={loading}
            >
              <Plus size={14} aria-hidden="true" />
              {term}
            </button>
          ))}
          {!hasSession && (
            <button className="ghost-button strong" type="button" onClick={() => onSubmit(starterPrompt)} disabled={loading}>
              一键填入赛题场景
            </button>
          )}
        </div>
      </div>

      <div className="message-list" aria-live="polite">
        {messages.map((message, index) => (
          <div key={`${message.role}-${index}`} className={`message ${message.role}`}>
            {message.content}
          </div>
        ))}
      </div>

      <form
        className="composer"
        onSubmit={(event) => {
          event.preventDefault();
          onSubmit();
        }}
      >
        <textarea
          value={input}
          onChange={(event) => onInputChange(event.target.value)}
          placeholder={hasSession ? "继续追加约束，比如：拒绝这个餐厅、想看画展、预算500以内" : "输入一句自然语言目标"}
          rows={4}
        />
        <button className="primary-button" type="submit" disabled={loading || !input.trim()}>
          <Send size={18} aria-hidden="true" />
          {loading ? "规划中" : hasSession ? "重规划" : "生成方案"}
        </button>
      </form>

      <div className="preference-panel">
        <div className="section-title">
          <p className="eyebrow">Preference Memory</p>
          <h2>用户偏好记录</h2>
        </div>
        <div className="preference-grid">
          <label>
            预算上限
            <input
              type="number"
              min={200}
              step={50}
              value={preferences.budget ?? ""}
              placeholder="800"
              onChange={(event) =>
                onPreferencesChange({
                  ...preferences,
                  budget: event.target.value ? Number(event.target.value) : undefined,
                })
              }
            />
          </label>
          <label>
            单段通勤
            <input
              type="number"
              min={8}
              step={2}
              value={preferences.max_leg_minutes ?? ""}
              placeholder="22"
              onChange={(event) =>
                onPreferencesChange({
                  ...preferences,
                  max_leg_minutes: event.target.value ? Number(event.target.value) : undefined,
                })
              }
            />
          </label>
        </div>
        <div className="toggle-row">
          <button
            className={`toggle-chip ${preferences.require_indoor ? "active" : ""}`}
            type="button"
            onClick={() => onPreferencesChange({ ...preferences, require_indoor: !preferences.require_indoor })}
          >
            优先室内
          </button>
          <button
            className={`toggle-chip ${preferences.avoid_crowded ? "active" : ""}`}
            type="button"
            onClick={() => onPreferencesChange({ ...preferences, avoid_crowded: !preferences.avoid_crowded })}
          >
            少排队
          </button>
        </div>
        <div className="tag-picker">
          {preferenceTags.map((tag) => (
            <button
              className={`tag-button ${preferences.liked_tags.includes(tag) ? "active" : ""}`}
              type="button"
              key={tag}
              onClick={() =>
                onPreferencesChange({
                  ...preferences,
                  liked_tags: toggleValue(preferences.liked_tags, tag),
                })
              }
            >
              {tag}
            </button>
          ))}
        </div>
        <button className="secondary-button" type="button" onClick={onApplyPreferences} disabled={loading || !hasSession}>
          应用偏好并重排
        </button>
      </div>
    </section>
  );
}
