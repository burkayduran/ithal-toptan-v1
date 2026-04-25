"use client";

import Link from "next/link";
import {
  useDashboardSummary,
  useAdminSuggestions,
  useFraudWatch,
} from "@/features/admin/hooks";
import type {
  AttentionItem,
  LifecycleStep,
  KpiValue,
  NearMoqActiveItem,
} from "@/features/admin/types";
import { formatCurrency } from "@/lib/utils/formatCurrency";
import {
  AlertTriangle, AlertCircle, Info, ArrowRight, TrendingUp,
  Package, ClipboardList, ShieldAlert, Users, CreditCard,
  BarChart2, ChevronRight, Plus, Eye,
} from "lucide-react";

// ── Helpers ───────────────────────────────────────────────────────────────────

function fmt(n: number | null | undefined, prefix = "") {
  if (n == null) return "—";
  return prefix + n.toLocaleString("tr-TR");
}

// ── Attention Banner ──────────────────────────────────────────────────────────

function AttentionBanner({ items }: { items: AttentionItem[] }) {
  if (!items.length) return null;

  const palette: Record<
    AttentionItem["severity"],
    { border: string; bg: string; icon: string; iconEl: React.ReactNode }
  > = {
    critical: {
      border: "border-red-300",
      bg: "bg-red-50",
      icon: "text-red-600",
      iconEl: <AlertCircle className="h-4 w-4" />,
    },
    warning: {
      border: "border-amber-300",
      bg: "bg-amber-50",
      icon: "text-amber-600",
      iconEl: <AlertTriangle className="h-4 w-4" />,
    },
    info: {
      border: "border-blue-200",
      bg: "bg-blue-50",
      icon: "text-blue-600",
      iconEl: <Info className="h-4 w-4" />,
    },
  };

  const sorted = [...items].sort((a, b) => {
    const order = { critical: 0, warning: 1, info: 2 };
    return order[a.severity] - order[b.severity];
  });

  return (
    <div className="mb-8 space-y-2">
      {sorted.map((item, i) => {
        const p = palette[item.severity];
        return (
          <div
            key={i}
            className={`flex items-start justify-between gap-4 rounded-xl border ${p.border} ${p.bg} px-4 py-3`}
          >
            <div className={`flex items-start gap-2.5 ${p.icon} flex-1 min-w-0`}>
              <span className="mt-0.5 flex-shrink-0">{p.iconEl}</span>
              <div className="min-w-0">
                <p className="text-sm font-semibold text-gray-900 truncate">{item.title}</p>
                <p className="text-xs text-gray-500 mt-0.5 truncate">{item.description}</p>
              </div>
            </div>
            <Link
              href={item.primaryActionHref}
              className={`text-xs font-semibold shrink-0 ${p.icon} hover:underline flex items-center gap-1`}
            >
              {item.primaryActionLabel} <ArrowRight className="h-3 w-3" />
            </Link>
          </div>
        );
      })}
    </div>
  );
}

// ── KPI Card ──────────────────────────────────────────────────────────────────

