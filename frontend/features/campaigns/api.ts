import { api } from "@/lib/api/client";
import { Campaign, PaginatedResponse } from "./types";

const V2 = "/api/v2";

interface ListParams {
  category_id?: string;
  search?: string;
  page?: number;
  per_page?: number;
}

export async function getCampaigns(params?: ListParams): Promise<PaginatedResponse<Campaign>> {
  const qs = new URLSearchParams();
  if (params?.category_id) qs.set("category_id", params.category_id);
  if (params?.search) qs.set("search", params.search);
  if (params?.page != null) qs.set("page", String(params.page));
  if (params?.per_page != null) qs.set("per_page", String(params.per_page));
  const query = qs.toString();
  return api.get<PaginatedResponse<Campaign>>(`${V2}/campaigns${query ? `?${query}` : ""}`);
}

export async function getCampaignById(id: string): Promise<Campaign> {
  return api.get<Campaign>(`${V2}/campaigns/${id}`);
}

export async function getSimilarCampaigns(id: string, limit = 3): Promise<Campaign[]> {
  return api.get<Campaign[]>(`${V2}/campaigns/${id}/similar?limit=${limit}`);
}
