import { WishlistEntry } from "./types";

// In-memory store for joined wishlist items (simulates user session data)
let mockWishlist: WishlistEntry[] = [];

export function getMockWishlist(): WishlistEntry[] {
  // Try to hydrate from localStorage on client
  if (typeof window !== "undefined") {
    const stored = localStorage.getItem("wishlist");
    if (stored) {
      try {
        mockWishlist = JSON.parse(stored);
      } catch {
        mockWishlist = [];
      }
    }
  }
  return mockWishlist;
}

export function addToMockWishlist(entry: WishlistEntry): void {
  mockWishlist = [...getMockWishlist(), entry];
  if (typeof window !== "undefined") {
    localStorage.setItem("wishlist", JSON.stringify(mockWishlist));
  }
}
