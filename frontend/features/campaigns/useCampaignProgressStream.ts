import { useState, useEffect } from "react";

export interface CampaignProgress {
  campaign_id: string;
  current_participant_count: number | null;
  moq_fill_percentage: number | null;
}

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export function useCampaignProgressStream(
  campaignId: string,
  moq: number | null,
): {
  progress: CampaignProgress | null;
} {
  const [currentCount, setCurrentCount] = useState<number | null>(null);

  useEffect(() => {
    if (!campaignId) return;

    const url = `${API_URL}/api/v2/moq/progress/${campaignId}`;
    const source = new EventSource(url);

    source.onmessage = (event) => {
      const count = parseInt(event.data, 10);
      if (!isNaN(count)) {
        setCurrentCount(count);
      }
    };

    source.onerror = () => {
      // SSE bağlantısı koparsa sessizce kapat
      // Polling fallback zaten useCampaign hook'unda var
      source.close();
    };

    return () => {
      source.close();
    };
  }, [campaignId]);

  if (currentCount === null) {
    return { progress: null };
  }

  const target = moq ?? 0;
  return {
    progress: {
      campaign_id: campaignId,
      current_participant_count: currentCount,
      moq_fill_percentage: target > 0 ? Math.round((currentCount / target) * 1000) / 10 : null,
    },
  };
}
