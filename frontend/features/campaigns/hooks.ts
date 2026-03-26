import { useQuery } from "@tanstack/react-query";
import { getCampaigns, getCampaignById, getSimilarCampaigns } from "./api";
import { Campaign, PaginatedResponse } from "./types";

export function useCampaigns(params?: { category_id?: string; per_page?: number }) {
  return useQuery({
    queryKey: ["campaigns", params],
    queryFn: () => getCampaigns(params),
    select: (data: PaginatedResponse<Campaign>) => data.items,
    refetchInterval: 60_000,
  });
}

export function useCampaign(id: string) {
  return useQuery({
    queryKey: ["campaign", id],
    queryFn: () => getCampaignById(id),
    enabled: !!id,
    refetchInterval: 30_000,
  });
}

export function useSimilarCampaigns(id: string) {
  return useQuery({
    queryKey: ["campaigns", "similar", id],
    queryFn: () => getSimilarCampaigns(id),
    enabled: !!id,
  });
}
