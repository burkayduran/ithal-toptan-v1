"use client";

import Link from "next/link";
import { useDashboardSummary, useAdminSuggestions } from "@/features/admin/hooks";
import {
  Package, Tags, ClipboardList, ArrowRight,
  TrendingUp, Users, ShoppingCart, CreditCard, BarChart3, Truck,
} from "lucide-react";
import { formatCurrency } from "@/lib/utils/formatCurrency";

function StatCard({
  label,
  value,
  sub,
  href,
}: {
  label: string;
  value: number | string;
  sub?: string;
  href?: string;
}) {
  const inner = (
    <div className={`bg-white rounded-xl border border-gray-200 p-5 ${href ? "hover:border-blue-300 hover:shadow-sm transition-all cursor-pointer" : ""}`}>
      <p className="text-xs font-medium text-gray-500 uppercase tracking-wide">{label}</p>
      <p className="mt-1 text-3xl font-bold text-gray-900">{value}</p>
      {sub && <p className="mt-1 text-xs text-gray-400">{sub}</p>}
    </div>
  );
  if (href) return <Link href={href}>{inner}</Link>;
  return inner;
}

export default function AdminDashboard() {
  const { data: summary, isLoading } = useDashboardSummary();
  const { data: pendingSuggestions } = useAdminSuggestions("pending");

  const pending = pendingSuggestions?.length ?? summary?.suggestions_pending ?? 0;

  const SHORTCUTS = [
    {
      href: "/admin/products",
      icon: Package,
      label: "Ürünler",
      desc: "Listele, ekle, yayınla",
      count: summary?.products_total ?? null,
      countLabel: "ürün",
    },
    {
      href: "/admin/categories",
      icon: Tags,
      label: "Kategoriler",
      desc: "Kategori yönetimi",
      count: null,
      countLabel: null,
    },
    {
      href: "/admin/product-requests",
      icon: ClipboardList,
      label: "Ürün İstekleri",
      desc: "Kullanıcı önerileri",
      count: pending,
      countLabel: "bekleyen",
    },
  ];

  return (
    <div className="p-8 max-w-5xl">
      <h1 className="text-xl font-bold text-gray-900 mb-1">Dashboard</h1>
      <p className="text-sm text-gray-500 mb-8">Yönetim paneline hoş geldiniz.</p>

      {isLoading ? (
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 mb-4">
          {Array.from({ length: 4 }).map((_, i) => (
            <div key={i} className="bg-white rounded-xl border border-gray-200 p-5 animate-pulse">
              <div className="h-3 bg-gray-200 rounded w-2/3 mb-3" />
              <div className="h-8 bg-gray-200 rounded w-1/3" />
            </div>
          ))}
        </div>
      ) : (
        <>
          {/* Row 1: Core metrics */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 mb-4">
            <StatCard
              label="Toplam Ürün"
              value={summary?.products_total ?? 0}
              href="/admin/products"
            />
            <StatCard
              label="Aktif Kampanya"
              value={summary?.campaigns_active ?? 0}
              href="/admin/products?status=active"
            />
            <StatCard
              label="Taslak"
              value={summary?.campaigns_draft ?? 0}
              href="/admin/products?status=draft"
            />
            <StatCard
              label="Bekleyen İstek"
              value={pending}
              href="/admin/product-requests?status=pending"
            />
          </div>

          {/* Row 2: Funnel */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 mb-4">
            <StatCard
              label="MOQ Dolmuş"
              value={summary?.campaigns_moq_reached ?? 0}
              href="/admin/products?status=moq_reached"
              sub="Ödeme aşamasına geç"
            />
            <StatCard
              label="Ödeme Toplanıyor"
              value={summary?.campaigns_payment_collecting ?? 0}
              href="/admin/products?status=payment_collecting"
            />
            <StatCard
              label="Sipariş Verilmiş"
              value={summary?.campaigns_ordered ?? 0}
              href="/admin/products?status=ordered"
            />
            <StatCard
              label="Kargoda"
              value={summary?.campaigns_shipped ?? 0}
              href="/admin/products?status=shipped"
            />
          </div>

          {/* Row 3: Demand + Revenue */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 mb-10">
            <StatCard
              label="Toplam Talep"
              value={summary?.demand_total ?? 0}
              sub={`${summary?.demand_unique_users ?? 0} benzersiz kullanıcı`}
            />
            <StatCard
              label="Son 30 Gün Talep"
              value={summary?.demand_last_30d ?? 0}
            />
            <StatCard
              label="Tahsil Edilen"
              value={summary?.revenue_total_try ? formatCurrency(summary.revenue_total_try) : "₺0"}
            />
            <StatCard
              label="Bekleyen Tahsilat"
              value={summary?.pending_collection_try ? formatCurrency(summary.pending_collection_try) : "₺0"}
              sub="Davet edilmiş katılımcılar"
            />
          </div>
        </>
      )}

      {/* Quick access */}
      <h2 className="text-sm font-semibold text-gray-700 mb-3 uppercase tracking-wide">
        Hızlı Erişim
      </h2>
      <div className="grid sm:grid-cols-3 gap-4">
        {SHORTCUTS.map(({ href, icon: Icon, label, desc, count, countLabel }) => (
          <Link
            key={href}
            href={href}
            className="bg-white border border-gray-200 rounded-xl p-5 hover:border-blue-300 hover:shadow-sm transition-all group"
          >
            <div className="flex items-start justify-between mb-3">
              <div className="p-2 bg-blue-50 rounded-lg">
                <Icon className="h-5 w-5 text-blue-600" />
              </div>
              <ArrowRight className="h-4 w-4 text-gray-300 group-hover:text-blue-500 transition-colors" />
            </div>
            <p className="font-semibold text-gray-900 text-sm">{label}</p>
            <p className="text-xs text-gray-400 mt-0.5">{desc}</p>
            {count != null && (
              <p className="text-xs text-blue-600 font-medium mt-2">
                {count} {countLabel}
              </p>
            )}
          </Link>
        ))}
      </div>
    </div>
  );
}
