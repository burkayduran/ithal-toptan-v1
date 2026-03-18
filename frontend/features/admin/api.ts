import { api } from "@/lib/api/client";
import type {
  AdminProduct,
  AdminCategory,
  AdminProductRequest,
  PriceBreakdown,
  ProductCreatePayload,
  ProductUpdatePayload,
  CategoryCreatePayload,
  CategoryUpdatePayload,
  ProductRequestUpdatePayload,
  PricePreviewPayload,
} from "./types";

const ADMIN = "/api/admin";

// ── Products ──────────────────────────────────────────────────────────────

export function getAdminProducts(): Promise<AdminProduct[]> {
  return api.get(`${ADMIN}/products`);
}

export function getAdminProduct(id: string): Promise<AdminProduct> {
  return api.get(`${ADMIN}/products/${id}`);
}

export function createAdminProduct(payload: ProductCreatePayload): Promise<AdminProduct> {
  return api.post(`${ADMIN}/products`, payload);
}

export function updateAdminProduct(
  id: string,
  payload: ProductUpdatePayload
): Promise<AdminProduct> {
  return api.patch(`${ADMIN}/products/${id}`, payload);
}

export function publishAdminProduct(id: string): Promise<{ message: string; id: string }> {
  return api.post(`${ADMIN}/products/${id}/publish`);
}

export function bulkPublishProducts(
  product_ids: string[]
): Promise<{ published: string[]; failed: { id: string; reason: string }[] }> {
  return api.post(`${ADMIN}/products/bulk-publish`, product_ids);
}

export function bulkCancelProducts(
  product_ids: string[]
): Promise<{ cancelled: string[]; failed: { id: string; reason: string }[] }> {
  return api.post(`${ADMIN}/products/bulk-cancel`, product_ids);
}

// ── Categories ────────────────────────────────────────────────────────────

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

// ── Product Requests ──────────────────────────────────────────────────────

export function getAdminProductRequests(
  status = "pending"
): Promise<AdminProductRequest[]> {
  return api.get(`${ADMIN}/product-requests?status=${encodeURIComponent(status)}`);
}

export function updateAdminProductRequest(
  id: string,
  payload: ProductRequestUpdatePayload
): Promise<AdminProductRequest> {
  return api.patch(`${ADMIN}/product-requests/${id}`, payload);
}

// ── Price Preview ─────────────────────────────────────────────────────────

/** Calculate selling price preview. */
export function calculatePricePreview(payload: PricePreviewPayload): Promise<PriceBreakdown> {
  return api.post(`${ADMIN}/calculate-price`, {
    unit_price_usd: payload.unit_price_usd,
    moq: payload.moq,
    shipping_cost_usd: payload.shipping_cost_usd ?? 0,
    customs_rate: payload.customs_rate ?? 0.35,
    margin_rate: payload.margin_rate ?? 0.30,
  });
}
