import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { joinWishlist, getWishlist } from "./api";

export function useWishlist() {
  return useQuery({
    queryKey: ["wishlist"],
    queryFn: getWishlist,
  });
}

export function useJoinWishlist() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({
      requestId,
      campaignSlug,
      quantity,
    }: {
      requestId: string;
      campaignSlug: string;
      quantity: number;
    }) => joinWishlist(requestId, campaignSlug, quantity),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["wishlist"] });
      queryClient.invalidateQueries({ queryKey: ["my-campaigns"] });
    },
  });
}
