"use client";

import Link from "next/link";
import { useAdminCampaigns } from "@/features/admin/hooks";
import { useAdminSuggestions } from "@/features/admin/hooks";
import { Package, Tags, ClipboardList, ArrowRight } from "lucide-react";

function StatCard({
  label,
  value,
  sub,
}: {
  label: string;
  value: number | string;
  sub?: string;
}) {
  return (
    <div className="bg-white rounded-xl border border-gray-200 p-5">
      <p className="text-xs font-medium text-gray-500 uppercase tracking-wide">{label}</p>
      <p className="mt-1 text-3xl font-bold text-gray-900">{value}</p>
      {sub && <p className="mt-1 text-xs text-gray-400">{sub}</p>}
    </div>
  );
}

export default function AdminDashboard() {
  const { data: campaigns } = useAdminCampaigns();
  const { data: pendingSuggestions } = useAdminSuggestions("pending");

  const total = campaigns?.length ?? 0;
  const draft = campaigns?.filter((p) => p.status === "draft").length ?? 0;
  const active = campaigns?.filter((p) => p.status === "active").length ?? 0;
  const pending = pendingSuggestions?.length ?? 0;
  const moqReached = campaigns?.filter((p) => p.status === "moq_reached").length ?? 0;
  const paymentCollecting = campaigns?.filter((p) => p.status === "payment_collecting").length ?? 0;
  const ordered = campaigns?.filter((p) => p.status === "ordered").length ?? 0;

  const SHORTCUTS = [
    {
      href: "/admin/products",
      icon: Package,
      label: "Ürünler",
      desc: "Listele, ekle, yayınla",
      count: total,
      countLabel: "toplam ürün",
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
    <div className="p-8 max-w-4xl">
      <h1 className="text-xl font-bold text-gray-900 mb-1">Dashboard</h1>
      <p className="text-sm text-gray-500 mb-8">Yönetim paneline hoş geldiniz.</p>

      {/* Stats - Row 1 */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 mb-4">
        <StatCard label="Toplam Ürün" value={total} />
        <StatCard label="Yayında" value={active} />
        <StatCard label="Taslak" value={draft} />
        <StatCard label="Bekleyen İstek" value={pending} />
      </div>

      {/* Stats - Row 2: Funnel */}
      <div className="grid grid-cols-2 sm:grid-cols-3 gap-4 mb-10">
        <StatCard
          label="MOQ Dolmuş"
          value={moqReached}
          sub={active > 0 ? `Aktif → MOQ: %${active > 0 ? Math.round((moqReached / active) * 100) : 0}` : undefined}
        />
        <StatCard label="Ödeme Toplanıyor" value={paymentCollecting} />
        <StatCard label="Sipariş Verilmiş" value={ordered} />
      </div>

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
