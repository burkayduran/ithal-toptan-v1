import { api } from "@/lib/api/client";
import type {
  AdminCampaign,
  AdminCategory,
  AdminSuggestion,
  PriceBreakdown,
  CampaignCreatePayload,
  CampaignUpdatePayload,
  CategoryCreatePayload,
  CategoryUpdatePayload,
  SuggestionUpdatePayload,
  PricePreviewPayload,
  DashboardSummary,
  DemandEntriesResponse,
  DemandUsersResponse,
  FraudWatchResponse,
  ActionItemsResponse,
} from "./types";

const ADMIN_V2 = "/api/v2/admin";

// ── Campaigns (V2) ───────────────────────────────────────────────────────

export function getAdminCampaigns(): Promise<AdminCampaign[]> {
  return api.get(`${ADMIN_V2}/campaigns`);
}

export function getAdminCampaign(id: string): Promise<AdminCampaign> {
  return api.get(`${ADMIN_V2}/campaigns/${id}`);
}

export function createAdminCampaign(payload: CampaignCreatePayload): Promise<AdminCampaign> {
  return api.post(`${ADMIN_V2}/campaigns`, payload);
}

export function publishAdminCampaign(id: string): Promise<{ message: string; id: string }> {
  return api.post(`${ADMIN_V2}/campaigns/${id}/publish`);
}

// Bulk operations — V2
export function bulkPublishCampaigns(
  campaign_ids: string[]
): Promise<{ published: string[]; failed: { id: string; reason: string }[] }> {
  return api.post(`${ADMIN_V2}/campaigns/bulk-publish`, campaign_ids);
}

export function bulkCancelCampaigns(
  campaign_ids: string[]
): Promise<{ cancelled: string[]; failed: { id: string; reason: string }[] }> {
  return api.post(`${ADMIN_V2}/campaigns/bulk-cancel`, campaign_ids);
}

// Update — V2
export function updateAdminCampaign(
  id: string,
  payload: CampaignUpdatePayload
): Promise<AdminCampaign> {
  return api.patch(`${ADMIN_V2}/campaigns/${id}`, payload);
}

// ── Categories (V2) ─────────────────────────────────────────────────────────

export function getAdminCategories(): Promise<AdminCategory[]> {
  return api.get(`${ADMIN_V2}/categories`);
}

export function createAdminCategory(payload: CategoryCreatePayload): Promise<AdminCategory> {
  return api.post(`${ADMIN_V2}/categories`, payload);
}

export function updateAdminCategory(
  id: string,
  payload: CategoryUpdatePayload
): Promise<AdminCategory> {
  return api.patch(`${ADMIN_V2}/categories/${id}`, payload);
}

export function deleteAdminCategory(id: string): Promise<void> {
  return api.delete(`${ADMIN_V2}/categories/${id}`);
}

// ── Suggestions (V2) ─────────────────────────────────────────────────────

export function getAdminSuggestions(
  status = "pending"
): Promise<AdminSuggestion[]> {
  return api.get(`${ADMIN_V2}/suggestions?status=${encodeURIComponent(status)}`);
}

export function updateAdminSuggestion(
  id: string,
  payload: SuggestionUpdatePayload
): Promise<AdminSuggestion> {
  return api.patch(`${ADMIN_V2}/suggestions/${id}`, payload);
}

// ── Price Preview (V2) ──────────────────────────────────────────────────────

export function calculatePricePreview(payload: PricePreviewPayload): Promise<PriceBreakdown> {
  return api.post(`${ADMIN_V2}/calculate-price`, {
    unit_price_usd: payload.unit_price_usd,
    moq: payload.moq,
    shipping_cost_usd: payload.shipping_cost_usd ?? 0,
    customs_rate: payload.customs_rate ?? 0.35,
    margin_rate: payload.margin_rate ?? 0.30,
  });
}

// ── Dashboard Summary ─────────────────────────────────────────────────────

export function getDashboardSummary(): Promise<DashboardSummary> {
  return api.get(`${ADMIN_V2}/dashboard-summary`);
}

// ── Demand Entries ───────────────────────────────────────────────────────

export function getCampaignDemandEntries(campaignId: string): Promise<DemandEntriesResponse> {
  return api.get(`${ADMIN_V2}/campaigns/${campaignId}/demand-entries`);
}

export function deleteDemandEntry(entryId: string, reason?: string): Promise<{ message: string }> {
  const params = reason ? `?reason=${encodeURIComponent(reason)}` : "";
  return api.delete(`${ADMIN_V2}/demand-entries/${entryId}${params}`);
}

export function updateDemandEntry(
  entryId: string,
  data: { admin_note?: string; status?: string }
): Promise<{ id: string; status: string; admin_note: string | null }> {
  return api.patch(`${ADMIN_V2}/demand-entries/${entryId}`, data);
}

// ── Demand Users ─────────────────────────────────────────────────────────────

export function getDemandUsers(sort = "quantity_desc"): Promise<DemandUsersResponse> {
  return api.get(`${ADMIN_V2}/demand-users?sort=${encodeURIComponent(sort)}`);
}

// ── Fraud Watch ───────────────────────────────────────────────────────────────

export function getFraudWatch(): Promise<FraudWatchResponse> {
  return api.get(`${ADMIN_V2}/fraud-watch`);
}

// ── Action Items ──────────────────────────────────────────────────────────────

export function getActionItems(): Promise<ActionItemsResponse> {
  return api.get(`${ADMIN_V2}/action-items`);
}

export function uploadProductImage(file: File): Promise<{ url: string; filename: string }> {
  const formData = new FormData();
  formData.append("file", file);
  // Use fetch directly to handle multipart/form-data with auth
  const token = typeof window !== "undefined" ? localStorage.getItem("access_token") : null;
  return fetch(`/api/v2/admin/uploads/image`, {
    method: "POST",
    headers: token ? { Authorization: `Bearer ${token}` } : {},
    body: formData,
  }).then(async (res) => {
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || "Upload failed");
    }
    return res.json();
  });
}
