import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { getPaymentEntry, getStatusEntry, confirmPayment } from "./api";

export function usePaymentEntry(participantId: string) {
  return useQuery({
    queryKey: ["payment", participantId],
    queryFn: () => getPaymentEntry(participantId),
    enabled: !!participantId,
  });
}

export function useStatusEntry(participantId: string) {
  return useQuery({
    queryKey: ["status", participantId],
    queryFn: () => getStatusEntry(participantId),
    enabled: !!participantId,
  });
}

export function useConfirmPayment() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (participantId: string) => confirmPayment(participantId),
    onSuccess: (data) => {
      queryClient.setQueryData(["payment", data.id], data);
      queryClient.setQueryData(["status", data.id], data);
      queryClient.invalidateQueries({ queryKey: ["my-participations"] });
    },
  });
}