function KpiCard({
  label,
  kpi,
  accent,
  icon,
}: {
  label: string;
  kpi: KpiValue | undefined;
  accent?: "red" | "amber" | "green" | "blue" | "purple";
  icon?: React.ReactNode;
}) {
  const value = kpi?.value ?? 0;
  const delta = kpi?.delta_7d;
  const hint = kpi?.hint;
  const href = kpi?.href;

  const accentCls: Record<string, string> = {
    red: "border-red-200 bg-red-50",
    amber: "border-amber-200 bg-amber-50",
    green: "border-green-200 bg-green-50",
    blue: "border-blue-200 bg-blue-50",
    purple: "border-purple-200 bg-purple-50",
  };

  const valueCls: Record<string, string> = {
    red: "text-red-700",
    amber: "text-amber-700",
    green: "text-green-700",
    blue: "text-blue-700",
    purple: "text-purple-700",
  };

  const card = (
    <div
      className={`rounded-xl border p-4 transition-all ${
        accent ? accentCls[accent] : "border-gray-200 bg-white"
      } ${href ? "hover:shadow-md hover:border-blue-300 cursor-pointer group" : ""}`}
    >
      <div className="flex items-start justify-between mb-2">
        <p className="text-xs font-medium text-gray-500 uppercase tracking-wide leading-tight">
          {label}
        </p>
        {icon && <span className="text-gray-400 group-hover:text-blue-500 transition-colors">{icon}</span>}
      </div>
      <p className={`text-3xl font-bold ${accent ? valueCls[accent] : "text-gray-900"}`}>
        {value.toLocaleString("tr-TR")}
      </p>
      {delta != null && delta > 0 && (
        <p className="mt-1 text-xs text-green-600 font-medium">
          <TrendingUp className="h-3 w-3 inline mr-0.5" />+{delta} bu hafta
        </p>
      )}
      {(!delta || delta === 0) && hint && (
        <p className="mt-1 text-xs text-gray-400">{hint}</p>
      )}
      {delta != null && delta > 0 && hint && (
        <p className="mt-0.5 text-xs text-gray-400">{hint}</p>
      )}
    </div>
  );

  if (href) return <Link href={href}>{card}</Link>;
  return card;
}

// ── Section title ─────────────────────────────────────────────────────────────

function SectionTitle({ children }: { children: React.ReactNode }) {
  return (
    <h2 className="text-xs font-bold text-gray-500 uppercase tracking-widest mb-3 mt-8 first:mt-0">
      {children}
    </h2>
  );
}

// ── Lifecycle Flow ────────────────────────────────────────────────────────────

function LifecycleFlow({ steps }: { steps: LifecycleStep[] }) {
  const statusColors: Record<string, string> = {
    draft: "bg-gray-100 text-gray-600 border-gray-200",
    active: "bg-green-100 text-green-700 border-green-200",
    moq_reached: "bg-blue-100 text-blue-700 border-blue-200",
    payment_collecting: "bg-indigo-100 text-indigo-700 border-indigo-200",
    ordered: "bg-purple-100 text-purple-700 border-purple-200",
    shipped: "bg-orange-100 text-orange-700 border-orange-200",
    delivered: "bg-emerald-100 text-emerald-700 border-emerald-200",
  };

  return (
    <div className="bg-white rounded-xl border border-gray-200 p-4">
      <div className="flex items-center gap-0 overflow-x-auto pb-1 scrollbar-hide">
        {steps.map((step, i) => (
          <div key={step.status} className="flex items-center flex-shrink-0">
            <Link href={step.href}>
              <div
                className={`flex flex-col items-center px-3 py-2 rounded-lg border transition-all hover:shadow-sm cursor-pointer min-w-[80px] ${
                  statusColors[step.status] ?? "bg-gray-100 text-gray-600 border-gray-200"
                }`}
              >
                <span className="text-2xl font-bold leading-none">{step.count}</span>
                <span className="text-xs font-medium mt-1 text-center leading-tight">{step.label}</span>
              </div>
            </Link>
            {i < steps.length - 1 && (
              <ChevronRight className="h-4 w-4 text-gray-300 mx-1 flex-shrink-0" />
            )}
          </div>
        ))}
      </div>
    </div>
  );
}

// ── Near MOQ Progress ─────────────────────────────────────────────────────────

function NearMoqPanel({ items }: { items: NearMoqActiveItem[] }) {
  if (!items.length) return null;
  return (
    <div className="bg-white border border-gray-200 rounded-xl p-4">
      <ul className="space-y-3">
        {items.map((item) => (
          <li key={item.campaign_id} className="flex items-center gap-3">
            <Link
              href={`/admin/products/${item.campaign_id}`}
              className="text-sm text-gray-700 hover:text-blue-600 w-40 truncate flex-shrink-0"
            >
              {item.title}
            </Link>
            <div className="flex-1 bg-gray-100 rounded-full h-2.5 min-w-0">
              <div
                className={`h-2.5 rounded-full transition-all ${
                  item.fill_pct >= 95 ? "bg-green-500" : "bg-blue-500"
                }`}
                style={{ width: `${Math.min(item.fill_pct, 100)}%` }}
              />
            </div>
            <span className="text-xs font-semibold text-gray-600 w-24 text-right flex-shrink-0">
              %{item.fill_pct} ({item.current_qty}/{item.moq})
            </span>
          </li>
        ))}
      </ul>
    </div>
  );
}

