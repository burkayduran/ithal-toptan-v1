"use client";

import { use } from "react";
import { useRouter } from "next/navigation";
import {
  useAdminCampaign,
  useUpdateCampaign,
  usePublishCampaign,
  useAdminCategories,
  useCalculatePrice,
} from "@/features/admin/hooks";
import type { AdminCampaign, AdminCategory } from "@/features/admin/types";
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

const ALLOWED_TRANSITIONS: Record<string, string[]> = {
  draft: ["active", "cancelled"],
  active: ["moq_reached", "cancelled", "failed"],
  moq_reached: ["payment_collecting", "cancelled", "failed"],
  payment_collecting: ["ordered", "cancelled", "failed"],
  ordered: ["shipped", "cancelled"],
  shipped: ["delivered"],
  delivered: [],
  cancelled: [],
  failed: [],
};

const STATUS_LABELS: Record<string, string> = {
  draft: "Taslak",
  active: "Aktif",
  moq_reached: "MOQ Doldu",
  payment_collecting: "Ödeme Toplanıyor",
  ordered: "Sipariş Verildi",
  shipped: "Kargoda",
  delivered: "Teslim Edildi",
  cancelled: "İptal",
  failed: "Başarısız",
};

function StatusSelect({
  currentStatus,
  value,
  onChange,
}: {
  currentStatus: string;
  value: string;
  onChange: (e: React.ChangeEvent<HTMLSelectElement>) => void;
}) {
  const allowed = ALLOWED_TRANSITIONS[currentStatus] ?? [];
  // Show current + allowed targets
  const options = [currentStatus, ...allowed.filter((s) => s !== currentStatus)];

  return (
    <select
      value={value}
      onChange={onChange}
      className="w-full text-sm border border-gray-200 rounded-lg px-3 py-2 bg-white focus:outline-none"
    >
      {options.map((s) => (
        <option key={s} value={s}>
          {STATUS_LABELS[s] ?? s}
        </option>
      ))}
    </select>
  );
}

