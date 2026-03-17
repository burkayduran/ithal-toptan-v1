import { useProduct } from "./hooks";

export interface CampaignProgress {
  product_id: string;
  current_wishlist_count: number | null;
  moq_fill_percentage: number | null;
}

/**
 * Returns live campaign progress.
 *
 * Currently backed by polling (30 s interval via useProduct).
 * To upgrade to SSE without touching any UI component:
 *   1. Open an EventSource to GET /api/v1/products/{id}/stream
 *   2. Parse incoming events and update local state
 *   3. Return the same { progress } shape below
 */
export function useCampaignProgressStream(productId: string): {
  progress: CampaignProgress | null;
} {
  const { data } = useProduct(productId);
  return {
    progress: data
      ? {
          product_id: productId,
          current_wishlist_count: data.current_wishlist_count,
          moq_fill_percentage: data.moq_fill_percentage,
        }
      : null,
  };
}
