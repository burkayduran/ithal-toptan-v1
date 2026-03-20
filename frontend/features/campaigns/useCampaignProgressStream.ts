import { useCampaign } from "./hooks";

export interface CampaignProgress {
  campaign_id: string;
  current_participant_count: number | null;
  moq_fill_percentage: number | null;
}

export function useCampaignProgressStream(campaignId: string): {
  progress: CampaignProgress | null;
} {
  const { data } = useCampaign(campaignId);
  return {
    progress: data
      ? {
          campaign_id: campaignId,
          current_participant_count: data.current_participant_count,
          moq_fill_percentage: data.moq_fill_percentage,
        }
      : null,
  };
}
