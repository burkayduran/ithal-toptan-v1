import { CampaignStatus } from "@/features/campaigns/types";

export function getStatusLabel(status: CampaignStatus): string {
  switch (status) {
    case "active":
      return "Aktif";
    case "moq_reached":
      return "Hedef Doldu";
    case "closed":
      return "Kapandı";
  }
}

export function getStatusVariant(
  status: CampaignStatus
): "default" | "secondary" | "destructive" | "outline" {
  switch (status) {
    case "active":
      return "default";
    case "moq_reached":
      return "secondary";
    case "closed":
      return "outline";
  }
}
