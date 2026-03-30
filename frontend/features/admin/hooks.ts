import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  getAdminCampaigns,
  getAdminCampaign,
  createAdminCampaign,
  updateAdminCampaign,
  publishAdminCampaign,
  bulkPublishCampaigns,
  bulkCancelCampaigns,
  getAdminCategories,
  createAdminCategory,
  updateAdminCategory,
  deleteAdminCategory,
  getAdminSuggestions,
  updateAdminSuggestion,
  calculatePricePreview,
  getDashboardSummary,
  getCampaignDemandEntries,
  deleteDemandEntry,
  uploadProductImage,
  getDemandUsers,
  getFraudWatch,
  getActionItems,
} from "./api";
import type {
  CampaignCreatePayload,
  CampaignUpdatePayload,
  CategoryCreatePayload,
  CategoryUpdatePayload,
  SuggestionUpdatePayload,
  PricePreviewPayload,
} from "./types";

// ── Campaigns ─────────────────────────────────────────────────────────────

export function useAdminCampaigns() {
  return useQuery({
    queryKey: ["admin", "campaigns"],
    queryFn: getAdminCampaigns,
  });
}

export function useAdminCampaign(id: string) {
  return useQuery({
    queryKey: ["admin", "campaigns", id],
    queryFn: () => getAdminCampaign(id),
    enabled: !!id,
  });
}

export function useCreateCampaign() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (payload: CampaignCreatePayload) => createAdminCampaign(payload),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["admin", "campaigns"] });
    },
  });
}

export function useUpdateCampaign(id: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (payload: CampaignUpdatePayload) => updateAdminCampaign(id, payload),
    onSuccess: (data) => {
      qc.invalidateQueries({ queryKey: ["admin", "campaigns"] });
      qc.setQueryData(["admin", "campaigns", id], data);
      qc.invalidateQueries({ queryKey: ["campaign", id] });
      qc.invalidateQueries({ queryKey: ["campaigns"] });
    },
  });
}

export function usePublishCampaign() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => publishAdminCampaign(id),
    onSuccess: (_data, id) => {
      qc.invalidateQueries({ queryKey: ["admin", "campaigns"] });
      qc.invalidateQueries({ queryKey: ["admin", "campaigns", id] });
      qc.invalidateQueries({ queryKey: ["campaigns"] });
    },
  });
}

export function useBulkPublishCampaigns() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (ids: string[]) => bulkPublishCampaigns(ids),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["admin", "campaigns"] });
      qc.invalidateQueries({ queryKey: ["campaigns"] });
    },
  });
}

export function useBulkCancelCampaigns() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (ids: string[]) => bulkCancelCampaigns(ids),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["admin", "campaigns"] });
      qc.invalidateQueries({ queryKey: ["campaigns"] });
    },
  });
}

// ── Categories (unchanged) ────────────────────────────────────────────────

export function useAdminCategories() {
  return useQuery({
    queryKey: ["admin", "categories"],
    queryFn: getAdminCategories,
  });
}

export function useCreateCategory() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (payload: CategoryCreatePayload) => createAdminCategory(payload),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["admin", "categories"] });
    },
  });
}

export function useUpdateCategory() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, payload }: { id: string; payload: CategoryUpdatePayload }) =>
      updateAdminCategory(id, payload),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["admin", "categories"] });
    },
  });
}

export function useDeleteCategory() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => deleteAdminCategory(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["admin", "categories"] });
    },
  });
}

// ── Suggestions ───────────────────────────────────────────────────────────

export function useAdminSuggestions(status = "pending") {
  return useQuery({
    queryKey: ["admin", "suggestions", status],
    queryFn: () => getAdminSuggestions(status),
  });
}

export function useUpdateSuggestion() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, payload }: { id: string; payload: SuggestionUpdatePayload }) =>
      updateAdminSuggestion(id, payload),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["admin", "suggestions"] });
    },
  });
}

// ── Price Preview (unchanged) ─────────────────────────────────────────────

export function useCalculatePrice() {
  return useMutation({
    mutationFn: (payload: PricePreviewPayload) => calculatePricePreview(payload),
  });
}

// ── Dashboard Summary ─────────────────────────────────────────────────────

export function useDashboardSummary() {
  return useQuery({
    queryKey: ["admin", "dashboard-summary"],
    queryFn: getDashboardSummary,
    staleTime: 30_000,
  });
}

// ── Demand Entries ────────────────────────────────────────────────────────

export function useCampaignDemandEntries(campaignId: string) {
  return useQuery({
    queryKey: ["admin", "demand-entries", campaignId],
    queryFn: () => getCampaignDemandEntries(campaignId),
    enabled: !!campaignId,
  });
}

export function useDeleteDemandEntry(campaignId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ entryId, reason }: { entryId: string; reason?: string }) =>
      deleteDemandEntry(entryId, reason),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["admin", "demand-entries", campaignId] });
      qc.invalidateQueries({ queryKey: ["admin", "campaigns"] });
    },
  });
}

export function useUploadProductImage() {
  return useMutation({
    mutationFn: (file: File) => uploadProductImage(file),
  });
}

// ── Demand Users ──────────────────────────────────────────────────────────────

export function useDemandUsers(sort = "quantity_desc") {
  return useQuery({
    queryKey: ["admin", "demand-users", sort],
    queryFn: () => getDemandUsers(sort),
    staleTime: 30_000,
  });
}

// ── Fraud Watch ───────────────────────────────────────────────────────────────

export function useFraudWatch() {
  return useQuery({
    queryKey: ["admin", "fraud-watch"],
    queryFn: getFraudWatch,
    staleTime: 30_000,
  });
}

// ── Action Items ──────────────────────────────────────────────────────────────

export function useActionItems() {
  return useQuery({
    queryKey: ["admin", "action-items"],
    queryFn: getActionItems,
    staleTime: 60_000,
  });
}
