"use client";

import { useState } from "react";
import Link from "next/link";
import { useDemandUsers } from "@/features/admin/hooks";
import type { DemandUser } from "@/features/admin/types";
import {
  Users, ArrowLeft, ArrowUpDown, Flag, Trash2, ExternalLink,
} from "lucide-react";

type SortOption = "quantity_desc" | "recent" | "campaigns" | "flagged";

const SORT_OPTIONS: { value: SortOption; label: string }[] = [
  { value: "quantity_desc", label: "En Yüksek Miktar" },
  { value: "recent", label: "Son Aktivite" },
  { value: "campaigns", label: "En Çok Kampanya" },
  { value: "flagged", label: "Flaglenenler" },
];

function UserRow({ user }: { user: DemandUser }) {
  return (
    <tr className="hover:bg-gray-50 transition-colors">
      <td className="px-4 py-3">
        <div>
          <p className="text-sm font-medium text-gray-900 truncate max-w-[200px]">{user.email}</p>
          {user.full_name && (
            <p className="text-xs text-gray-400 truncate max-w-[200px]">{user.full_name}</p>
          )}
        </div>
      </td>
      <td className="px-4 py-3 text-right">
        <span className="text-sm font-semibold text-gray-900">{user.total_entries}</span>
      </td>
      <td className="px-4 py-3 text-right">
        <span className="text-sm font-bold text-blue-700">{user.total_quantity}</span>
      </td>
      <td className="px-4 py-3 text-right">
        <span className="text-sm text-gray-700">{user.unique_campaigns}</span>
      </td>
      <td className="px-4 py-3 text-right">
        <span className="text-sm text-gray-700">{user.max_single_entry_qty}</span>
      </td>
      <td className="px-4 py-3 text-right">
        {user.flagged_count > 0 ? (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 bg-yellow-100 text-yellow-700 rounded text-xs font-medium">
            <Flag className="h-3 w-3" />
            {user.flagged_count}
          </span>
        ) : (
          <span className="text-xs text-gray-300">—</span>
        )}
      </td>
      <td className="px-4 py-3 text-right">
        {user.removed_count > 0 ? (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 bg-red-100 text-red-700 rounded text-xs font-medium">
            <Trash2 className="h-3 w-3" />
            {user.removed_count}
          </span>
        ) : (
          <span className="text-xs text-gray-300">—</span>
        )}
      </td>
      <td className="px-4 py-3 text-right text-xs text-gray-400">
        {user.last_activity
          ? new Date(user.last_activity).toLocaleDateString("tr-TR")
          : "—"}
      </td>
      <td className="px-4 py-3 text-right">
        <div className="flex items-center justify-end gap-2">
          <Link
            href={`/admin/demand-users/${user.user_id}`}
            className="inline-flex items-center gap-1 text-xs text-blue-600 hover:text-blue-800"
            title="Kullanıcı detayı"
          >
            <ExternalLink className="h-3 w-3" />
          </Link>
        </div>
      </td>
    </tr>
  );
}

export default function DemandUsersPage() {
  const [sort, setSort] = useState<SortOption>("quantity_desc");
  const { data, isLoading } = useDemandUsers(sort);

  const users = data?.users ?? [];

  return (
    <div className="p-8 max-w-6xl">
      {/* Header */}
      <div className="flex items-center gap-3 mb-1">
        <Link href="/admin" className="text-gray-400 hover:text-gray-600 transition-colors">
          <ArrowLeft className="h-4 w-4" />
        </Link>
        <div className="flex items-center gap-2">
          <Users className="h-5 w-5 text-purple-600" />
          <h1 className="text-xl font-bold text-gray-900">Demand Users</h1>
        </div>
      </div>
      <p className="text-sm text-gray-500 mb-6 ml-7">
        Kullanıcı bazında aggregate talep analizi.{" "}
        <Link href="/admin/fraud-watch" className="text-blue-600 hover:underline">
          Fraud Watch →
        </Link>
      </p>

      {/* Summary + Filters */}
      <div className="flex items-center justify-between mb-4 gap-4">
        <div className="text-sm text-gray-600">
          {data ? (
            <span>
              <strong>{data.total}</strong> kullanıcı
            </span>
          ) : null}
        </div>
        <div className="flex items-center gap-2">
          <ArrowUpDown className="h-4 w-4 text-gray-400" />
          <span className="text-xs text-gray-500">Sırala:</span>
          <div className="flex gap-1">
            {SORT_OPTIONS.map((opt) => (
              <button
                key={opt.value}
                onClick={() => setSort(opt.value)}
                className={`px-3 py-1.5 text-xs font-medium rounded-lg transition-colors ${
                  sort === opt.value
                    ? "bg-blue-600 text-white"
                    : "bg-gray-100 text-gray-600 hover:bg-gray-200"
                }`}
              >
                {opt.label}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Table */}
      {isLoading ? (
        <div className="bg-white rounded-xl border border-gray-200 p-8 text-center">
          <div className="animate-spin h-6 w-6 border-2 border-blue-600 border-t-transparent rounded-full mx-auto mb-2" />
          <p className="text-sm text-gray-500">Yükleniyor…</p>
        </div>
      ) : users.length === 0 ? (
        <div className="bg-white rounded-xl border border-gray-200 p-8 text-center">
          <Users className="h-8 w-8 text-gray-300 mx-auto mb-2" />
          <p className="text-sm text-gray-500">Henüz demand kaydı yok.</p>
        </div>
      ) : (
        <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="bg-gray-50 border-b border-gray-200">
                <tr>
                  <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wide">
                    Kullanıcı
                  </th>
                  <th className="px-4 py-3 text-right text-xs font-semibold text-gray-500 uppercase tracking-wide">
                    Entry
                  </th>
                  <th className="px-4 py-3 text-right text-xs font-semibold text-gray-500 uppercase tracking-wide">
                    Toplam Adet
                  </th>
                  <th className="px-4 py-3 text-right text-xs font-semibold text-gray-500 uppercase tracking-wide">
                    Kampanya
                  </th>
                  <th className="px-4 py-3 text-right text-xs font-semibold text-gray-500 uppercase tracking-wide">
                    Max Tek
                  </th>
                  <th className="px-4 py-3 text-right text-xs font-semibold text-gray-500 uppercase tracking-wide">
                    Flaglendi
                  </th>
                  <th className="px-4 py-3 text-right text-xs font-semibold text-gray-500 uppercase tracking-wide">
                    Silindi
                  </th>
                  <th className="px-4 py-3 text-right text-xs font-semibold text-gray-500 uppercase tracking-wide">
                    Son Aktivite
                  </th>
                  <th className="px-4 py-3 text-right text-xs font-semibold text-gray-500 uppercase tracking-wide">
                    —
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {users.map((user) => (
                  <UserRow key={user.user_id} user={user} />
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
