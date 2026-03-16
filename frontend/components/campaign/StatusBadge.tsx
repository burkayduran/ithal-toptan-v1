import type { ProductStatus } from "@/features/campaigns/types";
import type { WishlistStatus } from "@/features/wishlist/types";
import { cn } from "@/lib/utils";

/** Unified status type covering both product lifecycle and wishlist entry states */
type BadgeStatus = ProductStatus | WishlistStatus;

interface StatusBadgeProps {
  status: BadgeStatus;
  className?: string;
}

const STYLES: Record<string, string> = {
  // Product statuses
  active: "bg-green-100 text-green-800 border-green-200",
  moq_reached: "bg-blue-100 text-blue-800 border-blue-200",
  payment_collecting: "bg-amber-100 text-amber-800 border-amber-200",
  ordered: "bg-purple-100 text-purple-800 border-purple-200",
  delivered: "bg-gray-100 text-gray-700 border-gray-200",
  cancelled: "bg-red-100 text-red-700 border-red-200",
  pending: "bg-yellow-100 text-yellow-800 border-yellow-200",
  sourcing: "bg-orange-100 text-orange-800 border-orange-200",
  // Wishlist entry statuses
  waiting: "bg-blue-50 text-blue-700 border-blue-200",
  notified: "bg-amber-100 text-amber-800 border-amber-200",
  paid: "bg-green-100 text-green-800 border-green-200",
  expired: "bg-red-100 text-red-700 border-red-200",
};

const LABELS: Record<string, string> = {
  // Product statuses
  active: "Aktif",
  moq_reached: "Hedef Doldu",
  payment_collecting: "Ödeme Toplanıyor",
  ordered: "Sipariş Verildi",
  delivered: "Teslim Edildi",
  cancelled: "İptal Edildi",
  pending: "Beklemede",
  sourcing: "Tedarik Ediliyor",
  // Wishlist entry statuses
  waiting: "Beklemede",
  notified: "Ödeme Gerekli",
  paid: "Ödendi",
  expired: "Süresi Doldu",
};

export default function StatusBadge({ status, className }: StatusBadgeProps) {
  const styles = STYLES[status] ?? "bg-gray-100 text-gray-600 border-gray-200";
  const label = LABELS[status] ?? status;

  return (
    <span
      className={cn(
        "inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold border",
        styles,
        className
      )}
    >
      {status === "active" && (
        <span className="mr-1.5 h-1.5 w-1.5 rounded-full bg-green-500 inline-block animate-pulse" />
      )}
      {label}
    </span>
  );
}
