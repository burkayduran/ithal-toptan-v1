import { Campaign } from "./types";
import { isCampaignReached } from "@/lib/utils/campaign";

export type StatusFilter =
  | "all"
  | "active"
  | "near_unlock"
  | "moq_reached"
  | "payment_collecting";

export type SortOption = "near_unlock" | "newest" | "lowest_price";

export function filterCampaigns(
  campaigns: Campaign[],
  { search, status }: { search: string; status: StatusFilter }
): Campaign[] {
  let result = campaigns.filter((c) =>
    ["active", "moq_reached", "payment_collecting"].includes(c.status)
  );

  if (search.trim()) {
    const q = search.trim().toLowerCase();
    result = result.filter(
      (c) =>
        c.title.toLowerCase().includes(q) ||
        c.description?.toLowerCase().includes(q)
    );
  }

  switch (status) {
    case "active":
      return result.filter((c) => c.status === "active");
    case "near_unlock":
      return result.filter(
        (c) => c.status === "active" && (c.moq_fill_percentage ?? 0) >= 60
      );
    case "moq_reached":
      return result.filter((c) => c.status === "moq_reached" && isCampaignReached(c));
    case "payment_collecting":
      return result.filter((c) => c.status === "payment_collecting");
    default:
      return result;
  }
}

export function sortCampaigns(campaigns: Campaign[], sort: SortOption): Campaign[] {
  const copy = [...campaigns];
  switch (sort) {
    case "near_unlock":
      return copy.sort(
        (a, b) => (b.moq_fill_percentage ?? 0) - (a.moq_fill_percentage ?? 0)
      );
    case "newest":
      return copy.sort(
        (a, b) =>
          new Date(b.activated_at ?? b.created_at).getTime() -
          new Date(a.activated_at ?? a.created_at).getTime()
      );
    case "lowest_price":
      return copy.sort((a, b) => {
        if (a.selling_price_try == null) return 1;
        if (b.selling_price_try == null) return -1;
        return a.selling_price_try - b.selling_price_try;
      });
    default:
      return copy;
  }
}
