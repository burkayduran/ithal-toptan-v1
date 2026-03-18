/** Generic paginated response wrapper */
export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  per_page: number;
  total_pages: number;
}

/** Matches backend ProductRequest status values */
export type ProductStatus =
  | "pending"
  | "sourcing"
  | "active"
  | "moq_reached"
  | "payment_collecting"
  | "ordered"
  | "delivered"
  | "cancelled";

/** Matches backend ProductResponse */
export interface Product {
  id: string;
  title: string;
  description: string | null;
  category_id: string | null;
  images: string[];
  status: ProductStatus;
  view_count: number;
  created_at: string;
  activated_at: string | null;
  /** Minimum order quantity required to unlock the group buy */
  moq: number | null;
  /** Group buy price in Turkish Lira */
  selling_price_try: number | null;
  /** Estimated delivery lead time in days */
  lead_time_days: number | null;
  /** Total wishlist quantity currently committed */
  current_wishlist_count: number | null;
  /** Percentage of MOQ filled (0-100) */
  moq_fill_percentage: number | null;
}
