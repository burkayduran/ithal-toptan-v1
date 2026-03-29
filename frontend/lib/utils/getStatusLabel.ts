import type { CampaignStatus } from "@/features/campaigns/types";
import type { ParticipantStatus } from "@/features/wishlist/types";
import { getStatusConfig } from "@/lib/config/campaignStatus";

/** Returns the Turkish display label for a campaign status. */
export function getCampaignStatusLabel(status: CampaignStatus | string): string {
  return getStatusConfig(status).label;
}

export function getParticipantStatusLabel(status: ParticipantStatus): string {
  switch (status) {
    case "joined":    return "Beklemede";
    case "invited":   return "Ödeme Bekliyor";
    case "paid":      return "Ödendi";
    case "expired":   return "Süresi Doldu";
    case "cancelled": return "İptal";
    default:          return status;
  }
}

// Backward-compatible alias
export const getStatusLabel = getCampaignStatusLabel;

export function getStatusVariant(
  status: CampaignStatus | string
): "default" | "secondary" | "destructive" | "outline" {
  return getStatusConfig(status).badgeVariant;
}
