// Matches backend AdminCampaignDetailResponse — includes snapshot/offer fields
export interface AdminCampaign {
  id: string;
  product_id: string;
  title: string;
  description: string | null;
  category_id: string | null;
  images: string[];
  status: string;
  view_count: number;
  created_at: string;
  activated_at: string | null;
  moq: number | null;
  selling_price_try: number | null;
  lead_time_days: number | null;
  current_participant_count: number | null;
  moq_fill_percentage: number | null;
  // Snapshot fields (from AdminCampaignDetailResponse)
  selected_offer_id: string | null;
  supplier_name_snapshot: string | null;
  supplier_country_snapshot: string | null;
  alibaba_product_url_snapshot: string | null;
  unit_price_usd_snapshot: number | null;
  shipping_cost_usd_snapshot: number | null;
  customs_rate_snapshot: number | null;
  margin_rate_snapshot: number | null;
  fx_rate_snapshot: number | null;
  moq_reached_at: string | null;
  payment_deadline: string | null;
  ordered_at: string | null;
  delivered_at: string | null;
}

export interface CampaignCreatePayload {
  title: string;
  description?: string;
  category_id?: string;
  images: string[];
  supplier_name?: string;
  supplier_country: string;
  alibaba_product_url?: string;
  unit_price_usd: number;
  moq: number;
  lead_time_days?: number;
  shipping_cost_usd?: number;
  customs_rate?: number;
  margin_rate: number;
  from_suggestion_id?: string;
}

export interface CampaignUpdatePayload {
  title?: string;
  description?: string;
  category_id?: string | null;
  images?: string[];
  status?: string;
  // Supplier / offer fields
  unit_price_usd?: number;
  moq?: number;
  shipping_cost_usd?: number;
  customs_rate?: number;
  margin_rate?: number;
  supplier_name?: string;
  supplier_country?: string;
  alibaba_product_url?: string;
  lead_time_days?: number;
}

// Matches backend CategoryResponse
export interface AdminCategory {
  id: string;
  name: string;
  slug: string;
  parent_id: string | null;
  gumruk_rate: number | null;
  is_restricted: boolean;
  icon: string | null;
  sort_order: number;
}

export interface CategoryCreatePayload {
  name: string;
  slug: string;
  parent_id?: string;
  gumruk_rate?: number;
  is_restricted?: boolean;
  icon?: string;
  sort_order?: number;
}

export interface CategoryUpdatePayload {
  name?: string;
  slug?: string;
  parent_id?: string | null;
  gumruk_rate?: number | null;
  is_restricted?: boolean;
  icon?: string | null;
  sort_order?: number;
}

// Matches backend SuggestionResponse
export interface AdminSuggestion {
  id: string;
  title: string;
  description: string | null;
  category_id: string | null;
  reference_url: string | null;
  expected_price_try: number | null;
  status: string;
  created_by: string | null;
  admin_notes: string | null;
  created_at: string;
  reviewed_at: string | null;
}

export interface SuggestionUpdatePayload {
  status?: string;
  admin_notes?: string;
}

// PriceBreakdown fields are Decimal → come as numeric strings in JSON
export interface PriceBreakdown {
  unit_price_usd: string;
  unit_price_try: string;
  shipping_per_unit_try: string;
  customs_try: string;
  kdv_base_try: string;
  kdv_try: string;
  total_cost_try: string;
  margin_try: string;
  selling_price_try: string;
  usd_rate: string;
}

export interface PricePreviewPayload {
  unit_price_usd: number;
  moq: number;
  shipping_cost_usd?: number;
  customs_rate?: number;
  margin_rate?: number;
}

// ── Dashboard KPI value ───────────────────────────────────────────────────────

export interface KpiValue {
  value: number;
  delta_7d?: number | null;
  delta_30d?: number | null;
  hint?: string;
  href?: string;
  critical?: number;
  high?: number;
}

// ── Attention item ────────────────────────────────────────────────────────────

export type AttentionSeverity = "info" | "warning" | "critical";

export interface AttentionItem {
  severity: AttentionSeverity;
  title: string;
  description: string;
  href: string;
  primaryActionLabel: string;
  primaryActionHref: string;
}

// ── Lifecycle step ────────────────────────────────────────────────────────────

export interface LifecycleStep {
  status: string;
  label: string;
  count: number;
  href: string;
}

// ── Finance block ─────────────────────────────────────────────────────────────

export interface FinanceBlock {
  collected_amount: number;
  pending_amount: number;
  payment_conversion_rate: number | null;
  average_paid_order_value: number | null;
  invited_participant_count: number;
  paid_participant_count: number;
}

// ── Demand block ──────────────────────────────────────────────────────────────

export interface DemandBlock {
  total_quantity: number;
  unique_users: number;
  average_per_user: number;
  last_30_days_quantity: number;
  last_7_days_quantity: number;
}

// ── Near MOQ item ─────────────────────────────────────────────────────────────

