import { Product } from "./types";

export type StatusFilter =
  | "all"
  | "active"
  | "near_unlock"
  | "moq_reached"
  | "payment_collecting";

export type SortOption = "near_unlock" | "newest" | "lowest_price";

/**
 * Filter products by search text and status tab.
 * Always excludes pending/sourcing/cancelled/delivered — those are internal states.
 */
export function filterProducts(
  products: Product[],
  { search, status }: { search: string; status: StatusFilter }
): Product[] {
  // Public-facing statuses only
  let result = products.filter((p) =>
    ["active", "moq_reached", "payment_collecting", "ordered"].includes(p.status)
  );

  if (search.trim()) {
    const q = search.trim().toLowerCase();
    result = result.filter(
      (p) =>
        p.title.toLowerCase().includes(q) ||
        p.description?.toLowerCase().includes(q)
    );
  }

  switch (status) {
    case "active":
      return result.filter((p) => p.status === "active");
    case "near_unlock":
      return result.filter(
        (p) => p.status === "active" && (p.moq_fill_percentage ?? 0) >= 60
      );
    case "moq_reached":
      return result.filter((p) => p.status === "moq_reached");
    case "payment_collecting":
      return result.filter((p) => p.status === "payment_collecting");
    default:
      return result;
  }
}

/** Sort a product list in-place (returns new array). */
export function sortProducts(products: Product[], sort: SortOption): Product[] {
  const copy = [...products];
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
