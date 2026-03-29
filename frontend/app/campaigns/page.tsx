"use client";

import { useState, useMemo, useEffect } from "react";
import { useCampaigns } from "@/features/campaigns/hooks";
import {
  filterCampaigns,
  sortCampaigns,
  type StatusFilter,
  type SortOption,
} from "@/features/campaigns/adapters";
import PageContainer from "@/components/layout/PageContainer";
import CampaignGrid from "@/components/campaign/CampaignGrid";
import CampaignCardSkeleton from "@/components/campaign/CampaignCardSkeleton";
import ErrorState from "@/components/common/ErrorState";
import EmptyState from "@/components/common/EmptyState";
import { Input } from "@/components/ui/input";
import { cn } from "@/lib/utils";
import { Search } from "lucide-react";

const STATUS_OPTIONS: { value: StatusFilter; label: string }[] = [
  { value: "all", label: "Tümü" },
  { value: "active", label: "Aktif" },
  { value: "near_unlock", label: "Hedefe Yakın" },
  { value: "moq_reached", label: "Hedefe Ulaştı" },
];

const SORT_OPTIONS: { value: SortOption; label: string }[] = [
  { value: "near_unlock", label: "Hedefe Yakın" },
  { value: "newest", label: "En Yeni" },
  { value: "lowest_price", label: "En Düşük Fiyat" },
];

export default function CampaignsPage() {
  const [searchInput, setSearchInput] = useState("");
  const [debouncedSearch, setDebouncedSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState<StatusFilter>("all");
  const [sortBy, setSortBy] = useState<SortOption>("near_unlock");

  // Debounce search input 350 ms
  useEffect(() => {
    const id = setTimeout(() => setDebouncedSearch(searchInput), 350);
    return () => clearTimeout(id);
  }, [searchInput]);

  const { data: campaigns, isLoading, isError, refetch } = useCampaigns();

  const results = useMemo(() => {
    if (!campaigns) return [];
    const filtered = filterCampaigns(campaigns, {
      search: debouncedSearch,
      status: statusFilter,
    });
    return sortCampaigns(filtered, sortBy);
  }, [campaigns, debouncedSearch, statusFilter, sortBy]);

  return (
    <PageContainer>
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-900 mb-1">Kampanyalar</h1>
        <p className="text-sm text-gray-500">
          Aktif grup alımlarını keşfedin ve bekleme listesine katılın.
        </p>
      </div>

      {/* Filters */}
      <div className="flex flex-col gap-3 mb-8">
        {/* Search */}
        <div className="relative max-w-sm">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-400 pointer-events-none" />
          <Input
            placeholder="Kampanya ara..."
            value={searchInput}
            onChange={(e) => setSearchInput(e.target.value)}
            className="pl-9"
          />
        </div>

        {/* Status pills + sort */}
        <div className="flex flex-wrap items-center gap-2">
          <div className="flex flex-wrap gap-1.5">
            {STATUS_OPTIONS.map((opt) => (
              <button
                key={opt.value}
                onClick={() => setStatusFilter(opt.value)}
                className={cn(
                  "px-3 py-1 rounded-full text-xs font-medium border transition-colors",
                  statusFilter === opt.value
                    ? "bg-purple-600 text-white border-purple-600"
                    : "bg-white text-gray-600 border-gray-200 hover:border-gray-300 hover:bg-gray-50"
                )}
              >
                {opt.label}
              </button>
            ))}
          </div>

          <div className="flex-1" />

          <select
            value={sortBy}
            onChange={(e) => setSortBy(e.target.value as SortOption)}
            className="text-xs border border-gray-200 rounded-lg px-3 py-1.5 bg-white text-gray-700 hover:border-gray-300 focus:outline-none focus:ring-1 focus:ring-purple-500"
          >
            {SORT_OPTIONS.map((opt) => (
              <option key={opt.value} value={opt.value}>
                {opt.label}
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* Results */}
      {isLoading ? (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-5">
          {Array.from({ length: 6 }).map((_, i) => (
            <CampaignCardSkeleton key={i} />
          ))}
        </div>
      ) : isError ? (
        <ErrorState onRetry={() => refetch()} />
      ) : results.length === 0 ? (
        <EmptyState
          title="Kampanya bulunamadı"
          description={
            debouncedSearch || statusFilter !== "all"
              ? "Arama kriterlerinizi değiştirmeyi deneyin."
              : "Şu an aktif kampanya bulunmuyor."
          }
        />
      ) : (
        <>
          <p className="text-xs text-gray-400 mb-4">
            {results.length} kampanya
          </p>
          <CampaignGrid campaigns={results} />
        </>
      )}
    </PageContainer>
  );
}
