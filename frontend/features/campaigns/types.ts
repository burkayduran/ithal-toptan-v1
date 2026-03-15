export type CampaignStatus = "active" | "moq_reached" | "closed";

export interface Campaign {
  id: string;
  slug: string;
  title: string;
  description: string;
  images: string[];
  status: CampaignStatus;
  groupPrice: number;
  retailPrice: number;
  currentCount: number;
  targetCount: number;
  etaText: string;
  category: string;
  shortSpecs?: string[];
}
