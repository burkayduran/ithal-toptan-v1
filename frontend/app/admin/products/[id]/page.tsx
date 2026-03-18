"use client";

import { use } from "react";
import { useRouter } from "next/navigation";
import {
  useAdminProduct,
  useUpdateProduct,
  usePublishProduct,
  useAdminCategories,
  useCalculatePrice,
} from "@/features/admin/hooks";
import type { AdminProduct, AdminCategory } from "@/features/admin/types";
import { useState, useCallback, useRef } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { Loader2, ArrowLeft, RefreshCw } from "lucide-react";
import Link from "next/link";

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="space-y-1">
      <Label className="text-xs font-medium text-gray-700">{label}</Label>
      {children}
    </div>
  );
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="bg-white rounded-xl border border-gray-200 p-5 space-y-4">
      <h2 className="text-sm font-semibold text-gray-800">{title}</h2>
      {children}
    </div>
  );
}

// Inner form — only rendered after product loads, so state initialises from props directly
function EditForm({
  product,
  categories,
}: {
  product: AdminProduct;
  categories: AdminCategory[];
}) {
  const router = useRouter();
  const { mutate: update, isPending: isSaving, error } = useUpdateProduct(product.id);
  const { mutate: publish, isPending: isPublishing } = usePublishProduct();
  const { mutate: calcPrice, data: pricePreview, isPending: isCalcPending } = useCalculatePrice();

  const [form, setForm] = useState({
    // Product fields
    title: product.title,
    description: product.description ?? "",
    category_id: product.category_id ?? "",
    images: (product.images ?? []).join("\n"),
    status: product.status,
    // Supplier fields
    supplier_name: product.supplier_name ?? "",
    supplier_country: product.supplier_country ?? "CN",
    alibaba_product_url: product.alibaba_product_url ?? "",
    lead_time_days: product.lead_time_days?.toString() ?? "",
    // Pricing fields (as percentages for display)
    unit_price_usd: product.unit_price_usd?.toString() ?? "",
    moq: product.moq?.toString() ?? "",
    shipping_cost_usd: product.shipping_cost_usd?.toString() ?? "",
    customs_rate: product.customs_rate != null ? (product.customs_rate * 100).toFixed(0) : "35",
    margin_rate: product.margin_rate != null ? (product.margin_rate * 100).toFixed(0) : "30",
  });

  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  function set(key: keyof typeof form) {
    return (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>) => {
      setForm((prev) => ({ ...prev, [key]: e.target.value }));
    };
  }

  const triggerPriceCalc = useCallback(
    (f: typeof form) => {
      const usd = parseFloat(f.unit_price_usd);
      const moq = parseInt(f.moq, 10);
      if (!usd || !moq) return;
      const customs = parseFloat(f.customs_rate) / 100;
      const margin = parseFloat(f.margin_rate) / 100;
      const shipping = parseFloat(f.shipping_cost_usd) || 0;
      calcPrice({ unit_price_usd: usd, moq, shipping_cost_usd: shipping, customs_rate: customs, margin_rate: margin });
    },
    [calcPrice]
  );

  function setPricing(key: keyof typeof form) {
    return (e: React.ChangeEvent<HTMLInputElement>) => {
      const val = e.target.value;
      setForm((prev) => {
        const next = { ...prev, [key]: val };
        if (debounceRef.current) clearTimeout(debounceRef.current);
        debounceRef.current = setTimeout(() => triggerPriceCalc(next), 600);
        return next;
      });
    };
  }

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();

    const payload: Record<string, unknown> = {
      title: form.title.trim() || undefined,
      description: form.description.trim() || undefined,
      category_id: form.category_id || null,
      images: form.images.split("\n").map((s) => s.trim()).filter(Boolean),
      status: form.status || undefined,
    };

    // Supplier fields
    if (form.supplier_name.trim()) payload.supplier_name = form.supplier_name.trim();
    if (form.supplier_country.trim()) payload.supplier_country = form.supplier_country.trim();
    if (form.alibaba_product_url.trim()) payload.alibaba_product_url = form.alibaba_product_url.trim();
    if (form.lead_time_days) payload.lead_time_days = parseInt(form.lead_time_days, 10);

    // Pricing fields
    if (form.unit_price_usd) payload.unit_price_usd = parseFloat(form.unit_price_usd);
    if (form.moq) payload.moq = parseInt(form.moq, 10);
    if (form.shipping_cost_usd) payload.shipping_cost_usd = parseFloat(form.shipping_cost_usd);
    if (form.customs_rate) payload.customs_rate = parseFloat(form.customs_rate) / 100;
    if (form.margin_rate) payload.margin_rate = parseFloat(form.margin_rate) / 100;

    update(payload as Parameters<typeof update>[0], {
      onSuccess: () => router.push("/admin/products"),
    });
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-5">
      {/* Basic product info */}
      <Section title="Ürün Bilgileri">
        <Field label="Başlık">
          <Input required value={form.title} onChange={set("title")} />
        </Field>
        <Field label="Açıklama">
          <textarea
            value={form.description}
            onChange={set("description")}
            rows={4}
            className="w-full text-sm border border-gray-200 rounded-lg px-3 py-2 focus:outline-none focus:ring-1 focus:ring-blue-500 resize-none"
          />
        </Field>
        <Field label="Kategori">
          <select
            value={form.category_id}
            onChange={set("category_id")}
            className="w-full text-sm border border-gray-200 rounded-lg px-3 py-2 bg-white focus:outline-none"
          >
            <option value="">Kategori seç...</option>
            {categories.map((c) => (
              <option key={c.id} value={c.id}>
                {c.name}
              </option>
            ))}
          </select>
        </Field>
        <Field label="Görsel URL'leri (her satıra bir URL)">
          <textarea
            value={form.images}
            onChange={set("images")}
            rows={3}
            className="w-full text-sm border border-gray-200 rounded-lg px-3 py-2 focus:outline-none font-mono resize-none"
          />
        </Field>
        <Field label="Durum">
          <select
            value={form.status}
            onChange={set("status")}
            className="w-full text-sm border border-gray-200 rounded-lg px-3 py-2 bg-white focus:outline-none"
          >
            <option value="draft">Taslak</option>
            <option value="active">Aktif</option>
            <option value="moq_reached">MOQ Doldu</option>
            <option value="payment_collecting">Ödeme Toplanıyor</option>
            <option value="ordered">Sipariş Verildi</option>
            <option value="delivered">Teslim Edildi</option>
            <option value="cancelled">İptal</option>
          </select>
        </Field>
      </Section>

      {/* Supplier info */}
      <Section title="Tedarikçi Bilgileri">
        <div className="grid grid-cols-2 gap-3">
          <Field label="Tedarikçi Adı">
            <Input value={form.supplier_name} onChange={set("supplier_name")} placeholder="Alibaba Supplier Co." />
          </Field>
          <Field label="Tedarikçi Ülke">
            <Input value={form.supplier_country} onChange={set("supplier_country")} placeholder="CN" />
          </Field>
        </div>
        <Field label="Alibaba Ürün URL">
          <Input value={form.alibaba_product_url} onChange={set("alibaba_product_url")} placeholder="https://alibaba.com/..." />
        </Field>
        <Field label="Teslimat Süresi (gün)">
          <Input type="number" value={form.lead_time_days} onChange={set("lead_time_days")} placeholder="14" min={1} />
        </Field>
      </Section>

      {/* Pricing */}
      <Section title="Fiyatlandırma">
        <div className="grid grid-cols-2 gap-3">
          <Field label="Birim Fiyat (USD)">
            <Input type="number" step="0.01" value={form.unit_price_usd} onChange={setPricing("unit_price_usd")} placeholder="10.00" min={0.01} />
          </Field>
          <Field label="MOQ (minimum sipariş)">
            <Input type="number" value={form.moq} onChange={setPricing("moq")} placeholder="100" min={1} />
          </Field>
          <Field label="Kargo (USD, toplam)">
            <Input type="number" step="0.01" value={form.shipping_cost_usd} onChange={setPricing("shipping_cost_usd")} placeholder="0" min={0} />
          </Field>
          <Field label="Gümrük Oranı (%)">
            <Input type="number" value={form.customs_rate} onChange={setPricing("customs_rate")} placeholder="35" min={0} />
          </Field>
          <Field label="Kâr Marjı (%)">
            <Input type="number" value={form.margin_rate} onChange={setPricing("margin_rate")} placeholder="30" min={0} />
          </Field>
        </div>

        {/* Price preview */}
        {(pricePreview || isCalcPending) && (
          <div className="mt-2 rounded-lg bg-blue-50 border border-blue-100 p-3 text-xs">
            {isCalcPending ? (
              <div className="flex items-center gap-2 text-blue-600">
                <RefreshCw className="h-3 w-3 animate-spin" /> Hesaplanıyor...
              </div>
            ) : pricePreview ? (
              <div className="space-y-1 text-gray-700">
                <div className="flex justify-between">
                  <span>Kur (USD/TRY)</span>
                  <span className="font-mono">{parseFloat(pricePreview.usd_rate).toFixed(2)}</span>
                </div>
                <div className="flex justify-between">
                  <span>Birim TRY</span>
                  <span className="font-mono">{parseFloat(pricePreview.unit_price_try).toFixed(2)} ₺</span>
                </div>
                <div className="flex justify-between">
                  <span>Gümrük</span>
                  <span className="font-mono">{parseFloat(pricePreview.customs_try).toFixed(2)} ₺</span>
                </div>
                <div className="flex justify-between">
                  <span>KDV (%20)</span>
                  <span className="font-mono">{parseFloat(pricePreview.kdv_try).toFixed(2)} ₺</span>
                </div>
                <div className="flex justify-between font-semibold text-blue-700 border-t border-blue-200 pt-1 mt-1">
                  <span>Satış Fiyatı</span>
                  <span className="font-mono">{parseFloat(pricePreview.selling_price_try).toFixed(2)} ₺</span>
                </div>
              </div>
            ) : null}
          </div>
        )}
      </Section>

      {error && (
        <p className="text-xs text-red-600 bg-red-50 rounded px-3 py-2">
          {(error as Error).message}
        </p>
      )}

      <div className="flex gap-3">
        <Button type="submit" disabled={isSaving} className="flex-1">
          {isSaving ? <Loader2 className="h-4 w-4 animate-spin" /> : "Kaydet"}
        </Button>
        {product.status === "draft" && (
          <Button
            type="button"
            variant="outline"
            disabled={isPublishing}
            onClick={() =>
              publish(product.id, { onSuccess: () => router.push("/admin/products") })
            }
          >
            {isPublishing ? <Loader2 className="h-4 w-4 animate-spin" /> : "Yayınla"}
          </Button>
        )}
      </div>
    </form>
  );
}

