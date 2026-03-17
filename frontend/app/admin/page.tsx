"use client";

import Link from "next/link";
import { useAdminProducts } from "@/features/admin/hooks";
import { useAdminProductRequests } from "@/features/admin/hooks";
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
  const { data: products } = useAdminProducts();
  const { data: pendingRequests } = useAdminProductRequests("pending");

  const total = products?.length ?? 0;
  const draft = products?.filter((p) => p.status === "draft").length ?? 0;
  const active = products?.filter((p) => p.status === "active").length ?? 0;
  const pending = pendingRequests?.length ?? 0;

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

      {/* Stats */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 mb-10">
        <StatCard label="Toplam Ürün" value={total} />
        <StatCard label="Yayında" value={active} />
        <StatCard label="Taslak" value={draft} />
        <StatCard label="Bekleyen İstek" value={pending} />
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
