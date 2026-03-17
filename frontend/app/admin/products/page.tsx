"use client";

import { useState } from "react";
import Link from "next/link";
import { useAdminProducts, usePublishProduct } from "@/features/admin/hooks";
import { formatCurrency } from "@/lib/utils/formatCurrency";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { Plus, Search, Loader2 } from "lucide-react";

const STATUS_LABEL: Record<string, { label: string; variant: "default" | "secondary" | "destructive" | "outline" }> = {
  draft: { label: "Taslak", variant: "secondary" },
  active: { label: "Aktif", variant: "default" },
  moq_reached: { label: "MOQ Doldu", variant: "default" },
  payment_collecting: { label: "Ödeme", variant: "default" },
  ordered: { label: "Sipariş", variant: "outline" },
  delivered: { label: "Teslim", variant: "outline" },
  cancelled: { label: "İptal", variant: "destructive" },
};

export default function AdminProductsPage() {
  const { data: products, isLoading, isError, refetch } = useAdminProducts();
  const { mutate: publish, isPending: isPublishing, variables: publishingId } = usePublishProduct();
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState("all");

  const filtered = (products ?? []).filter((p) => {
    const matchesSearch = p.title.toLowerCase().includes(search.toLowerCase());
    const matchesStatus = statusFilter === "all" || p.status === statusFilter;
    return matchesSearch && matchesStatus;
  });

  return (
    <div className="p-6">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-xl font-bold text-gray-900">Ürünler</h1>
        <Link href="/admin/products/new">
          <Button size="sm" className="gap-1.5">
            <Plus className="h-4 w-4" />
            Yeni Ürün
          </Button>
        </Link>
      </div>

      {/* Filters */}
      <div className="flex flex-wrap gap-3 mb-5">
        <div className="relative w-64">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-gray-400 pointer-events-none" />
          <Input
            placeholder="Ürün ara..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="pl-8 h-8 text-sm"
          />
        </div>
        <select
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value)}
          className="text-sm border border-gray-200 rounded-lg px-3 py-1.5 bg-white text-gray-700 focus:outline-none"
        >
          <option value="all">Tüm Durumlar</option>
          <option value="draft">Taslak</option>
          <option value="active">Aktif</option>
          <option value="moq_reached">MOQ Doldu</option>
          <option value="payment_collecting">Ödeme</option>
          <option value="ordered">Sipariş</option>
          <option value="delivered">Teslim</option>
          <option value="cancelled">İptal</option>
        </select>
      </div>

      {isLoading ? (
        <div className="text-sm text-gray-400 py-10 text-center">Yükleniyor...</div>
      ) : isError ? (
        <div className="text-sm text-red-500 py-10 text-center">
          Hata oluştu.{" "}
          <button className="underline" onClick={() => refetch()}>
            Tekrar dene
          </button>
        </div>
      ) : filtered.length === 0 ? (
        <div className="text-sm text-gray-400 py-10 text-center">Ürün bulunamadı.</div>
      ) : (
        <div className="bg-white border border-gray-200 rounded-xl overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 border-b border-gray-200">
              <tr>
                <th className="text-left px-4 py-3 font-medium text-gray-600 text-xs">Başlık</th>
                <th className="text-left px-4 py-3 font-medium text-gray-600 text-xs hidden md:table-cell">Durum</th>
                <th className="text-right px-4 py-3 font-medium text-gray-600 text-xs hidden lg:table-cell">Fiyat</th>
                <th className="text-right px-4 py-3 font-medium text-gray-600 text-xs hidden lg:table-cell">MOQ</th>
                <th className="text-left px-4 py-3 font-medium text-gray-600 text-xs hidden xl:table-cell">Tarih</th>
                <th className="text-right px-4 py-3 font-medium text-gray-600 text-xs">İşlem</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {filtered.map((p) => {
                const meta = STATUS_LABEL[p.status] ?? { label: p.status, variant: "outline" as const };
                const isThisPublishing = isPublishing && publishingId === p.id;
                return (
                  <tr key={p.id} className="hover:bg-gray-50 transition-colors">
                    <td className="px-4 py-3">
                      <p className="font-medium text-gray-900 line-clamp-1">{p.title}</p>
                    </td>
                    <td className="px-4 py-3 hidden md:table-cell">
                      <Badge variant={meta.variant} className="text-xs">{meta.label}</Badge>
                    </td>
                    <td className="px-4 py-3 text-right text-gray-600 hidden lg:table-cell">
                      {p.selling_price_try != null ? formatCurrency(p.selling_price_try) : "—"}
                    </td>
                    <td className="px-4 py-3 text-right text-gray-600 hidden lg:table-cell">
                      {p.moq ?? "—"}
                    </td>
                    <td className="px-4 py-3 text-gray-400 text-xs hidden xl:table-cell">
                      {new Date(p.created_at).toLocaleDateString("tr-TR")}
                    </td>
                    <td className="px-4 py-3 text-right">
                      <div className="flex items-center justify-end gap-2">
                        {p.status === "draft" && (
                          <Button
                            size="sm"
                            variant="outline"
                            className="h-7 text-xs"
                            disabled={isThisPublishing}
                            onClick={() => publish(p.id)}
                          >
                            {isThisPublishing ? (
                              <Loader2 className="h-3 w-3 animate-spin" />
                            ) : (
                              "Yayınla"
                            )}
                          </Button>
                        )}
                        <Link href={`/admin/products/${p.id}`}>
                          <Button size="sm" variant="ghost" className="h-7 text-xs">
                            Düzenle
                          </Button>
                        </Link>
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