export default function EditProductPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const { data: product, isLoading, isError } = useAdminProduct(id);
  const { data: categories } = useAdminCategories();

  return (
    <div className="p-6 max-w-2xl">
      <div className="flex items-center gap-3 mb-6">
        <Link href="/admin/products">
          <Button variant="ghost" size="sm" className="gap-1.5">
            <ArrowLeft className="h-4 w-4" />
            Geri
          </Button>
        </Link>
        <h1 className="text-xl font-bold text-gray-900 flex-1 line-clamp-1">
          {product?.title ?? "Ürün Düzenle"}
        </h1>
        {product && (
          <Badge variant={product.status === "active" ? "default" : "secondary"}>
            {product.status}
          </Badge>
        )}
      </div>

      {isLoading ? (
        <div className="flex items-center gap-2 text-sm text-gray-500">
          <Loader2 className="h-4 w-4 animate-spin" /> Yükleniyor...
        </div>
      ) : isError || !product ? (
        <div>
          <p className="text-sm text-red-500">Ürün bulunamadı.</p>
          <Link href="/admin/products">
            <Button variant="outline" size="sm" className="mt-3">
              Geri Dön
            </Button>
          </Link>
        </div>
      ) : (
        <EditForm product={product} categories={categories ?? []} />
      )}
    </div>
  );
}
