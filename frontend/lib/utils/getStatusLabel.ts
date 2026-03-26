import { CampaignStatus } from "@/features/campaigns/types";
import { ParticipantStatus } from "@/features/wishlist/types";

export function getCampaignStatusLabel(status: CampaignStatus): string {
  switch (status) {
    case "active":
      return "Aktif";
    case "moq_reached":
      return "Hedef Doldu";
    case "payment_collecting":
      return "Ödeme Toplanıyor";
    case "ordered":
      return "Sipariş Verildi";
    case "delivered":
      return "Teslim Edildi";
    case "cancelled":
      return "İptal Edildi";
    case "draft":
      return "Taslak";
    default:
      return status;
  }
}

export function getParticipantStatusLabel(status: ParticipantStatus): string {
  switch (status) {
    case "joined":
      return "Beklemede";
    case "invited":
      return "Ödeme Bekliyor";
    case "paid":
      return "Ödendi";
    case "expired":
      return "Süresi Doldu";
    case "cancelled":
      return "İptal";
    default:
      return status;
  }
}

// Keep backward-compatible aliases
export const getStatusLabel = getCampaignStatusLabel;

export function getStatusVariant(
  status: CampaignStatus
): "default" | "secondary" | "destructive" | "outline" {
  switch (status) {
    case "active":
      return "default";
    case "moq_reached":
    case "payment_collecting":
    case "ordered":
    case "delivered":
      return "secondary";
    case "cancelled":
      return "destructive";
    default:
      return "outline";
  }
}
