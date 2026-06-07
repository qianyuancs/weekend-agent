export type TraceStep = {
  step: string;
  tool: string;
  status: "done" | "warn" | "error";
  detail: string;
  data?: Record<string, unknown>;
};

export type TimelineItem = {
  id: string;
  time: string;
  type: "transport" | "activity" | "event" | "break" | "restaurant";
  name: string;
  duration_minutes: number;
  duration_label: string;
  note: string;
  cost: number;
  poi_id?: string | null;
  poi_kind?: "restaurant" | "activity" | "event" | null;
  detail_url?: string | null;
  actionable: boolean;
  feedback_status: "pending" | "approved" | "rejected";
  route?: {
    from: string;
    to: string;
    minutes: number;
    mode: string;
  } | null;
};

export type Check = {
  label: string;
  status: "pass" | "warn" | "fail";
  detail: string;
};

export type Plan = {
  id: string;
  plan_key: string;
  title: string;
  reason: string;
  timeline: TimelineItem[];
  total_cost: number;
  total_duration: string;
  total_minutes: number;
  max_leg_minutes: number;
  transport_cost: number;
  next_actions: string[];
  valid: boolean;
  checks: Check[];
  issues: string[];
  warnings: string[];
  feedback_status: "pending" | "approved" | "rejected";
};

export type UserPreferences = {
  liked_tags: string[];
  disliked_tags: string[];
  food_preferences: string[];
  activity_preferences: string[];
  avoid_crowded: boolean;
  require_indoor: boolean;
  budget?: number;
  max_leg_minutes?: number;
};

export type AgentData = {
  session_id: string;
  intent: {
    location: string;
    date: string;
    start_time: string;
    budget: number;
    preferences: string[];
    keyword_matches?: Record<string, string[]>;
    parse_strategy?: string;
    user_preferences?: UserPreferences;
    people: {
      adults: number;
      children: number;
      child_age?: number | null;
    };
  };
  weather: {
    condition: string;
    temperature: number;
    rain_probability: number;
    suggestion: string;
  };
  plans: Plan[];
  recommended_plan: Plan | null;
  trace: TraceStep[];
  change_log: string[];
  summary: string;
  suggested_terms: string[];
  routing: {
    retrieval_mode: "database" | "llm_reasoning";
    keyword_confidence: number;
    plan_reject_count: number;
    llm_reasoning_count: number;
  };
};

export type PoiDetail = {
  id: string;
  kind: "restaurant" | "activity" | "event";
  kind_name: string;
  name: string;
  category: string;
  area: string;
  distance_km: number;
  price: number;
  rating: number;
  open_time: string;
  available: boolean;
  capacity_left: number;
  wait_minutes: number;
  tags: string[];
  booking_required: boolean;
  child_friendly: boolean;
  mock_meituan_url: string;
  future_real_url_field: string;
  hero: {
    title: string;
    subtitle: string;
    tone: "mint" | "sunset" | "sky";
  };
  coupons: Array<{ title: string; price: number; note: string }>;
  reviews: Array<{ user: string; text: string }>;
};

export type RideOption = {
  id: string;
  name: string;
  eta_minutes: number;
  price: number;
  tag: string;
  selected: boolean;
};

export type RideOptions = {
  origin: string;
  destination: string;
  mode: string;
  estimated_minutes: number;
  recommended_option: RideOption;
  options: RideOption[];
  mock_didi_url: string;
  future_real_url_field: string;
  future_api: string;
  notice: string;
};

export type BookingResult = {
  booking: {
    confirmation_id: string;
    status: string;
    title: string;
    reserved_items: string[];
    message: string;
  };
  order: {
    order_id: string;
    amount: number;
    status: string;
    actions: string[];
  };
};
