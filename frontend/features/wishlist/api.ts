import { api } from "@/lib/api/client";
import { Participant } from "./types";

const V2 = "/api/v2";

export async function getMyParticipations(): Promise<Participant[]> {
  return api.get<Participant[]>(`${V2}/campaigns/my`);
}

export async function joinCampaign(
  campaignId: string,
  quantity: number
): Promise<Participant> {
  return api.post<Participant>(`${V2}/campaigns/${campaignId}/join`, { quantity });
}

export async function leaveCampaign(campaignId: string): Promise<void> {
  return api.delete(`${V2}/campaigns/${campaignId}/leave`);
}
