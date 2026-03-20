"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { useAdminSuggestions, useUpdateSuggestion } from "@/features/admin/hooks";
import type { AdminSuggestion } from "@/features/admin/types";
import { Button } from "@/components/ui/button";
import { Loader2, ChevronDown, Plus } from "lucide-react";

const STATUS_OPTIONS = ["pending", "reviewing", "approved", "rejected"] as const;
type RequestStatus = (typeof STATUS_OPTIONS)[number];

const STATUS_LABEL: Record<RequestStatus, string> = {
  pending: "Bekliyor",
  reviewing: "İnceleniyor",
  approved: "Onaylandı",
  rejected: "Reddedildi",
};

function RequestRow({
  req,
  onSave,
  isSaving,
  onCreateProduct,
}: {
  req: AdminSuggestion;
  onSave: (id: string, status: string, notes: string) => void;
  isSaving: boolean;
  onCreateProduct: (req: AdminSuggestion) => void;
}) {
  const [status, setStatus] = useState(req.status);
  const [notes, setNotes] = useState(req.admin_notes ?? "");
  const dirty = status !== req.status || notes !== (req.admin_notes ?? "");

  return (
    <tr className="border-b border-gray-100 last:border-0">
      <td className="px-4 py-4 align-top">
        <p className="font-medium text-gray-900 text-sm">{req.title}</p>
        {req.description && (
          <p className="text-xs text-gray-400 mt-0.5 line-clamp-2">{req.description}</p>
        )}
        {req.reference_url && (
          <a
            href={req.reference_url}
            target="_blank"
            rel="noopener noreferrer"
            className="text-xs text-blue-500 hover:underline mt-0.5 block truncate max-w-xs"
          >
            {req.reference_url}
          </a>
        )}
        <p className="text-xs text-gray-300 mt-1">
          {new Date(req.created_at).toLocaleDateString("tr-TR")}
        </p>
      </td>
      <td className="px-4 py-4 align-top hidden md:table-cell">
        {req.expected_price_try != null ? (
          <span className="text-sm text-gray-600">
            ₺{req.expected_price_try.toLocaleString("tr-TR")}
          </span>
        ) : (
          <span className="text-xs text-gray-300">—</span>
        )}
      </td>
      <td className="px-4 py-4 align-top">
        <div className="space-y-2">
          <div className="relative inline-block">
            <select
              value={status}
              onChange={(e) => setStatus(e.target.value)}
              className="text-xs border border-gray-200 rounded-lg pl-2 pr-7 py-1.5 bg-white text-gray-700 focus:outline-none appearance-none"
            >
              {STATUS_OPTIONS.map((s) => (
                <option key={s} value={s}>
                  {STATUS_LABEL[s]}
                </option>
              ))}
            </select>
            <ChevronDown className="absolute right-1.5 top-1/2 -translate-y-1/2 h-3 w-3 text-gray-400 pointer-events-none" />
          </div>
          <textarea
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
            rows={2}
            placeholder="Admin notu..."
            className="w-full text-xs border border-gray-200 rounded-lg px-2 py-1.5 focus:outline-none focus:ring-1 focus:ring-blue-400 resize-none min-w-[200px]"
          />
          <div className="flex items-center gap-2">
            {dirty && (
              <Button
                size="sm"
                className="h-7 text-xs"
                onClick={() => onSave(req.id, status, notes)}
                disabled={isSaving}
              >
                {isSaving ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : "Kaydet"}
              </Button>
            )}
            {req.status === "approved" && (
              <Button
                size="sm"
                variant="outline"
                className="h-7 text-xs gap-1"
                onClick={() => onCreateProduct(req)}
              >
                <Plus className="h-3 w-3" />
                Ürün Oluştur
              </Button>
            )}
          </div>
        </div>
      </td>
    </tr>
  );
}

export default function AdminProductRequestsPage() {
  const router = useRouter();
  const [activeStatus, setActiveStatus] = useState<RequestStatus>("pending");
  const { data: requests, isLoading, isError, refetch } = useAdminSuggestions(activeStatus);
  const { mutate: updateRequest, isPending: isSaving } = useUpdateSuggestion();

  function handleSave(id: string, status: string, admin_notes: string) {
    updateRequest({ id, payload: { status, admin_notes } });
  }

  function handleCreateProduct(req: AdminSuggestion) {
    const params = new URLSearchParams();
    if (req.title) params.set("title", req.title);
    if (req.description) params.set("description", req.description);
    params.set("from_request", req.id);
    router.push(`/admin/products/new?${params.toString()}`);
  }

  return (
    <div className="p-6 max-w-4xl">
      <h1 className="text-xl font-bold text-gray-900 mb-6">Ürün İstekleri</h1>

      {/* Status tabs */}
      <div className="flex gap-1 mb-5 bg-gray-100 p-1 rounded-lg w-fit">
        {STATUS_OPTIONS.map((s) => (
          <button
            key={s}
            onClick={() => setActiveStatus(s)}
            className={`px-3 py-1.5 rounded-md text-xs font-medium transition-colors ${
              activeStatus === s
                ? "bg-white text-gray-900 shadow-sm"
                : "text-gray-500 hover:text-gray-700"
            }`}
          >
            {STATUS_LABEL[s]}
          </button>
        ))}
      </div>

      {isLoading ? (
        <div className="text-sm text-gray-400 py-10 text-center">Yükleniyor...</div>
      ) : isError ? (
        <div className="text-sm text-red-500 py-10 text-center">
          Hata.{" "}
          <button className="underline" onClick={() => refetch()}>
            Tekrar dene
          </button>
        </div>
      ) : (requests ?? []).length === 0 ? (
        <div className="text-sm text-gray-400 py-10 text-center">
          Bu durumda istek bulunmuyor.
        </div>
      ) : (
        <div className="bg-white border border-gray-200 rounded-xl overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 border-b border-gray-200">
              <tr>
                <th className="text-left px-4 py-3 text-xs font-medium text-gray-600">İstek</th>
                <th className="text-left px-4 py-3 text-xs font-medium text-gray-600 hidden md:table-cell">
                  Hedef Fiyat
                </th>
                <th className="text-left px-4 py-3 text-xs font-medium text-gray-600">
                  Durum / Not
                </th>
              </tr>
            </thead>
            <tbody>
              {(requests ?? []).map((req) => (
                <RequestRow
                  key={req.id}
                  req={req}
                  onSave={handleSave}
                  isSaving={isSaving}
                  onCreateProduct={handleCreateProduct}
                />
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
