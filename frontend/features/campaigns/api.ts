import { api } from "@/lib/api/client";
import { Product } from "./types";

interface ListParams {
  category_id?: string;
  search?: string;
  page?: number;
  per_page?: number;
}

export async function getProducts(params?: ListParams): Promise<Product[]> {
  const qs = new URLSearchParams();
  if (params?.category_id) qs.set("category_id", params.category_id);
  if (params?.search) qs.set("search", params.search);
  if (params?.page != null) qs.set("page", String(params.page));
  if (params?.per_page != null) qs.set("per_page", String(params.per_page));
  const query = qs.toString();
  return api.get<Product[]>(`/api/v1/products${query ? `?${query}` : ""}`);
}

export async function getProductById(id: string): Promise<Product> {
  return api.get<Product>(`/api/v1/products/${id}`);
}
