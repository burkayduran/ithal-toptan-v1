import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { addToWishlist, getMyWishlist } from "./api";
import { useAuthStore } from "@/features/auth/store";

export function useWishlist() {
  const { token, isHydrated } = useAuthStore();
  return useQuery({
    queryKey: ["wishlist"],
    queryFn: getMyWishlist,
    // Only run once auth state is resolved and user is logged in
    enabled: isHydrated && !!token,
  });
}

export function useJoinWishlist() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({
      request_id,
      quantity,
    }: {
      request_id: string;
      quantity: number;
    }) => addToWishlist(request_id, quantity),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["wishlist"] });
    },
  });
}
