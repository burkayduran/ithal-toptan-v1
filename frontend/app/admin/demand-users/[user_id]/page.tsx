"use client";

import { use, useState } from "react";
import Link from "next/link";
import { useDemandUserDetail } from "@/features/admin/hooks";
import type { DemandUserDetailCampaign, DemandUserDetailEntry } from "@/features/admin/types";
import {
  ArrowLeft, Users, Flag, Trash2, ChevronDown, ChevronUp,
  AlertTriangle, Package,
} from "lucide-react";

// ── Status badge ─────────────────────────────────────────────────────────────

function EntryStatusBadge({ status }: { status: string }) {
  const config =
    status === "active"
      ? "bg-green-100 text-green-700"
      : status === "flagged"
      ? "bg-amber-100 text-amber-700"
      : "bg-red-100 text-red-600";
  return (
    <span className={`inline-block px-2 py-0.5 rounded text-xs font-medium ${config}`}>
      {status === "active" ? "Aktif" : status === "flagged" ? "Flaglendi" : "Silindi"}
    </span>
  );
}

// ── Campaign row ──────────────────────────────────────────────────────────────

function CampaignRow({ camp }: { camp: DemandUserDetailCampaign }) {
  const [expanded, setExpanded] = useState(false);

  const moqPct =
    camp.campaign_moq && camp.campaign_moq > 0
      ? Math.round((camp.total_active_quantity / camp.campaign_moq) * 100)
      : null;

  return (
    <>
      <tr
        className={`hover:bg-gray-50 transition-colors cursor-pointer ${expanded ? "bg-gray-50" : ""}`}
        onClick={() => setExpanded((v) => !v)}
      >
        <td className="px-4 py-3">
          <div className="flex items-start gap-2">
            <Package className="h-4 w-4 text-gray-400 mt-0.5 flex-shrink-0" />
            <div>
              <p className="text-sm font-medium text-gray-900 truncate max-w-[220px]">
                {camp.campaign_title}
              </p>
              <p className="text-xs text-gray-400">
                <span className="capitalize">{camp.campaign_status}</span>
                {camp.campaign_moq != null && (
                  <span className="ml-2">MOQ: {camp.campaign_moq}</span>
                )}
              </p>
            </div>
          </div>
        </td>
        <td className="px-4 py-3 text-right">
          <span className="text-sm font-bold text-blue-700">{camp.total_active_quantity}</span>
          {moqPct != null && (
            <span className="text-xs text-gray-400 ml-1">(%{moqPct})</span>
          )}
        </td>
        <td className="px-4 py-3 text-right">
          <span className="text-sm text-gray-600">{camp.entry_count}</span>
        </td>
        <td className="px-4 py-3 text-right">
          {camp.flagged_count > 0 ? (
            <span className="inline-flex items-center gap-0.5 px-1.5 py-0.5 bg-amber-100 text-amber-700 rounded text-xs font-medium">
              <Flag className="h-3 w-3" />
              {camp.flagged_count}
            </span>
          ) : (
            <span className="text-xs text-gray-300">—</span>
          )}
        </td>
        <td className="px-4 py-3 text-right">
          {camp.removed_count > 0 ? (
            <span className="inline-flex items-center gap-0.5 px-1.5 py-0.5 bg-red-100 text-red-600 rounded text-xs font-medium">
              <Trash2 className="h-3 w-3" />
              {camp.removed_count}
            </span>
          ) : (
            <span className="text-xs text-gray-300">—</span>
          )}
        </td>
        <td className="px-4 py-3 text-right text-xs text-gray-400">
          {new Date(camp.last_activity).toLocaleDateString("tr-TR")}
        </td>
        <td className="px-4 py-3 text-right">
          <div className="flex items-center justify-end gap-2">
            <Link
              href={`/admin/products/${camp.campaign_id}`}
              onClick={(e) => e.stopPropagation()}
              className="text-xs text-blue-600 hover:underline"
            >
              Kampanya →
            </Link>
            <button className="text-gray-400">
              {expanded ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
            </button>
          </div>
        </td>
      </tr>

      {/* Expanded entries */}
      {expanded && (
        <tr className="bg-blue-50">
          <td colSpan={7} className="px-6 py-3">
            <table className="w-full text-xs">
              <thead>
                <tr className="text-gray-500">
                  <th className="text-left pb-1 font-medium">Adet</th>
                  <th className="text-left pb-1 font-medium">Durum</th>
                  <th className="text-left pb-1 font-medium">Tarih</th>
                  <th className="text-left pb-1 font-medium">Not / Sebep</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-blue-100">
                {camp.entries.map((entry: DemandUserDetailEntry) => (
                  <tr key={entry.id}>
                    <td className="py-1.5 font-semibold text-gray-800">{entry.quantity}</td>
                    <td className="py-1.5">
                      <EntryStatusBadge status={entry.status} />
                    </td>
                    <td className="py-1.5 text-gray-400">
                      {new Date(entry.created_at).toLocaleDateString("tr-TR")}
                    </td>
                    <td className="py-1.5 text-gray-500">
                      {entry.removal_reason && (
                        <span className="text-red-500">{entry.removal_reason}</span>
                      )}
                      {entry.admin_note && !entry.removal_reason && (
                        <span className="italic">{entry.admin_note}</span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </td>
        </tr>
      )}
    </>
  );
}

// ── Page ──────────────────────────────────────────────────────────────────────

export default function DemandUserDetailPage({
  params,
}: {
  params: Promise<{ user_id: string }>;
}) {
  const { user_id } = use(params);
  const { data, isLoading, isError } = useDemandUserDetail(user_id);

  return (
    <div className="p-8 max-w-5xl">
      {/* Header */}
      <div className="flex items-center gap-3 mb-1">
        <Link href="/admin/demand-users" className="text-gray-400 hover:text-gray-600 transition-colors">
          <ArrowLeft className="h-4 w-4" />
        </Link>
        <div className="flex items-center gap-2">
          <Users className="h-5 w-5 text-purple-600" />
          <h1 className="text-xl font-bold text-gray-900">
            {isLoading ? "Yükleniyor…" : data?.email ?? "Kullanıcı Detayı"}
          </h1>
        </div>
      </div>
      {data?.full_name && (
        <p className="text-sm text-gray-500 mb-6 ml-7">{data.full_name}</p>
      )}

      {/* Totals */}
      {data && (
        <div className="grid grid-cols-2 sm:grid-cols-5 gap-3 mb-8">
          {[
            { label: "Toplam Entry", value: data.totals.total_entries },
            { label: "Aktif Adet", value: data.totals.total_active_quantity, highlight: true },
            { label: "Kampanya", value: data.totals.unique_campaigns },
            {
              label: "Flaglendi",
              value: data.totals.flagged_count,
              warn: data.totals.flagged_count > 0,
            },
            {
              label: "Silindi",
              value: data.totals.removed_count,
              danger: data.totals.removed_count > 0,
            },
          ].map(({ label, value, highlight, warn, danger }) => (
            <div
              key={label}
              className={`bg-white rounded-xl border p-4 text-center ${
                danger
                  ? "border-red-200 bg-red-50"
                  : warn
                  ? "border-amber-200 bg-amber-50"
                  : "border-gray-200"
              }`}
            >
              <p className="text-xs text-gray-500 mb-1">{label}</p>
              <p
                className={`text-2xl font-bold ${
                  danger
                    ? "text-red-700"
                    : warn
                    ? "text-amber-700"
                    : highlight
                    ? "text-blue-700"
                    : "text-gray-900"
                }`}
              >
                {value}
              </p>
            </div>
          ))}
        </div>
      )}

      {/* Fraud link if any flags */}
      {data && (data.totals.flagged_count > 0 || data.totals.removed_count > 0) && (
        <div className="mb-4 flex items-center gap-2 bg-amber-50 border border-amber-200 rounded-lg px-4 py-3 text-sm text-amber-800">
          <AlertTriangle className="h-4 w-4 flex-shrink-0" />
          <span>Bu kullanıcıda şüpheli aktivite var.</span>
          <Link
            href="/admin/fraud-watch"
            className="ml-auto text-amber-700 hover:text-amber-900 font-medium hover:underline"
          >
            Fraud Watch →
          </Link>
        </div>
      )}

      {/* Campaigns table */}
      {isLoading ? (
        <div className="bg-white rounded-xl border border-gray-200 p-8 text-center">
          <div className="animate-spin h-6 w-6 border-2 border-blue-600 border-t-transparent rounded-full mx-auto mb-2" />
          <p className="text-sm text-gray-500">Yükleniyor…</p>
        </div>
      ) : isError ? (
        <div className="bg-white rounded-xl border border-red-200 p-8 text-center">
          <p className="text-sm text-red-500">Kullanıcı bulunamadı.</p>
        </div>
      ) : data?.campaigns.length === 0 ? (
        <div className="bg-white rounded-xl border border-gray-200 p-8 text-center">
          <p className="text-sm text-gray-400">Henüz demand kaydı yok.</p>
        </div>
      ) : (
        <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="bg-gray-50 border-b border-gray-200">
                <tr>
                  <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wide">Kampanya</th>
                  <th className="px-4 py-3 text-right text-xs font-semibold text-gray-500 uppercase tracking-wide">Aktif Adet</th>
                  <th className="px-4 py-3 text-right text-xs font-semibold text-gray-500 uppercase tracking-wide">Entry</th>
                  <th className="px-4 py-3 text-right text-xs font-semibold text-gray-500 uppercase tracking-wide">Flag</th>
                  <th className="px-4 py-3 text-right text-xs font-semibold text-gray-500 uppercase tracking-wide">Silindi</th>
                  <th className="px-4 py-3 text-right text-xs font-semibold text-gray-500 uppercase tracking-wide">Son Aktivite</th>
                  <th className="px-4 py-3 text-right text-xs font-semibold text-gray-500 uppercase tracking-wide">—</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {data?.campaigns.map((camp) => (
                  <CampaignRow key={camp.campaign_id} camp={camp} />
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
