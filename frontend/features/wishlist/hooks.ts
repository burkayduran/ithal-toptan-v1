import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { getMyParticipations, joinCampaign, leaveCampaign } from "./api";
import { useAuthStore } from "@/features/auth/store";
import { Participant } from "./types";

export function useMyParticipations() {
  const { token, isHydrated, user } = useAuthStore();
  return useQuery({
    queryKey: ["my-participations", user?.id ?? null],
    queryFn: getMyParticipations,
    enabled: isHydrated && !!token,
  });
}

export function useJoinCampaign() {
  const queryClient = useQueryClient();
  const { user } = useAuthStore();
  const userId = user?.id ?? null;
  return useMutation({
    mutationFn: ({
      campaignId,
      quantity,
    }: {
      campaignId: string;
      quantity: number;
    }) => joinCampaign(campaignId, quantity),
    onMutate: async () => {
      await queryClient.cancelQueries({ queryKey: ["my-participations"] });
      await queryClient.cancelQueries({ queryKey: ["campaigns"] });

      const previous = queryClient.getQueryData<Participant[]>(["my-participations", userId]);
      return { previous };
    },
    onError: (_err, _variables, context) => {
      if (context?.previous) {
        queryClient.setQueryData(["my-participations", userId], context.previous);
      }
    },
    onSettled: (_data, _error, variables) => {
      queryClient.invalidateQueries({ queryKey: ["my-participations"] });
      queryClient.invalidateQueries({ queryKey: ["campaign", variables.campaignId] });
      queryClient.invalidateQueries({ queryKey: ["campaigns"] });
    },
  });
}

export function useLeaveCampaign() {
  const queryClient = useQueryClient();
  const { user } = useAuthStore();
  const userId = user?.id ?? null;
  return useMutation({
    mutationFn: (campaignId: string) => leaveCampaign(campaignId),
    onMutate: async (campaignId) => {
      await queryClient.cancelQueries({ queryKey: ["my-participations"] });

      const previous = queryClient.getQueryData<Participant[]>(["my-participations", userId]);

      if (previous) {
        queryClient.setQueryData(
          ["my-participations", userId],
          previous.filter((p) => p.campaign_id !== campaignId)
        );
      }

      return { previous };
    },
    onError: (_err, _campaignId, context) => {
      if (context?.previous) {
        queryClient.setQueryData(["my-participations", userId], context.previous);
      }
    },
    onSettled: (_data, _error, campaignId) => {
      queryClient.invalidateQueries({ queryKey: ["my-participations"] });
      queryClient.invalidateQueries({ queryKey: ["campaign", campaignId] });
      queryClient.invalidateQueries({ queryKey: ["campaigns"] });
    },
  });
}
