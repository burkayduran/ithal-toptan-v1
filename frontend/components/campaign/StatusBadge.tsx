import type { CampaignStatus } from "@/features/campaigns/types";
import type { ParticipantStatus } from "@/features/wishlist/types";
import { cn } from "@/lib/utils";
import { getStatusConfig } from "@/lib/config/campaignStatus";

/** Unified status type covering both campaign lifecycle and participant states */
type BadgeStatus = CampaignStatus | ParticipantStatus | string;

interface StatusBadgeProps {
  status: BadgeStatus;
  className?: string;
}

// Participant statuses are not in the campaign config — handle inline
const PARTICIPANT_META: Record<string, { label: string; className: string }> = {
  joined:   { label: "Katıldı",        className: "bg-blue-50 text-blue-700 border-blue-200" },
  invited:  { label: "Ödeme Gerekli",  className: "bg-amber-100 text-amber-800 border-amber-200" },
  paid:     { label: "Ödendi",         className: "bg-green-100 text-green-800 border-green-200" },
  expired:  { label: "Süresi Doldu",   className: "bg-red-100 text-red-700 border-red-200" },
  // Legacy participant statuses
  waiting:  { label: "Beklemede",      className: "bg-blue-50 text-blue-700 border-blue-200" },
  notified: { label: "Ödeme Gerekli",  className: "bg-amber-100 text-amber-800 border-amber-200" },
};

export default function StatusBadge({ status, className }: StatusBadgeProps) {
  // Participant status takes precedence over campaign config
  const participantMeta = PARTICIPANT_META[status];
  const label = participantMeta
    ? participantMeta.label
    : getStatusConfig(status).label;
  const metaClass = participantMeta
    ? participantMeta.className
    : getStatusConfig(status).badgeClassName;

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
