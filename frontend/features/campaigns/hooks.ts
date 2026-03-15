import { useQuery } from "@tanstack/react-query";
import { getCampaigns, getCampaignBySlug, getMyCampaigns } from "./api";

export function useCampaigns() {
  return useQuery({
    queryKey: ["campaigns"],
    queryFn: getCampaigns,
  });
}

export function useCampaign(slug: string) {
  return useQuery({
    queryKey: ["campaign", slug],
    queryFn: () => getCampaignBySlug(slug),
    enabled: !!slug,
  });
}

export function useMyCampaigns(wishlistIds: string[]) {
  return useQuery({
    queryKey: ["my-campaigns", wishlistIds],
    queryFn: () => getMyCampaigns(wishlistIds),
    enabled: wishlistIds.length > 0,
  });
}
