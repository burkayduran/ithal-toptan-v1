import { WishlistEntry } from "./types";
import { addToMockWishlist, getMockWishlist } from "./mock";

const delay = (ms = 600) => new Promise((r) => setTimeout(r, ms));

export async function joinWishlist(requestId: string, campaignSlug: string, quantity: number): Promise<WishlistEntry> {
  await delay();
  const entry: WishlistEntry = {
    id: `wl_${Date.now()}`,
    requestId,
    campaignSlug,
    quantity,
    status: "waiting",
    joinedAt: new Date().toISOString(),
  };
  addToMockWishlist(entry);
  return entry;
}

export async function getWishlist(): Promise<WishlistEntry[]> {
  await delay(200);
  return getMockWishlist();
}
