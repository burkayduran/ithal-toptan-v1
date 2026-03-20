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
} from "./types";

const ADMIN = "/api/admin";
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

// ── Categories (unchanged — shared table) ─────────────────────────────────

export function getAdminCategories(): Promise<AdminCategory[]> {
  return api.get(`${ADMIN}/categories`);
}

export function createAdminCategory(payload: CategoryCreatePayload): Promise<AdminCategory> {
  return api.post(`${ADMIN}/categories`, payload);
}

export function updateAdminCategory(
  id: string,
  payload: CategoryUpdatePayload
): Promise<AdminCategory> {
  return api.patch(`${ADMIN}/categories/${id}`, payload);
}

export function deleteAdminCategory(id: string): Promise<void> {
  return api.delete(`${ADMIN}/categories/${id}`);
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

// ── Price Preview (unchanged — shared endpoint) ──────────────────────────

export function calculatePricePreview(payload: PricePreviewPayload): Promise<PriceBreakdown> {
  return api.post(`${ADMIN}/calculate-price`, {
    unit_price_usd: payload.unit_price_usd,
    moq: payload.moq,
    shipping_cost_usd: payload.shipping_cost_usd ?? 0,
    customs_rate: payload.customs_rate ?? 0.35,
    margin_rate: payload.margin_rate ?? 0.30,
  });
}
