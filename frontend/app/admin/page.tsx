"use client";

import Link from "next/link";
import { useDashboardSummary, useAdminSuggestions, useActionItems, useFraudWatch } from "@/features/admin/hooks";
import {
  Package, Tags, ClipboardList, ArrowRight,
  Users, ShieldAlert, AlertTriangle, TrendingUp, Activity,
  Clock, CreditCard,
} from "lucide-react";
import { formatCurrency } from "@/lib/utils/formatCurrency";

// ── StatCard ─────────────────────────────────────────────────────────────────

function StatCard({
  label,
  value,
  sub,
  subHref,
  href,
}: {
  label: string;
  value: number | string;
  sub?: string;
  subHref?: string;
  href?: string;
}) {
  const inner = (
    <div className={`bg-white rounded-xl border border-gray-200 p-5 ${href ? "hover:border-blue-400 hover:shadow-md transition-all cursor-pointer group" : ""}`}>
      <p className="text-xs font-medium text-gray-500 uppercase tracking-wide">{label}</p>
      <p className="mt-1 text-3xl font-bold text-gray-900">{value}</p>
      {sub && !subHref && <p className="mt-1 text-xs text-gray-400">{sub}</p>}
      {sub && subHref && (
        <Link
          href={subHref}
          onClick={(e) => e.stopPropagation()}
          className="mt-1 text-xs text-blue-500 hover:text-blue-700 hover:underline font-medium transition-colors block"
        >
          {sub}
        </Link>
      )}
    </div>
  );
  if (href) return <Link href={href}>{inner}</Link>;
  return inner;
}

// ── Section title ─────────────────────────────────────────────────────────────

function SectionTitle({ children }: { children: React.ReactNode }) {
  return (
    <h2 className="text-xs font-bold text-gray-500 uppercase tracking-widest mb-3 mt-8">
      {children}
    </h2>
  );
}

// ── Dashboard ─────────────────────────────────────────────────────────────────

