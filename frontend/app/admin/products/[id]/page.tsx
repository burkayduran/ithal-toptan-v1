"use client";

import { use } from "react";
import { useRouter } from "next/navigation";
import {
  useAdminProduct,
  useUpdateProduct,
  usePublishProduct,
  useAdminCategories,
} from "@/features/admin/hooks";
import type { AdminProduct, AdminCategory } from "@/features/admin/types";
import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { Loader2, ArrowLeft } from "lucide-react";
import Link from "next/link";

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="space-y-1">
      <Label className="text-xs font-medium text-gray-700">{label}</Label>
      {children}
    </div>
  );
}

// Inner form — only rendered after product loads, so state initialises from props
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

  const [form, setForm] = useState({
    title: product.title,
    description: product.description ?? "",
    category_id: product.category_id ?? "",
    images: (product.images ?? []).join("\n"),
    status: product.status,
  });

  function set(key: keyof typeof form) {
    return (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>) =>
      setForm((prev) => ({ ...prev, [key]: e.target.value }));
  }

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    update(
      {
        title: form.title.trim() || undefined,
        description: form.description.trim() || undefined,
        category_id: form.category_id || null,
        images: form.images
          .split("\n")
          .map((s) => s.trim())
          .filter(Boolean),
        status: form.status || undefined,
      },
      { onSuccess: () => router.push("/admin/products") }
    );
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-5">
      <div className="bg-white rounded-xl border border-gray-200 p-5 space-y-4">
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
      </div>

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
