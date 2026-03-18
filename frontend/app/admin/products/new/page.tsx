"use client";

import { useState, useEffect } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { useCreateProduct, useCalculatePrice, useAdminCategories } from "@/features/admin/hooks";
import type { PriceBreakdown } from "@/features/admin/types";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Loader2, ArrowLeft } from "lucide-react";
import Link from "next/link";

function Field({
  label,
  children,
  hint,
}: {
  label: string;
  children: React.ReactNode;
  hint?: string;
}) {
  return (
    <div className="space-y-1">
      <Label className="text-xs font-medium text-gray-700">{label}</Label>
      {children}
      {hint && <p className="text-xs text-gray-400">{hint}</p>}
    </div>
  );
}

function PriceRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex justify-between text-sm py-1.5 border-b border-gray-100 last:border-0">
      <span className="text-gray-500">{label}</span>
      <span className="font-medium text-gray-900">₺{parseFloat(value).toFixed(2)}</span>
    </div>
  );
}

export default function NewProductPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { data: categories } = useAdminCategories();
  const { mutate: create, isPending, error } = useCreateProduct();
  const { mutate: calcPrice, data: priceData, isPending: isCalcing } = useCalculatePrice();

  // Pre-fill from product request query params (D3)
  const prefillTitle = searchParams.get("title") ?? "";
  const prefillDesc = searchParams.get("description") ?? "";

  const [form, setForm] = useState({
    title: prefillTitle,
    description: prefillDesc,
    category_id: "",
    images: "",
    supplier_name: "",
    supplier_country: "CN",
    alibaba_product_url: "",
    unit_price_usd: "",
    moq: "",
    lead_time_days: "",
    shipping_cost_usd: "0",
    customs_rate: "35",
    margin_rate: "30",
  });

  const price = priceData as PriceBreakdown | undefined;

  // Auto-calculate when pricing fields change
  useEffect(() => {
    const usd = parseFloat(form.unit_price_usd);
    const moq = parseInt(form.moq);
    if (!usd || !moq || usd <= 0 || moq <= 0) return;
    const timer = setTimeout(() => {
      calcPrice({
        unit_price_usd: usd,
        moq,
        shipping_cost_usd: parseFloat(form.shipping_cost_usd) || 0,
        customs_rate: (parseFloat(form.customs_rate) || 35) / 100,
        margin_rate: (parseFloat(form.margin_rate) || 30) / 100,
      });
    }, 600);
    return () => clearTimeout(timer);
  }, [form.unit_price_usd, form.moq, form.shipping_cost_usd, form.customs_rate, form.margin_rate, calcPrice]);

  function set(key: keyof typeof form) {
    return (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>) =>
      setForm((prev) => ({ ...prev, [key]: e.target.value }));
  }

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    const usd = parseFloat(form.unit_price_usd);
    const moq = parseInt(form.moq);
    if (!usd || !moq) return;

    create(
      {
        title: form.title.trim(),
        description: form.description.trim() || undefined,
        category_id: form.category_id || undefined,
        images: form.images
          .split("\n")
          .map((s) => s.trim())
          .filter(Boolean),
        supplier_name: form.supplier_name.trim() || undefined,
        supplier_country: form.supplier_country || "CN",
        alibaba_product_url: form.alibaba_product_url.trim() || undefined,
        unit_price_usd: usd,
        moq,
        lead_time_days: parseInt(form.lead_time_days) || undefined,
        shipping_cost_usd: parseFloat(form.shipping_cost_usd) || 0,
        customs_rate: (parseFloat(form.customs_rate) || 35) / 100,
        margin_rate: (parseFloat(form.margin_rate) || 30) / 100,
      },
      {
        onSuccess: (data) => {
          router.push(`/admin/products/${data.id}`);
        },
      }
    );
  }

  return (
    <div className="p-6 max-w-5xl">
      <div className="flex items-center gap-3 mb-6">
        <Link href="/admin/products">
          <Button variant="ghost" size="sm" className="gap-1.5">
            <ArrowLeft className="h-4 w-4" />
            Geri
          </Button>
        </Link>
        <h1 className="text-xl font-bold text-gray-900">Yeni Ürün</h1>
      </div>

      <form onSubmit={handleSubmit}>
        <div className="grid lg:grid-cols-3 gap-6">
          {/* Left: form fields */}
          <div className="lg:col-span-2 space-y-6">
            {/* Product info */}
            <section className="bg-white rounded-xl border border-gray-200 p-5 space-y-4">
              <h2 className="text-sm font-semibold text-gray-900">Ürün Bilgileri</h2>
              <Field label="Başlık *">
                <Input required value={form.title} onChange={set("title")} placeholder="Ürün adı" />
              </Field>
              <Field label="Açıklama">
                <textarea
                  value={form.description}
                  onChange={set("description")}
                  rows={3}
                  className="w-full text-sm border border-gray-200 rounded-lg px-3 py-2 focus:outline-none focus:ring-1 focus:ring-blue-500 resize-none"
                  placeholder="Ürün açıklaması..."
                />
              </Field>
              <Field label="Kategori">
                <select
                  value={form.category_id}
                  onChange={set("category_id")}
                  className="w-full text-sm border border-gray-200 rounded-lg px-3 py-2 bg-white focus:outline-none"
                >
                  <option value="">Kategori seç...</option>
                  {(categories ?? []).map((c) => (
                    <option key={c.id} value={c.id}>
                      {c.name}
                    </option>
                  ))}
                </select>
              </Field>
              <Field label="Görsel URL'leri" hint="Her satıra bir URL girin">
                <textarea
                  value={form.images}
                  onChange={set("images")}
                  rows={3}
                  className="w-full text-sm border border-gray-200 rounded-lg px-3 py-2 focus:outline-none focus:ring-1 focus:ring-blue-500 resize-none font-mono"
                  placeholder="https://example.com/img1.jpg&#10;https://example.com/img2.jpg"
                />
              </Field>
            </section>

            {/* Supplier info */}
            <section className="bg-white rounded-xl border border-gray-200 p-5 space-y-4">
              <h2 className="text-sm font-semibold text-gray-900">Tedarikçi & Fiyatlama</h2>
              <div className="grid sm:grid-cols-2 gap-4">
                <Field label="Tedarikçi Adı">
                  <Input value={form.supplier_name} onChange={set("supplier_name")} placeholder="Alibaba Supplier Co." />
                </Field>
                <Field label="Tedarikçi Ülkesi">
                  <Input value={form.supplier_country} onChange={set("supplier_country")} placeholder="CN" />
                </Field>
              </div>
              <Field label="Alibaba URL">
                <Input value={form.alibaba_product_url} onChange={set("alibaba_product_url")} placeholder="https://alibaba.com/..." />
              </Field>
              <div className="grid sm:grid-cols-2 gap-4">
                <Field label="Birim Fiyat (USD) *">
                  <Input
                    required
                    type="number"
                    step="0.01"
                    min="0.01"
                    value={form.unit_price_usd}
                    onChange={set("unit_price_usd")}
                    placeholder="12.50"
                  />
                </Field>
                <Field label="Minimum Sipariş Adedi (MOQ) *">
                  <Input
                    required
                    type="number"
                    min="1"
                    value={form.moq}
                    onChange={set("moq")}
                    placeholder="100"
                  />
                </Field>
                <Field label="Teslimat Süresi (gün)">
                  <Input type="number" min="1" value={form.lead_time_days} onChange={set("lead_time_days")} placeholder="30" />
                </Field>
                <Field label="Kargo Maliyeti (USD / adet)">
                  <Input type="number" step="0.01" min="0" value={form.shipping_cost_usd} onChange={set("shipping_cost_usd")} />
                </Field>
                <Field label="Gümrük Oranı (%)" hint="Örn: 35 → %35">
                  <Input type="number" step="0.1" min="0" max="200" value={form.customs_rate} onChange={set("customs_rate")} />
                </Field>
                <Field label="Kâr Marjı (%)" hint="Örn: 30 → %30">
                  <Input type="number" step="0.1" min="0" max="200" value={form.margin_rate} onChange={set("margin_rate")} />
                </Field>
              </div>
            </section>
          </div>

          {/* Right: price preview */}
          <div className="space-y-4">
            <section className="bg-white rounded-xl border border-gray-200 p-5 sticky top-4">
              <h2 className="text-sm font-semibold text-gray-900 mb-3">
                Fiyat Önizleme
                {isCalcing && <Loader2 className="inline h-3 w-3 animate-spin ml-2 text-gray-400" />}
              </h2>
              {price ? (
                <div>
                  <PriceRow label="USD Kuru" value={(parseFloat(price.usd_rate)).toFixed(4).replace(/₺/, "")} />
                  <PriceRow label="Birim Fiyat (TRY)" value={price.unit_price_try} />
                  <PriceRow label="Kargo / Adet" value={price.shipping_per_unit_try} />
                  <PriceRow label="Gümrük" value={price.customs_try} />
                  <PriceRow label="KDV" value={price.kdv_try} />
                  <PriceRow label="Maliyet" value={price.total_cost_try} />
                  <PriceRow label="Kâr" value={price.margin_try} />
                  <div className="mt-3 pt-3 border-t border-gray-200 flex justify-between">
                    <span className="font-semibold text-gray-900">Satış Fiyatı</span>
                    <span className="font-bold text-blue-600 text-lg">
                      ₺{parseFloat(price.selling_price_try).toFixed(2)}
                    </span>
                  </div>
                </div>
              ) : (
                <p className="text-xs text-gray-400">USD fiyat ve MOQ girin, otomatik hesaplanır.</p>
              )}
            </section>

            {/* Submit */}
            <div className="space-y-2">
              {error && (
                <p className="text-xs text-red-600 bg-red-50 rounded px-3 py-2">
                  {(error as Error).message}
                </p>
              )}
              <Button type="submit" className="w-full" disabled={isPending}>
                {isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : "Taslak Olarak Kaydet"}
              </Button>
              <p className="text-xs text-gray-400 text-center">
                Ürün taslak olarak kaydedilir. Listeden yayınlayabilirsiniz.
              </p>
            </div>
          </div>
        </div>
      </form>
    </div>
  );
}