// ── Stat Row ──────────────────────────────────────────────────────────────────

function StatRow({
  label,
  value,
  subHref,
  subLabel,
}: {
  label: string;
  value: React.ReactNode;
  subHref?: string;
  subLabel?: string;
}) {
  return (
    <div className="flex items-center justify-between py-2 border-b border-gray-100 last:border-0">
      <span className="text-sm text-gray-600">{label}</span>
      <div className="text-right">
        <span className="text-sm font-semibold text-gray-900">{value}</span>
        {subHref && subLabel && (
          <Link href={subHref} className="block text-xs text-blue-500 hover:underline mt-0.5">
            {subLabel}
          </Link>
        )}
      </div>
    </div>
  );
}

// ── Quick Access ──────────────────────────────────────────────────────────────

function QuickAccess() {
  const groups = [
    {
      label: "Kampanyalar",
      icon: <BarChart2 className="h-4 w-4 text-blue-600" />,
      bg: "bg-blue-50",
      links: [
        { href: "/admin/products?status=active", label: "Aktif kampanyalar" },
        { href: "/admin/products?status=moq_reached", label: "MOQ dolanlar" },
        { href: "/admin/products?status=payment_collecting", label: "Ödeme toplananlar" },
      ],
    },
    {
      label: "Ürünler",
      icon: <Package className="h-4 w-4 text-indigo-600" />,
      bg: "bg-indigo-50",
      links: [
        { href: "/admin/products", label: "Tüm ürünler" },
        { href: "/admin/products/new", label: "Yeni ürün ekle" },
      ],
    },
    {
      label: "Ürün İstekleri",
      icon: <ClipboardList className="h-4 w-4 text-purple-600" />,
      bg: "bg-purple-50",
      links: [
        { href: "/admin/product-requests?status=pending", label: "Bekleyenleri gör" },
        { href: "/admin/product-requests", label: "Tüm istekler" },
      ],
    },
    {
      label: "Demand & Risk",
      icon: <Users className="h-4 w-4 text-rose-600" />,
      bg: "bg-rose-50",
      links: [
        { href: "/admin/demand-users", label: "Demand users" },
        { href: "/admin/fraud-watch", label: "Fraud watch" },
      ],
    },
  ];

  return (
    <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-4">
      {groups.map((g) => (
        <div key={g.label} className="bg-white border border-gray-200 rounded-xl p-4">
          <div className={`inline-flex p-2 rounded-lg ${g.bg} mb-3`}>{g.icon}</div>
          <p className="text-sm font-semibold text-gray-800 mb-2">{g.label}</p>
          <ul className="space-y-1.5">
            {g.links.map((l) => (
              <li key={l.href}>
                <Link
                  href={l.href}
                  className="text-xs text-gray-500 hover:text-blue-600 hover:underline flex items-center gap-1 transition-colors"
                >
                  <ArrowRight className="h-3 w-3 flex-shrink-0" />
                  {l.label}
                </Link>
              </li>
            ))}
          </ul>
        </div>
      ))}
    </div>
  );
}

// ── Skeleton ──────────────────────────────────────────────────────────────────

function KpiSkeleton() {
  return (
    <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3 mb-6">
      {Array.from({ length: 6 }).map((_, i) => (
        <div key={i} className="bg-white rounded-xl border border-gray-200 p-4 animate-pulse">
          <div className="h-3 bg-gray-200 rounded w-3/4 mb-3" />
          <div className="h-8 bg-gray-200 rounded w-1/2 mb-2" />
          <div className="h-2 bg-gray-100 rounded w-2/3" />
        </div>
      ))}
    </div>
  );
}

