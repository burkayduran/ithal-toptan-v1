import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { addToWishlist, getMyWishlist, removeFromWishlist } from "./api";
import { useAuthStore } from "@/features/auth/store";

export function useWishlist() {
  const { token, isHydrated } = useAuthStore();
  return useQuery({
    queryKey: ["wishlist"],
    queryFn: getMyWishlist,
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
    onSuccess: (data) => {
      // Wishlist list reflects the new entry immediately
      queryClient.invalidateQueries({ queryKey: ["wishlist"] });
      // The joined product's current_wishlist_count / moq_fill_percentage changed
      queryClient.invalidateQueries({ queryKey: ["product", data.request_id] });
      // Product list cards also show live counts
      queryClient.invalidateQueries({ queryKey: ["products"] });
    },
  });
}

export function useRemoveFromWishlist() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (request_id: string) => removeFromWishlist(request_id),
    onSuccess: (_data, request_id) => {
      queryClient.invalidateQueries({ queryKey: ["wishlist"] });
      // Count decreased — keep product detail fresh
      queryClient.invalidateQueries({ queryKey: ["product", request_id] });
      queryClient.invalidateQueries({ queryKey: ["products"] });
    },
  });
}
