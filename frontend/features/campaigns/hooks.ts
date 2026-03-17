import { useQuery } from "@tanstack/react-query";
import { getProducts, getProductById } from "./api";

export function useProducts() {
  return useQuery({
    queryKey: ["products"],
    queryFn: () => getProducts(),
    // Poll every 60 s — keeps home and listing in sync with detail page (30 s)
    refetchInterval: 60_000,
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
