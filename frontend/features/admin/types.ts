// Matches backend ProductResponse — includes draft status
export interface AdminProduct {
  id: string;
  title: string;
  description: string | null;
  category_id: string | null;
  images: string[];
  status: string;
  view_count: number;
  created_at: string;
  activated_at: string | null;
  moq: number | null;
  selling_price_try: number | null;
  lead_time_days: number | null;
  current_wishlist_count: number | null;
  moq_fill_percentage: number | null;
}

export interface ProductCreatePayload {
  title: string;
  description?: string;
  category_id?: string;
  images: string[];
  supplier_name?: string;
  supplier_country: string;
  alibaba_product_url?: string;
  unit_price_usd: number;
  moq: number;
  lead_time_days?: number;
  shipping_cost_usd?: number;
  customs_rate?: number;
  margin_rate: number;
}

export interface ProductUpdatePayload {
  title?: string;
  description?: string;
  category_id?: string | null;
  images?: string[];
  status?: string;
}

// Matches backend CategoryResponse
export interface AdminCategory {
  id: string;
  name: string;
  slug: string;
  parent_id: string | null;
  gumruk_rate: number | null;
  is_restricted: boolean;
  icon: string | null;
  sort_order: number;
}

export interface CategoryCreatePayload {
  name: string;
  slug: string;
  parent_id?: string;
  gumruk_rate?: number;
  is_restricted?: boolean;
  icon?: string;
  sort_order?: number;
}

export interface CategoryUpdatePayload {
  name?: string;
  slug?: string;
  parent_id?: string | null;
  gumruk_rate?: number | null;
  is_restricted?: boolean;
  icon?: string | null;
  sort_order?: number;
}

// Matches backend ProductRequestResponse
export interface AdminProductRequest {
  id: string;
  title: string;
  description: string | null;
  category_id: string | null;
  reference_url: string | null;
  expected_price_try: number | null;
  status: string;
  created_by: string | null;
  admin_notes: string | null;
  created_at: string;
}

export interface ProductRequestUpdatePayload {
  status?: string;
  admin_notes?: string;
}

// PriceBreakdown fields are Decimal → come as numeric strings in JSON
export interface PriceBreakdown {
  unit_price_usd: string;
  unit_price_try: string;
  shipping_per_unit_try: string;
  customs_try: string;
  kdv_base_try: string;
  kdv_try: string;
  total_cost_try: string;
  margin_try: string;
  selling_price_try: string;
  usd_rate: string;
}

export interface PricePreviewPayload {
  unit_price_usd: number;
  moq: number;
  shipping_cost_usd?: number;
  customs_rate?: number;
  margin_rate?: number;
}
