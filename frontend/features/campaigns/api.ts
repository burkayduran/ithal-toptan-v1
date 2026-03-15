import { Campaign } from "./types";
import { mockCampaigns } from "./mock";

const delay = (ms = 400) => new Promise((r) => setTimeout(r, ms));

export async function getCampaigns(): Promise<Campaign[]> {
  await delay();
  return mockCampaigns;
}

export async function getCampaignBySlug(slug: string): Promise<Campaign> {
  await delay();
  const campaign = mockCampaigns.find((c) => c.slug === slug);
  if (!campaign) throw new Error("Kampanya bulunamadı.");
  return campaign;
}

export async function getMyCampaigns(wishlistIds: string[]): Promise<Campaign[]> {
  await delay(200);
  return mockCampaigns.filter((c) => wishlistIds.includes(c.id));
}
