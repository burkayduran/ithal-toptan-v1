import type { CampaignStatus } from "@/features/campaigns/types";
import type { ParticipantStatus } from "@/features/wishlist/types";
import { cn } from "@/lib/utils";

/** Unified status type covering both campaign lifecycle and participant states */
type BadgeStatus = CampaignStatus | ParticipantStatus;

interface StatusBadgeProps {
  status: BadgeStatus;
  className?: string;
}

interface StatusMeta {
  label: string;
  className: string;
}

const STATUS_META: Record<string, StatusMeta> = {
  // Campaign statuses
  active:              { label: "Aktif",               className: "bg-purple-100 text-purple-800 border-purple-200" },
  moq_reached:         { label: "Hedef Doldu",         className: "bg-blue-100 text-blue-800 border-blue-200" },
  payment_collecting:  { label: "Ödeme Toplanıyor",    className: "bg-amber-100 text-amber-800 border-amber-200" },
  ordered:             { label: "Sipariş Verildi",     className: "bg-purple-100 text-purple-800 border-purple-200" },
  shipped:             { label: "Kargoda",             className: "bg-blue-100 text-blue-800 border-blue-200" },
  delivered:           { label: "Teslim Edildi",       className: "bg-gray-100 text-gray-700 border-gray-200" },
  cancelled:           { label: "İptal Edildi",        className: "bg-red-100 text-red-700 border-red-200" },
  pending:             { label: "Beklemede",           className: "bg-yellow-100 text-yellow-800 border-yellow-200" },
  sourcing:            { label: "Tedarik Ediliyor",    className: "bg-orange-100 text-orange-800 border-orange-200" },
  // Participant statuses
  joined:              { label: "Katıldı",             className: "bg-blue-50 text-blue-700 border-blue-200" },
  invited:             { label: "Ödeme Gerekli",       className: "bg-amber-100 text-amber-800 border-amber-200" },
  paid:                { label: "Ödendi",              className: "bg-green-100 text-green-800 border-green-200" },
  expired:             { label: "Süresi Doldu",        className: "bg-red-100 text-red-700 border-red-200" },
  // Backward compat: old status values
  waiting:             { label: "Beklemede",           className: "bg-blue-50 text-blue-700 border-blue-200" },
  notified:            { label: "Ödeme Gerekli",       className: "bg-amber-100 text-amber-800 border-amber-200" },
};

const FALLBACK: StatusMeta = { label: "", className: "bg-gray-100 text-gray-600 border-gray-200" };

export default function StatusBadge({ status, className }: StatusBadgeProps) {
  const { label, className: metaClass } = STATUS_META[status] ?? { ...FALLBACK, label: status };

  return (
    <span
      className={cn(
        "inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold border",
        metaClass,
        className
      )}
    >
      {status === "active" && (
        <span className="mr-1.5 h-1.5 w-1.5 rounded-full bg-purple-500 inline-block animate-pulse" />
      )}
      {label}
    </span>
  );
}