export default function AdminDashboard() {
  const { data: summary, isLoading } = useDashboardSummary();
  const { data: pendingSuggestions } = useAdminSuggestions("pending");
  const { data: actionItems } = useActionItems();
  const { data: fraudWatch } = useFraudWatch();

  const pending = pendingSuggestions?.length ?? summary?.suggestions_pending ?? 0;
  const fraudCount = fraudWatch?.total ?? 0;

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
              sub="Ödeme aşamasına geç →"
              subHref="/admin/products?status=moq_reached"
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

          {/* Row 3: Demand + Revenue + Fraud */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 mb-10">
            <StatCard
              label="Toplam Talep"
              value={summary?.demand_total ?? 0}
              href="/admin/demand-users"
              sub={`${summary?.demand_unique_users ?? 0} benzersiz kullanıcı →`}
              subHref="/admin/demand-users"
            />
            <StatCard
              label="Son 30 Gün Talep"
              value={summary?.demand_last_30d ?? 0}
              href="/admin/demand-users"
            />
            <StatCard
              label="Tahsil Edilen"
              value={summary?.revenue_total_try ? formatCurrency(summary.revenue_total_try) : "₺0"}
            />
            <StatCard
              label="Fraud Watch"
              value={fraudCount}
              href="/admin/fraud-watch"
              sub={fraudCount > 0 ? `${fraudCount} şüpheli kayıt →` : "Temiz"}
              subHref={fraudCount > 0 ? "/admin/fraud-watch" : undefined}
            />
          </div>
        </>
      )}

      {/* ── Operasyon Blokları ─────────────────────────────────────────── */}

      {actionItems && (
        <>
          {/* Aksiyon Bekleyen Kampanyalar */}
          {(actionItems.moq_stalled.length > 0 || actionItems.payment_collecting.length > 0) && (
            <>
              <SectionTitle>Aksiyon Bekleyen Kampanyalar</SectionTitle>
              <div className="grid sm:grid-cols-2 gap-4 mb-2">
                {/* MOQ dolmuş ama ödeme sürecine geçmemiş */}
                {actionItems.moq_stalled.length > 0 && (
                  <div className="bg-amber-50 border border-amber-200 rounded-xl p-4">
                    <div className="flex items-center gap-2 mb-3">
                      <AlertTriangle className="h-4 w-4 text-amber-600" />
                      <span className="text-sm font-semibold text-amber-800">
                        MOQ Dolmuş — Ödeme Bekliyor ({actionItems.moq_stalled.length})
                      </span>
                    </div>
                    <ul className="space-y-2">
                      {actionItems.moq_stalled.slice(0, 5).map((item) => (
                        <li key={item.campaign_id} className="flex items-center justify-between">
                          <Link
                            href={`/admin/products?status=moq_reached`}
                            className="text-sm text-gray-700 hover:text-blue-600 truncate max-w-[180px]"
                          >
                            {item.title || item.campaign_id.slice(0, 8)}
                          </Link>
                          <span className="text-xs text-gray-400 shrink-0 ml-2">MOQ: {item.moq}</span>
                        </li>
                      ))}
                    </ul>
                    <Link
                      href="/admin/products?status=moq_reached"
                      className="mt-3 text-xs text-amber-700 hover:text-amber-900 font-medium flex items-center gap-1"
                    >
                      Tümünü gör <ArrowRight className="h-3 w-3" />
                    </Link>
                  </div>
                )}

                {/* Ödeme toplanıyor */}
                {actionItems.payment_collecting.length > 0 && (
                  <div className="bg-blue-50 border border-blue-200 rounded-xl p-4">
                    <div className="flex items-center gap-2 mb-3">
                      <CreditCard className="h-4 w-4 text-blue-600" />
                      <span className="text-sm font-semibold text-blue-800">
                        Ödeme Toplanıyor ({actionItems.payment_collecting.length})
                      </span>
                    </div>
                    <ul className="space-y-2">
                      {actionItems.payment_collecting.slice(0, 5).map((item) => (
                        <li key={item.campaign_id} className="flex items-center justify-between">
                          <Link
                            href={`/admin/products?status=payment_collecting`}
                            className="text-sm text-gray-700 hover:text-blue-600 truncate max-w-[180px]"
                          >
                            {item.title || item.campaign_id.slice(0, 8)}
                          </Link>
                          {item.payment_deadline && (
                            <span className="text-xs text-gray-400 shrink-0 ml-2">
                              {new Date(item.payment_deadline).toLocaleDateString("tr-TR")}
                            </span>
                          )}
                        </li>
                      ))}
                    </ul>
                    <Link
                      href="/admin/products?status=payment_collecting"
                      className="mt-3 text-xs text-blue-700 hover:text-blue-900 font-medium flex items-center gap-1"
                    >
                      Tümünü gör <ArrowRight className="h-3 w-3" />
                    </Link>
                  </div>
                )}
              </div>
            </>
          )}

          {/* MOQ'ya en yakın kampanyalar */}
          {actionItems.near_moq_active.length > 0 && (
            <>
              <SectionTitle>MOQ&apos;ya En Yakın Aktif Kampanyalar</SectionTitle>
              <div className="bg-white border border-gray-200 rounded-xl p-4 mb-2">
                <ul className="space-y-2">
                  {actionItems.near_moq_active.slice(0, 6).map((item) => (
                    <li key={item.campaign_id} className="flex items-center gap-3">
                      <Link
                        href={`/admin/products?status=active`}
                        className="text-sm text-gray-700 hover:text-blue-600 w-40 truncate"
                      >
                        {item.title || item.campaign_id.slice(0, 8)}
                      </Link>
                      <div className="flex-1 bg-gray-100 rounded-full h-2">
                        <div
                          className="bg-green-500 h-2 rounded-full transition-all"
                          style={{ width: `${Math.min(item.fill_pct, 100)}%` }}
                        />
                      </div>
                      <span className="text-xs font-semibold text-gray-600 w-16 text-right">
                        %{item.fill_pct} ({item.current_qty}/{item.moq})
                      </span>
                    </li>
                  ))}
                </ul>
              </div>
            </>
          )}

          {/* Trend / Hareket */}
          {(actionItems.trending_24h.length > 0 || actionItems.top_demand_30d.length > 0) && (
            <>
              <SectionTitle>Trend / Hareket</SectionTitle>
              <div className="grid sm:grid-cols-2 gap-4 mb-2">
                {actionItems.trending_24h.length > 0 && (
                  <div className="bg-white border border-gray-200 rounded-xl p-4">
                    <div className="flex items-center gap-2 mb-3">
                      <Activity className="h-4 w-4 text-green-600" />
                      <span className="text-sm font-semibold text-gray-700">Son 24 Saat</span>
                    </div>
                    <ul className="space-y-1.5">
                      {actionItems.trending_24h.slice(0, 5).map((item) => (
                        <li key={item.campaign_id} className="flex items-center justify-between">
                          <span className="text-sm text-gray-700 truncate max-w-[180px]">
                            {item.title || item.campaign_id.slice(0, 8)}
                          </span>
                          <span className="text-xs font-medium text-green-600 shrink-0 ml-2">
                            +{item.qty_sum} adet
                          </span>
                        </li>
                      ))}
                    </ul>
                  </div>
                )}

                {actionItems.top_demand_30d.length > 0 && (
                  <div className="bg-white border border-gray-200 rounded-xl p-4">
                    <div className="flex items-center gap-2 mb-3">
                      <TrendingUp className="h-4 w-4 text-blue-600" />
                      <span className="text-sm font-semibold text-gray-700">Son 30 Gün</span>
                    </div>
                    <ul className="space-y-1.5">
                      {actionItems.top_demand_30d.slice(0, 5).map((item) => (
                        <li key={item.campaign_id} className="flex items-center justify-between">
                          <span className="text-sm text-gray-700 truncate max-w-[180px]">
                            {item.title || item.campaign_id.slice(0, 8)}
                          </span>
                          <span className="text-xs font-medium text-blue-600 shrink-0 ml-2">
                            {item.qty_sum} adet
                          </span>
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>
            </>
          )}

          {/* Son Moderasyon */}
          {actionItems.recent_moderated.length > 0 && (
            <>
              <SectionTitle>Son Moderasyon Aktiviteleri</SectionTitle>
              <div className="bg-white border border-gray-200 rounded-xl p-4 mb-2">
                <ul className="divide-y divide-gray-100">
                  {actionItems.recent_moderated.slice(0, 5).map((entry) => (
                    <li key={entry.entry_id} className="py-2 flex items-start justify-between gap-3">
                      <div className="min-w-0">
                        <p className="text-sm text-gray-800 truncate">{entry.user_email}</p>
                        <p className="text-xs text-gray-400 truncate">{entry.campaign_title}</p>
                        {entry.removal_reason && (
                          <p className="text-xs text-red-500 mt-0.5">{entry.removal_reason}</p>
                        )}
                      </div>
                      <div className="shrink-0 text-right">
                        <span className={`inline-block px-2 py-0.5 rounded text-xs font-medium ${
                          entry.status === "removed"
                            ? "bg-red-100 text-red-700"
                            : "bg-yellow-100 text-yellow-700"
                        }`}>
                          {entry.status === "removed" ? "Silindi" : "Flaglendi"}
                        </span>
                        {entry.removed_at && (
                          <p className="text-xs text-gray-400 mt-0.5">
                            {new Date(entry.removed_at).toLocaleDateString("tr-TR")}
                          </p>
                        )}
                      </div>
                    </li>
                  ))}
                </ul>
              </div>
            </>
          )}
        </>
      )}

      {/* Quick access */}
      <SectionTitle>Hızlı Erişim</SectionTitle>
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

        <Link
          href="/admin/demand-users"
          className="bg-white border border-gray-200 rounded-xl p-5 hover:border-blue-300 hover:shadow-sm transition-all group"
        >
          <div className="flex items-start justify-between mb-3">
            <div className="p-2 bg-purple-50 rounded-lg">
              <Users className="h-5 w-5 text-purple-600" />
            </div>
            <ArrowRight className="h-4 w-4 text-gray-300 group-hover:text-blue-500 transition-colors" />
          </div>
          <p className="font-semibold text-gray-900 text-sm">Demand Users</p>
          <p className="text-xs text-gray-400 mt-0.5">Kullanıcı bazlı talep analizi</p>
          {summary?.demand_unique_users != null && (
            <p className="text-xs text-purple-600 font-medium mt-2">
              {summary.demand_unique_users} kullanıcı
            </p>
          )}
        </Link>

        <Link
          href="/admin/fraud-watch"
          className="bg-white border border-gray-200 rounded-xl p-5 hover:border-red-300 hover:shadow-sm transition-all group"
        >
          <div className="flex items-start justify-between mb-3">
            <div className="p-2 bg-red-50 rounded-lg">
              <ShieldAlert className="h-5 w-5 text-red-600" />
            </div>
            <ArrowRight className="h-4 w-4 text-gray-300 group-hover:text-red-500 transition-colors" />
          </div>
          <p className="font-semibold text-gray-900 text-sm">Fraud Watch</p>
          <p className="text-xs text-gray-400 mt-0.5">MOQ %10+ risk takibi</p>
          {fraudCount > 0 && (
            <p className="text-xs text-red-600 font-medium mt-2">
              {fraudCount} şüpheli kayıt
            </p>
          )}
        </Link>
      </div>
    </div>
  );
}
