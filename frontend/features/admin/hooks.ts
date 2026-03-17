import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  getAdminProducts,
  getAdminProduct,
  createAdminProduct,
  updateAdminProduct,
  publishAdminProduct,
  getAdminCategories,
  createAdminCategory,
  updateAdminCategory,
  deleteAdminCategory,
  getAdminProductRequests,
  updateAdminProductRequest,
  calculatePricePreview,
} from "./api";
import type {
  ProductCreatePayload,
  ProductUpdatePayload,
  CategoryCreatePayload,
  CategoryUpdatePayload,
  ProductRequestUpdatePayload,
  PricePreviewPayload,
} from "./types";

// ── Products ──────────────────────────────────────────────────────────────

export function useAdminProducts() {
  return useQuery({
    queryKey: ["admin", "products"],
    queryFn: getAdminProducts,
  });
}

export function useAdminProduct(id: string) {
  return useQuery({
    queryKey: ["admin", "products", id],
    queryFn: () => getAdminProduct(id),
    enabled: !!id,
  });
}

export function useCreateProduct() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (payload: ProductCreatePayload) => createAdminProduct(payload),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["admin", "products"] });
    },
  });
}

export function useUpdateProduct(id: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (payload: ProductUpdatePayload) => updateAdminProduct(id, payload),
    onSuccess: (data) => {
      qc.invalidateQueries({ queryKey: ["admin", "products"] });
      qc.setQueryData(["admin", "products", id], data);
      // Also invalidate public product cache
      qc.invalidateQueries({ queryKey: ["product", id] });
      qc.invalidateQueries({ queryKey: ["products"] });
    },
  });
}

export function usePublishProduct() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => publishAdminProduct(id),
    onSuccess: (_data, id) => {
      qc.invalidateQueries({ queryKey: ["admin", "products"] });
      qc.invalidateQueries({ queryKey: ["admin", "products", id] });
      qc.invalidateQueries({ queryKey: ["products"] });
    },
  });
}

// ── Categories ────────────────────────────────────────────────────────────

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

// ── Product Requests ──────────────────────────────────────────────────────

export function useAdminProductRequests(status = "pending") {
  return useQuery({
    queryKey: ["admin", "product-requests", status],
    queryFn: () => getAdminProductRequests(status),
  });
}

export function useUpdateProductRequest() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, payload }: { id: string; payload: ProductRequestUpdatePayload }) =>
      updateAdminProductRequest(id, payload),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["admin", "product-requests"] });
    },
  });
}

// ── Price Preview ─────────────────────────────────────────────────────────

export function useCalculatePrice() {
  return useMutation({
    mutationFn: (payload: PricePreviewPayload) => calculatePricePreview(payload),
  });
}
