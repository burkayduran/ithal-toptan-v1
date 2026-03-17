import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { getPaymentEntry, getStatusEntry, markPaymentAsPaid } from "./api";

export function usePaymentEntry(entryId: string) {
  return useQuery({
    queryKey: ["payment", entryId],
    queryFn: () => getPaymentEntry(entryId),
    enabled: !!entryId,
  });
}

export function useStatusEntry(entryId: string) {
  return useQuery({
    queryKey: ["status", entryId],
    queryFn: () => getStatusEntry(entryId),
    enabled: !!entryId,
  });
}

export function useMarkPaymentAsPaid() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (entryId: string) => markPaymentAsPaid(entryId),
    onSuccess: (data) => {
      queryClient.setQueryData(["payment", data.id], data);
      queryClient.setQueryData(["status", data.id], data);
      // Invalidate the real wishlist so My Campaigns reflects the updated status
      queryClient.invalidateQueries({ queryKey: ["wishlist"] });
    },
  });
}
