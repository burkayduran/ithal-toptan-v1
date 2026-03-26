/** Generic paginated response wrapper */
export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  per_page: number;
  total_pages: number;
}

/** Campaign status values (matches backend CampaignStatus) */
export type CampaignStatus =
  | "draft"
  | "active"
  | "moq_reached"
  | "payment_collecting"
  | "ordered"
  | "shipped"
  | "delivered"
  | "cancelled";

/** Matches backend CampaignResponse */
export interface Campaign {
  id: string;
  product_id: string;
  title: string;
  description: string | null;
  category_id: string | null;
  images: string[];
  status: CampaignStatus;
  view_count: number;
  created_at: string;
  activated_at: string | null;
  /** Snapshot selling price in TRY */
  selling_price_try: number | null;
  /** Minimum order quantity */
  moq: number | null;
  /** Estimated delivery lead time in days */
  lead_time_days: number | null;
  /** Total participant quantity currently committed */
  current_participant_count: number | null;
  /** Percentage of MOQ filled (0-100) */
  moq_fill_percentage: number | null;
}
