"use client";

import { useState } from "react";
import Link from "next/link";
import { useFraudWatch } from "@/features/admin/hooks";
import type { FraudWatchEntry, FraudRiskLevel } from "@/features/admin/types";
import {
  ShieldAlert, ArrowLeft, ExternalLink, Flag, Users,
  AlertTriangle, ChevronDown, ChevronUp,
} from "lucide-react";

// ── Risk level badge ──────────────────────────────────────────────────────────

function RiskBadge({ level }: { level: FraudRiskLevel }) {
  const config = {
    watch: { bg: "bg-yellow-100", text: "text-yellow-800", label: "Watch" },
    high: { bg: "bg-orange-100", text: "text-orange-800", label: "High" },
    critical: { bg: "bg-red-100", text: "text-red-800", label: "Critical" },
  }[level];

  return (
    <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-semibold ${config.bg} ${config.text}`}>
      <AlertTriangle className="h-3 w-3" />
      {config.label}
    </span>
  );
}

// ── Percent bar ───────────────────────────────────────────────────────────────

function MoqBar({ pct }: { pct: number }) {
  const clamped = Math.min(pct, 100);
  const color = pct >= 30 ? "bg-red-500" : pct >= 20 ? "bg-orange-500" : "bg-yellow-400";
  return (
    <div className="flex items-center gap-2">
      <div className="w-20 bg-gray-100 rounded-full h-2">
        <div className={`${color} h-2 rounded-full`} style={{ width: `${clamped}%` }} />
      </div>
      <span className={`text-xs font-bold ${pct >= 30 ? "text-red-600" : pct >= 20 ? "text-orange-600" : "text-yellow-600"}`}>
        %{pct}
      </span>
    </div>
  );
}

// ── Row ───────────────────────────────────────────────────────────────────────

function FraudRow({ entry }: { entry: FraudWatchEntry }) {
  const [expanded, setExpanded] = useState(false);

  return (
    <>
      <tr
        className={`hover:bg-gray-50 transition-colors cursor-pointer ${expanded ? "bg-gray-50" : ""}`}
        onClick={() => setExpanded((v) => !v)}
      >
        <td className="px-4 py-3">
          <RiskBadge level={entry.risk_level} />
        </td>
        <td className="px-4 py-3">
          <div>
            <p className="text-sm font-medium text-gray-900 truncate max-w-[180px]">{entry.email}</p>
            {entry.full_name && (
              <p className="text-xs text-gray-400 truncate max-w-[180px]">{entry.full_name}</p>
            )}
          </div>
        </td>
        <td className="px-4 py-3">
          <p className="text-sm text-gray-700 truncate max-w-[180px]">{entry.campaign_title}</p>
          <p className="text-xs text-gray-400">MOQ: {entry.campaign_moq}</p>
        </td>
        <td className="px-4 py-3">
          <MoqBar pct={entry.percent_of_moq} />
        </td>
        <td className="px-4 py-3 text-right">
          <span className="text-sm font-bold text-gray-900">{entry.user_total_quantity}</span>
          <span className="text-xs text-gray-400 ml-1">/ {entry.campaign_moq}</span>
        </td>
        <td className="px-4 py-3 text-right">
          <span className="text-sm text-gray-600">{entry.entry_count}</span>
        </td>
        <td className="px-4 py-3 text-right">
          {entry.flagged_count > 0 && (
            <span className="inline-flex items-center gap-0.5 px-1.5 py-0.5 bg-yellow-100 text-yellow-700 rounded text-xs font-medium">
              <Flag className="h-3 w-3" />
              {entry.flagged_count}
            </span>
          )}
        </td>
        <td className="px-4 py-3 text-right text-xs text-gray-400">
          {entry.last_activity
            ? new Date(entry.last_activity).toLocaleDateString("tr-TR")
            : "—"}
        </td>
        <td className="px-4 py-3 text-right">
          <div className="flex items-center justify-end gap-2">
            <Link
              href={`/admin/demand-users/${entry.user_id}`}
              onClick={(e) => e.stopPropagation()}
              title="Kullanıcı detayı"
              className="text-gray-400 hover:text-purple-600 transition-colors"
            >
              <Users className="h-4 w-4" />
            </Link>
            <Link
              href={`/admin/products/${entry.campaign_id}`}
              onClick={(e) => e.stopPropagation()}
              title="Kampanyaya git"
              className="text-gray-400 hover:text-blue-600 transition-colors"
            >
              <ExternalLink className="h-4 w-4" />
            </Link>
            <button className="text-gray-400 hover:text-gray-600 transition-colors">
              {expanded ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
            </button>
          </div>
        </td>
      </tr>

      {/* Expanded risk reasons */}
      {expanded && (
        <tr className="bg-yellow-50">
          <td colSpan={9} className="px-4 py-3">
            <div className="flex flex-wrap gap-2">
              {entry.risk_reasons.map((reason, i) => (
                <span
                  key={i}
                  className="inline-flex items-center gap-1 px-2 py-1 bg-white border border-yellow-200 text-yellow-800 rounded text-xs"
                >
                  <AlertTriangle className="h-3 w-3" />
                  {reason}
                </span>
              ))}
            </div>
          </td>
        </tr>
      )}
    </>
  );
}

// ── Page ──────────────────────────────────────────────────────────────────────

type FilterLevel = "all" | "watch" | "high" | "critical";

export default function FraudWatchPage() {
  const { data, isLoading } = useFraudWatch();
  const [filterLevel, setFilterLevel] = useState<FilterLevel>("all");

  const allEntries = data?.entries ?? [];
  const entries =
    filterLevel === "all"
      ? allEntries
      : allEntries.filter((e) => e.risk_level === filterLevel);

  const counts = {
    watch: allEntries.filter((e) => e.risk_level === "watch").length,
    high: allEntries.filter((e) => e.risk_level === "high").length,
    critical: allEntries.filter((e) => e.risk_level === "critical").length,
  };

  return (
    <div className="p-8 max-w-6xl">
      {/* Header */}
      <div className="flex items-center gap-3 mb-1">
        <Link href="/admin" className="text-gray-400 hover:text-gray-600 transition-colors">
          <ArrowLeft className="h-4 w-4" />
        </Link>
        <div className="flex items-center gap-2">
          <ShieldAlert className="h-5 w-5 text-red-600" />
          <h1 className="text-xl font-bold text-gray-900">Fraud Watch</h1>
        </div>
      </div>
      <p className="text-sm text-gray-500 mb-6 ml-7">
        MOQ&apos;nun %{data?.threshold_pct ?? 10}+'unu tek başına alan kullanıcılar risk olarak işaretlenir.
      </p>

      {/* Risk summary cards */}
      <div className="grid grid-cols-3 gap-4 mb-6">
        {(["watch", "high", "critical"] as const).map((level) => {
          const config = {
            watch: { label: "Watch (%10+)", bg: "bg-yellow-50 border-yellow-200", textColor: "text-yellow-700" },
            high: { label: "High (%20+)", bg: "bg-orange-50 border-orange-200", textColor: "text-orange-700" },
            critical: { label: "Critical (%30+)", bg: "bg-red-50 border-red-200", textColor: "text-red-700" },
          }[level];
          return (
            <button
              key={level}
              onClick={() => setFilterLevel(filterLevel === level ? "all" : level)}
              className={`rounded-xl border p-4 text-left transition-all ${config.bg} ${
                filterLevel === level ? "ring-2 ring-offset-1 ring-gray-400" : ""
              }`}
            >
              <p className={`text-xs font-semibold uppercase ${config.textColor}`}>{config.label}</p>
              <p className={`text-2xl font-bold mt-1 ${config.textColor}`}>{counts[level]}</p>
            </button>
          );
        })}
      </div>

      {/* Filter tabs */}
      <div className="flex items-center gap-2 mb-4">
        <span className="text-xs text-gray-500">Filtre:</span>
        {(["all", "watch", "high", "critical"] as const).map((level) => (
          <button
            key={level}
            onClick={() => setFilterLevel(level)}
            className={`px-3 py-1.5 text-xs font-medium rounded-lg transition-colors ${
              filterLevel === level
                ? "bg-gray-800 text-white"
                : "bg-gray-100 text-gray-600 hover:bg-gray-200"
            }`}
          >
            {level === "all" ? `Tümü (${allEntries.length})` : `${level} (${counts[level]})`}
          </button>
        ))}
      </div>

      {/* Table */}
      {isLoading ? (
        <div className="bg-white rounded-xl border border-gray-200 p-8 text-center">
          <div className="animate-spin h-6 w-6 border-2 border-red-600 border-t-transparent rounded-full mx-auto mb-2" />
          <p className="text-sm text-gray-500">Yükleniyor…</p>
        </div>
      ) : entries.length === 0 ? (
        <div className="bg-white rounded-xl border border-gray-200 p-8 text-center">
          <ShieldAlert className="h-10 w-10 text-gray-200 mx-auto mb-3" />
          <p className="text-sm font-semibold text-gray-500">Şüpheli kayıt yok</p>
          <p className="text-xs text-gray-400 mt-1">
            MOQ&apos;nun %{data?.threshold_pct ?? 10}+'unu alan kullanıcı bulunamadı.
          </p>
        </div>
      ) : (
        <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="bg-gray-50 border-b border-gray-200">
                <tr>
                  <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wide">Risk</th>
                  <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wide">Kullanıcı</th>
                  <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wide">Kampanya</th>
                  <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wide">MOQ %</th>
                  <th className="px-4 py-3 text-right text-xs font-semibold text-gray-500 uppercase tracking-wide">Adet</th>
                  <th className="px-4 py-3 text-right text-xs font-semibold text-gray-500 uppercase tracking-wide">Entry</th>
                  <th className="px-4 py-3 text-right text-xs font-semibold text-gray-500 uppercase tracking-wide">Flag</th>
                  <th className="px-4 py-3 text-right text-xs font-semibold text-gray-500 uppercase tracking-wide">Son Aktivite</th>
                  <th className="px-4 py-3 text-right text-xs font-semibold text-gray-500 uppercase tracking-wide">—</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {entries.map((entry) => (
                  <FraudRow
                    key={`${entry.user_id}-${entry.campaign_id}`}
                    entry={entry}
                  />
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
