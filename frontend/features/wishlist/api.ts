import { api } from "@/lib/api/client";
import { WishlistEntry } from "./types";

export async function getMyWishlist(): Promise<WishlistEntry[]> {
  return api.get<WishlistEntry[]>("/api/v1/wishlist/my");
}

export async function addToWishlist(
  request_id: string,
  quantity: number
): Promise<WishlistEntry> {
  return api.post<WishlistEntry>("/api/v1/wishlist/add", { request_id, quantity });
}

export async function removeFromWishlist(request_id: string): Promise<void> {
  return api.delete(`/api/v1/wishlist/${request_id}`);
}