export interface NearMoqActiveItem {
  campaign_id: string;
  title: string;
  fill_pct: number;
  current_qty: number;
  moq: number;
}

export interface DashboardSummary {
  // Legacy flat fields (backward compat)
  campaigns_total: number;
  campaigns_draft: number;
  campaigns_active: number;
  campaigns_moq_reached: number;
  campaigns_payment_collecting: number;
  campaigns_ordered: number;
  campaigns_shipped: number;
  campaigns_delivered: number;
  products_total: number;
  demand_total: number;
  demand_unique_users: number;
  demand_last_30d: number;
  suggestions_pending: number;
  revenue_total_try: number;
  pending_collection_try: number;
  // New structured fields
  kpis?: {
    total_products: KpiValue;
    active_campaigns: KpiValue;
    moq_reached: KpiValue;
    payment_collecting: KpiValue;
    pending_suggestions: KpiValue;
    fraud_watch: KpiValue;
  };
  attention?: AttentionItem[];
  lifecycle?: LifecycleStep[];
  finance?: FinanceBlock;
  demand?: DemandBlock;
  near_moq_active?: NearMoqActiveItem[];
}

export interface DemandEntry {
  id: string;
  campaign_id: string;
  user_id: string;
  user_email: string;
  user_full_name: string | null;
  quantity: number;
  status: string;
  admin_note: string | null;
  removal_reason: string | null;
  removed_at: string | null;
  created_at: string;
}

export interface DemandEntriesResponse {
  campaign_id: string;
  total_active_quantity: number;
  unique_active_users: number;
  entries: DemandEntry[];
}

// ── Demand Users (user-level aggregate) ──────────────────────────────────────

export interface DemandUser {
  user_id: string;
  email: string;
  full_name: string | null;
  total_entries: number;
  total_quantity: number;
  unique_campaigns: number;
  max_single_entry_qty: number;
  last_activity: string | null;
  flagged_count: number;
  removed_count: number;
}

export interface DemandUsersResponse {
  users: DemandUser[];
  total: number;
}

// ── Fraud Watch ───────────────────────────────────────────────────────────────

export type FraudRiskLevel = "watch" | "high" | "critical";

export interface FraudWatchEntry {
  user_id: string;
  email: string;
  full_name: string | null;
  campaign_id: string;
  campaign_title: string;
  campaign_moq: number;
  campaign_status: string;
  user_total_quantity: number;
  percent_of_moq: number;
  entry_count: number;
  flagged_count: number;
  removed_count: number;
  last_activity: string | null;
  risk_level: FraudRiskLevel;
  risk_reasons: string[];
}

export interface FraudWatchResponse {
  entries: FraudWatchEntry[];
  total: number;
  threshold_pct: number;
}

// ── Action Items ──────────────────────────────────────────────────────────────

export interface MoqStalledItem {
  campaign_id: string;
  title: string;
  moq: number;
  moq_reached_at: string | null;
}

export interface PaymentCollectingItem {
  campaign_id: string;
  title: string;
  moq: number;
  payment_deadline: string | null;
}

export interface NearMoqItem {
  campaign_id: string;
  title: string;
  fill_pct: number;
  current_qty: number;
  moq: number;
}

export interface TrendingItem {
  campaign_id: string;
  title: string;
  entry_count: number;
  qty_sum: number;
}

export interface TopDemandItem {
  campaign_id: string;
  title: string;
  qty_sum: number;
}

export interface ModeratedEntry {
  entry_id: string;
  campaign_id: string;
  campaign_title: string;
  user_email: string;
  quantity: number;
  status: string;
  admin_note: string | null;
  removal_reason: string | null;
  removed_at: string | null;
  created_at: string;
}

// ── Demand User Detail (per-user drilldown) ───────────────────────────────────

export interface DemandUserDetailEntry {
  id: string;
  quantity: number;
  status: string;
  admin_note: string | null;
  removal_reason: string | null;
  removed_at: string | null;
  created_at: string;
}

export interface DemandUserDetailCampaign {
  campaign_id: string;
  campaign_title: string;
  campaign_status: string;
  campaign_moq: number | null;
  total_active_quantity: number;
  entry_count: number;
  flagged_count: number;
  removed_count: number;
  last_activity: string;
  entries: DemandUserDetailEntry[];
}

export interface DemandUserDetail {
  user_id: string;
  email: string;
  full_name: string | null;
  created_at: string | null;
  campaigns: DemandUserDetailCampaign[];
  totals: {
    total_entries: number;
    total_active_quantity: number;
    unique_campaigns: number;
    flagged_count: number;
    removed_count: number;
  };
}

export interface ActionItemsResponse {
  moq_stalled: MoqStalledItem[];
  payment_collecting: PaymentCollectingItem[];
  near_moq_active: NearMoqItem[];
  trending_24h: TrendingItem[];
  top_demand_30d: TopDemandItem[];
  recent_moderated: ModeratedEntry[];
}
