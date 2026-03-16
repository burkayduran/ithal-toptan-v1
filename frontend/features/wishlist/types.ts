/** Matches backend WishlistEntry status values */
export type WishlistStatus = "waiting" | "notified" | "paid" | "expired" | "cancelled";

/** Matches backend WishlistResponse – includes denormalized product fields */
export interface WishlistEntry {
  id: string;
  /** The product/request ID this entry belongs to */
  request_id: string;
  user_id: string;
  quantity: number;
  status: WishlistStatus;
  joined_at: string;
  notified_at: string | null;
  payment_deadline: string | null;
  /** Denormalized from product – may be null if product was deleted */
  product_title: string | null;
  product_image: string | null;
  selling_price_try: number | null;
}