// Inner form — only rendered after campaign loads, so state initialises from props directly
function EditForm({
  campaign,
  categories,
}: {
  campaign: AdminCampaign;
  categories: AdminCategory[];
}) {
  const router = useRouter();
  const { mutate: update, isPending: isSaving, error } = useUpdateCampaign(campaign.id);
  const { mutate: publish, isPending: isPublishing } = usePublishCampaign();
  const { mutate: calcPrice, data: pricePreview, isPending: isCalcPending } = useCalculatePrice();

  const [form, setForm] = useState({
    // Campaign fields
    title: campaign.title,
    description: campaign.description ?? "",
    category_id: campaign.category_id ?? "",
    images: (campaign.images ?? []).join("\n"),
    status: campaign.status,
    // Supplier fields — read from _snapshot fields
    supplier_name: campaign.supplier_name_snapshot ?? "",
    supplier_country: campaign.supplier_country_snapshot ?? "CN",
    alibaba_product_url: campaign.alibaba_product_url_snapshot ?? "",
    lead_time_days: campaign.lead_time_days?.toString() ?? "",
    // Pricing fields — read from _snapshot fields, convert to display percentages
    unit_price_usd: campaign.unit_price_usd_snapshot?.toString() ?? "",
    moq: campaign.moq?.toString() ?? "",
    shipping_cost_usd: campaign.shipping_cost_usd_snapshot?.toString() ?? "",
    customs_rate: campaign.customs_rate_snapshot != null
      ? (campaign.customs_rate_snapshot * 100).toFixed(0) : "35",
    margin_rate: campaign.margin_rate_snapshot != null
      ? (campaign.margin_rate_snapshot * 100).toFixed(0) : "30",
  });

  const isLocked = ["moq_reached", "payment_collecting", "ordered"].includes(campaign.status);

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

    // B4: Status change confirmations
    if (form.status !== campaign.status) {
      if (form.status === "cancelled") {
        const confirmed = window.confirm(
          "Bu kampanyayı iptal etmek istediğinize emin misiniz? Bu işlem geri alınamaz."
        );
        if (!confirmed) return;
      }
      const STATUS_ORDER = ["draft", "active", "moq_reached", "payment_collecting", "ordered", "delivered"];
      const oldIdx = STATUS_ORDER.indexOf(campaign.status);
      const newIdx = STATUS_ORDER.indexOf(form.status);
      if (
        oldIdx >= STATUS_ORDER.indexOf("ordered") &&
        newIdx >= 0 &&
        newIdx < oldIdx
      ) {
        const confirmed = window.confirm(
          "Bu durumu geriye almak istediğinize emin misiniz?"
        );
        if (!confirmed) return;
      }
    }

    const payload: Record<string, unknown> = {
      title: form.title.trim() || undefined,
      description: form.description.trim() || undefined,
      category_id: form.category_id || null,
      images: form.images.split("\n").map((s) => s.trim()).filter(Boolean),
      status: form.status || undefined,
    };

    // B3: Supplier fields — use !== "" to allow zero values
    if (form.supplier_name.trim() !== "") payload.supplier_name = form.supplier_name.trim();
    if (form.supplier_country.trim() !== "") payload.supplier_country = form.supplier_country.trim();
    if (form.alibaba_product_url.trim() !== "") payload.alibaba_product_url = form.alibaba_product_url.trim();
    const ltd = parseInt(form.lead_time_days, 10);
    if (form.lead_time_days !== "" && !isNaN(ltd)) payload.lead_time_days = ltd;

    // B3: Pricing fields — use !== "" and NaN checks
    const usd = parseFloat(form.unit_price_usd);
    if (form.unit_price_usd !== "" && !isNaN(usd)) payload.unit_price_usd = usd;
    const moqVal = parseInt(form.moq, 10);
    if (form.moq !== "" && !isNaN(moqVal)) payload.moq = moqVal;
    const ship = parseFloat(form.shipping_cost_usd);
    if (form.shipping_cost_usd !== "" && !isNaN(ship)) payload.shipping_cost_usd = ship;
    const customs = parseFloat(form.customs_rate);
    if (form.customs_rate !== "" && !isNaN(customs)) payload.customs_rate = customs / 100;
    const margin = parseFloat(form.margin_rate);
    if (form.margin_rate !== "" && !isNaN(margin)) payload.margin_rate = margin / 100;

    update(payload as Parameters<typeof update>[0], {
      onSuccess: () => router.push("/admin/products"),
    });
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-5">
      {/* Basic campaign info */}
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
          <StatusSelect currentStatus={campaign.status} value={form.status} onChange={set("status")} />
        </Field>
      </Section>

      {/* Supplier info */}
      <Section title="Tedarikçi Bilgileri">
        {isLocked && (
          <div className="bg-amber-50 border border-amber-200 rounded-lg px-4 py-3 text-sm text-amber-800">
            Bu kampanyada ödeme süreci başlamıştır. Fiyat ve tedarikçi bilgileri değiştirilemez.
          </div>
        )}
        <div className="grid grid-cols-2 gap-3">
          <Field label="Tedarikçi Adı">
            <Input value={form.supplier_name} onChange={set("supplier_name")} placeholder="Alibaba Supplier Co." disabled={isLocked} />
          </Field>
          <Field label="Tedarikçi Ülke">
            <Input value={form.supplier_country} onChange={set("supplier_country")} placeholder="CN" disabled={isLocked} />
          </Field>
        </div>
        <Field label="Alibaba Ürün URL">
          <Input value={form.alibaba_product_url} onChange={set("alibaba_product_url")} placeholder="https://alibaba.com/..." disabled={isLocked} />
        </Field>
        <Field label="Teslimat Süresi (gün)">
          <Input type="number" value={form.lead_time_days} onChange={set("lead_time_days")} placeholder="14" min={1} disabled={isLocked} />
        </Field>
      </Section>

      {/* Pricing */}
      <Section title="Fiyatlandırma">
        {isLocked && (
          <div className="bg-amber-50 border border-amber-200 rounded-lg px-4 py-3 text-sm text-amber-800">
            Bu kampanyada ödeme süreci başlamıştır. Fiyat ve tedarikçi bilgileri değiştirilemez.
          </div>
        )}
        <div className="grid grid-cols-2 gap-3">
          <Field label="Birim Fiyat (USD)">
            <Input type="number" step="0.01" value={form.unit_price_usd} onChange={setPricing("unit_price_usd")} placeholder="10.00" min={0.01} disabled={isLocked} />
          </Field>
          <Field label="MOQ (minimum sipariş)">
            <Input type="number" value={form.moq} onChange={setPricing("moq")} placeholder="100" min={1} disabled={isLocked} />
          </Field>
          <Field label="Kargo (USD, toplam)">
            <Input type="number" step="0.01" value={form.shipping_cost_usd} onChange={setPricing("shipping_cost_usd")} placeholder="0" min={0} disabled={isLocked} />
          </Field>
          <Field label="Gümrük Oranı (%)">
            <Input type="number" value={form.customs_rate} onChange={setPricing("customs_rate")} placeholder="35" min={0} disabled={isLocked} />
          </Field>
          <Field label="Kâr Marjı (%)">
            <Input type="number" value={form.margin_rate} onChange={setPricing("margin_rate")} placeholder="30" min={0} disabled={isLocked} />
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
        {campaign.status === "draft" && (
          <Button
            type="button"
            variant="outline"
            disabled={isPublishing}
            onClick={() =>
              publish(campaign.id, { onSuccess: () => router.push("/admin/products") })
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
  const { data: campaign, isLoading, isError } = useAdminCampaign(id);
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
          {campaign?.title ?? "Ürün Düzenle"}
        </h1>
        {campaign && (
          <Badge variant={campaign.status === "active" ? "default" : "secondary"}>
            {campaign.status}
          </Badge>
        )}
      </div>

      {isLoading ? (
        <div className="flex items-center gap-2 text-sm text-gray-500">
          <Loader2 className="h-4 w-4 animate-spin" /> Yükleniyor...
        </div>
      ) : isError || !campaign ? (
        <div>
          <p className="text-sm text-red-500">Ürün bulunamadı.</p>
          <Link href="/admin/products">
            <Button variant="outline" size="sm" className="mt-3">
              Geri Dön
            </Button>
          </Link>
        </div>
      ) : (
        <EditForm campaign={campaign} categories={categories ?? []} />
      )}
    </div>
  );
}
