import { useQuery } from "@tanstack/react-query";
import { getProducts, getProductById } from "./api";

export function useProducts() {
  return useQuery({
    queryKey: ["products"],
    queryFn: () => getProducts(),
  });
}

export function useProduct(id: string) {
  return useQuery({
    queryKey: ["product", id],
    queryFn: () => getProductById(id),
    enabled: !!id,
    // Poll every 30 s so campaign progress stays fresh without SSE
    refetchInterval: 30_000,
  });
}
