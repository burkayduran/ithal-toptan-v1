/**
 * Single source of truth for campaign status display metadata.
 *
 * All UI layers (StatusBadge, status labels, admin pages, filter pills)
 * import from here. Adding a new status means editing exactly one file.
 */

export interface StatusConfig {
  /** Full Turkish display label (public-facing) */
  label: string;
  /** Shorter label for admin table cells */
  adminLabel: string;
  /** Tailwind classes for the badge pill */
  badgeClassName: string;
  /** Badge variant for shadcn/ui <Badge> (admin tables) */
  badgeVariant: "default" | "secondary" | "destructive" | "outline";
  /** Canonical pipeline order (0 = earliest) */
  order: number;
  /** Label shown in filter pills (if this status is filterable) */
  filterLabel?: string;
}

export const CAMPAIGN_STATUS_CONFIG: Record<string, StatusConfig> = {
  draft: {
    label: "Taslak",
    adminLabel: "Taslak",
    badgeClassName: "bg-gray-100 text-gray-700 border-gray-200",
    badgeVariant: "secondary",
    order: 0,
  },
  active: {
    label: "Aktif",
    adminLabel: "Aktif",
    badgeClassName: "bg-purple-100 text-purple-800 border-purple-200",
    badgeVariant: "default",
    order: 1,
    filterLabel: "Aktif",
  },
  moq_reached: {
    label: "Hedef Doldu",
    adminLabel: "MOQ Doldu",
    badgeClassName: "bg-blue-100 text-blue-800 border-blue-200",
    badgeVariant: "default",
    order: 2,
    filterLabel: "Hedefe Ulaştı",
  },
  payment_collecting: {
    label: "Ödeme Toplanıyor",
    adminLabel: "Ödeme",
    badgeClassName: "bg-amber-100 text-amber-800 border-amber-200",
    badgeVariant: "default",
    order: 3,
    filterLabel: "Ödeme Aşaması",
  },
  ordered: {
    label: "Sipariş Verildi",
    adminLabel: "Sipariş",
    badgeClassName: "bg-purple-100 text-purple-800 border-purple-200",
    badgeVariant: "outline",
    order: 4,
  },
  shipped: {
    label: "Kargoda",
    adminLabel: "Kargoda",
    badgeClassName: "bg-blue-100 text-blue-800 border-blue-200",
    badgeVariant: "outline",
    order: 5,
  },
  delivered: {
    label: "Teslim Edildi",
    adminLabel: "Teslim",
    badgeClassName: "bg-gray-100 text-gray-700 border-gray-200",
    badgeVariant: "outline",
    order: 6,
  },
  cancelled: {
    label: "İptal Edildi",
    adminLabel: "İptal",
    badgeClassName: "bg-red-100 text-red-700 border-red-200",
    badgeVariant: "destructive",
    order: 7,
  },
  // ── Legacy / backward-compat ──────────────────────────────────────────────
  failed: {
    label: "Başarısız",
    adminLabel: "Başarısız",
    badgeClassName: "bg-red-100 text-red-700 border-red-200",
    badgeVariant: "destructive",
    order: 99,
  },
};

/** Statuses ordered by pipeline position. */
export const STATUS_ORDER: string[] = Object.entries(CAMPAIGN_STATUS_CONFIG)
  .sort(([, a], [, b]) => a.order - b.order)
  .map(([key]) => key);

/** Helper — get config entry or a safe fallback. */
export function getStatusConfig(status: string): StatusConfig {
  return (
    CAMPAIGN_STATUS_CONFIG[status] ?? {
      label: status,
      adminLabel: status,
      badgeClassName: "bg-gray-100 text-gray-600 border-gray-200",
      badgeVariant: "outline" as const,
      order: 99,
    }
  );
}