// ── Dashboard ─────────────────────────────────────────────────────────────────

export default function AdminDashboard() {
  const { data: summary, isLoading } = useDashboardSummary();
  const { data: pendingSuggestions } = useAdminSuggestions("pending");
  const { data: fraudWatch } = useFraudWatch();

  const attention = summary?.attention ?? [];
  const lifecycle = summary?.lifecycle ?? [];
  const kpis = summary?.kpis;
  const finance = summary?.finance;
  const demand = summary?.demand;
  const nearMoq = summary?.near_moq_active ?? [];

  // Fallback counts from legacy fields
  const fraudCount = fraudWatch?.total ?? kpis?.fraud_watch?.value ?? 0;
  const pendingCount = pendingSuggestions?.length ?? summary?.suggestions_pending ?? 0;

  return (
    <div className="p-6 sm:p-8 max-w-6xl">
      {/* Header */}
      <div className="mb-6">
        <h1 className="text-xl font-bold text-gray-900">Dashboard</h1>
        <p className="text-sm text-gray-500 mt-0.5">Operasyonel aksiyon merkezi</p>
      </div>

      {/* Attention banner */}
      {attention.length > 0 && <AttentionBanner items={attention} />}

      {/* ── KPI Grid ─────────────────────────────────────────────────── */}
      <SectionTitle>Durum & Risk</SectionTitle>

      {isLoading ? (
        <KpiSkeleton />
      ) : (
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3 mb-2">
          <KpiCard
            label="Aktif Kampanya"
            kpi={kpis?.active_campaigns ?? { value: summary?.campaigns_active ?? 0, href: "/admin/products?status=active" }}
            accent="green"
          />
          <KpiCard
            label="MOQ Doldu"
            kpi={kpis?.moq_reached ?? { value: summary?.campaigns_moq_reached ?? 0, href: "/admin/products?status=moq_reached" }}
            accent={summary?.campaigns_moq_reached ? "amber" : undefined}
          />
          <KpiCard
            label="Ödeme Topl."
            kpi={kpis?.payment_collecting ?? { value: summary?.campaigns_payment_collecting ?? 0, href: "/admin/products?status=payment_collecting" }}
            accent="blue"
          />
          <KpiCard
            label="Taslak"
            kpi={{ value: summary?.campaigns_draft ?? 0, href: "/admin/products?status=draft" }}
          />
          <KpiCard
            label="Fraud Watch"
            kpi={kpis?.fraud_watch ?? { value: fraudCount, href: "/admin/fraud-watch" }}
            accent={fraudCount > 0 ? "red" : undefined}
            icon={<ShieldAlert className="h-4 w-4" />}
          />
          <KpiCard
            label="Bekleyen İstek"
            kpi={kpis?.pending_suggestions ?? { value: pendingCount, href: "/admin/product-requests?status=pending" }}
            accent={pendingCount > 0 ? "purple" : undefined}
            icon={<ClipboardList className="h-4 w-4" />}
          />
        </div>
      )}

      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-2">
        {[
          { label: "Sipariş Verilmiş", val: summary?.campaigns_ordered ?? 0, href: "/admin/products?status=ordered" },
          { label: "Kargoda", val: summary?.campaigns_shipped ?? 0, href: "/admin/products?status=shipped" },
          { label: "Teslim Edildi", val: summary?.campaigns_delivered ?? 0, href: "/admin/products?status=delivered" },
          { label: "Toplam Ürün", val: summary?.products_total ?? 0, href: "/admin/products" },
        ].map((item) => (
          <Link key={item.label} href={item.href}>
            <div className="bg-white rounded-xl border border-gray-200 p-4 hover:border-blue-300 hover:shadow-sm transition-all">
              <p className="text-xs font-medium text-gray-500 uppercase tracking-wide">{item.label}</p>
              <p className="text-2xl font-bold text-gray-900 mt-1">{item.val}</p>
            </div>
          </Link>
        ))}
      </div>

      {/* ── Campaign Lifecycle ────────────────────────────────────────── */}
      {lifecycle.length > 0 && (
        <>
          <SectionTitle>Kampanya Lifecycle</SectionTitle>
          <LifecycleFlow steps={lifecycle} />
        </>
      )}

      {/* ── MOQ'ya En Yakın ───────────────────────────────────────────── */}
      {nearMoq.length > 0 && (
        <>
          <SectionTitle>MOQ&apos;ya En Yakın Aktif Kampanyalar</SectionTitle>
          <NearMoqPanel items={nearMoq} />
        </>
      )}

      {/* ── Finance & Demand ─────────────────────────────────────────── */}
      <div className="grid sm:grid-cols-2 gap-4 mt-8">
        {/* Finance */}
        <div>
          <SectionTitle>Finansal Durum</SectionTitle>
          <div className="bg-white rounded-xl border border-gray-200 p-4">
            <StatRow
              label="Tahsil Edilen"
              value={
                <span className="text-green-700">
                  {finance
                    ? formatCurrency(finance.collected_amount)
                    : formatCurrency(summary?.revenue_total_try ?? 0)}
                </span>
              }
            />
            <StatRow
              label="Bekleyen Tahsilat"
              value={
                finance
                  ? formatCurrency(finance.pending_amount)
                  : formatCurrency(summary?.pending_collection_try ?? 0)
              }
            />
            <StatRow
              label="Ödeme Dönüşüm Oranı"
              value={
                finance?.payment_conversion_rate != null
                  ? `%${finance.payment_conversion_rate}`
                  : "—"
              }
            />
            <StatRow
              label="Ort. Ödeme Tutarı"
              value={
                finance?.average_paid_order_value
                  ? formatCurrency(finance.average_paid_order_value)
                  : "—"
              }
            />
            <StatRow
              label="Davet Edilen Katılımcı"
              value={fmt(finance?.invited_participant_count)}
            />
            <StatRow
              label="Ödeme Yapan Katılımcı"
              value={
                <span className="text-blue-700">{fmt(finance?.paid_participant_count)}</span>
              }
            />
          </div>
        </div>

        {/* Demand */}
        <div>
          <SectionTitle>Talep İstihbarat</SectionTitle>
          <div className="bg-white rounded-xl border border-gray-200 p-4">
            <StatRow
              label="Toplam Talep Adedi"
              value={fmt(demand?.total_quantity ?? summary?.demand_total)}
              subHref="/admin/demand-users"
              subLabel="Kullanıcı detayı →"
            />
            <StatRow
              label="Benzersiz Kullanıcı"
              value={fmt(demand?.unique_users ?? summary?.demand_unique_users)}
              subHref="/admin/demand-users"
              subLabel="Tümünü gör →"
            />
            <StatRow
              label="Kullanıcı Başı Ort."
              value={
                demand?.average_per_user != null
                  ? demand.average_per_user.toFixed(1)
                  : "—"
              }
            />
            <StatRow
              label="Son 30 Gün"
              value={fmt(demand?.last_30_days_quantity ?? summary?.demand_last_30d)}
            />
            <StatRow
              label="Son 7 Gün"
              value={fmt(demand?.last_7_days_quantity)}
            />
            <StatRow
              label="Şüpheli Kayıt"
              value={
                <Link
                  href="/admin/fraud-watch"
                  className={`font-semibold ${fraudCount > 0 ? "text-red-600 hover:underline" : "text-gray-900"}`}
                >
                  {fraudCount > 0 ? `${fraudCount} → Fraud Watch` : "Temiz"}
                </Link>
              }
            />
          </div>
        </div>
      </div>

      {/* ── Quick Access ─────────────────────────────────────────────── */}
      <SectionTitle>Hızlı Erişim</SectionTitle>
      <QuickAccess />
    </div>
  );
}
