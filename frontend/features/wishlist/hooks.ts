import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { addToWishlist, getMyWishlist, removeFromWishlist } from "./api";
import { useAuthStore } from "@/features/auth/store";
import { WishlistEntry } from "./types";

export function useWishlist() {
  const { token, isHydrated, user } = useAuthStore();
  return useQuery({
    queryKey: ["wishlist", user?.id ?? null],
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
    onMutate: async (variables) => {
      // Cancel outgoing queries so they don't overwrite optimistic update
      await queryClient.cancelQueries({ queryKey: ["wishlist"] });
      await queryClient.cancelQueries({ queryKey: ["products"] });

      // Snapshot current wishlist for rollback
      const previousWishlist = queryClient.getQueryData<WishlistEntry[]>(["wishlist"]);

      return { previousWishlist };
    },
    onError: (_err, _variables, context) => {
      // Rollback on error
      if (context?.previousWishlist) {
        queryClient.setQueryData(["wishlist"], context.previousWishlist);
      }
    },
    onSettled: (_data, _error, variables) => {
      // Always refetch after mutation
      queryClient.invalidateQueries({ queryKey: ["wishlist"] });
      queryClient.invalidateQueries({ queryKey: ["product", variables.request_id] });
      queryClient.invalidateQueries({ queryKey: ["products"] });
    },
  });
}

export function useRemoveFromWishlist() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (request_id: string) => removeFromWishlist(request_id),
    onMutate: async (request_id) => {
      await queryClient.cancelQueries({ queryKey: ["wishlist"] });

      const previousWishlist = queryClient.getQueryData<WishlistEntry[]>(["wishlist"]);

      // Optimistically remove the entry
      if (previousWishlist) {
        queryClient.setQueryData(
          ["wishlist"],
          previousWishlist.filter((e) => e.request_id !== request_id)
        );
      }

      return { previousWishlist };
    },
    onError: (_err, _request_id, context) => {
      if (context?.previousWishlist) {
        queryClient.setQueryData(["wishlist"], context.previousWishlist);
      }
    },
    onSettled: (_data, _error, request_id) => {
      queryClient.invalidateQueries({ queryKey: ["wishlist"] });
      queryClient.invalidateQueries({ queryKey: ["product", request_id] });
      queryClient.invalidateQueries({ queryKey: ["products"] });
    },
  });
}
