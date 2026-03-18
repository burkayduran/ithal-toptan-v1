import { useQuery } from "@tanstack/react-query";
import { getProducts, getProductById, getSimilarProducts } from "./api";
import { Product, PaginatedResponse } from "./types";

export function useProducts(params?: { category_id?: string; per_page?: number }) {
  return useQuery({
    queryKey: ["products", params],
    queryFn: () => getProducts(params),
    select: (data: PaginatedResponse<Product>) => data.items,
    // Poll every 60 s — keeps home and listing in sync with detail page (30 s)
    refetchInterval: 60_000,
  });
}

export function useSimilarProducts(id: string) {
  return useQuery({
    queryKey: ["products", "similar", id],
    queryFn: () => getSimilarProducts(id),
    enabled: !!id,
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
