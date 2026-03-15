export type WishlistStatus = "waiting" | "notified" | "paid" | "expired";

export interface WishlistEntry {
  id: string;
  requestId: string; // campaign id
  campaignSlug: string;
  quantity: number;
  status: WishlistStatus;
  joinedAt: string;
}
