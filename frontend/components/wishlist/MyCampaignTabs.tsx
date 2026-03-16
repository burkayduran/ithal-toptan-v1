"use client";

import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { WishlistEntry } from "@/features/wishlist/types";
import MyCampaignCard from "./MyCampaignCard";
import EmptyState from "@/components/common/EmptyState";

interface TabDef {
  value: string;
  label: string;
  statuses: WishlistEntry["status"][];
  emptyTitle: string;
  emptyDescription: string;
}

const TABS: TabDef[] = [
  {
    value: "active",
    label: "Aktif",
    statuses: ["waiting"],
    emptyTitle: "Aktif kampanyanız yok",
    emptyDescription: "Bekleme listesine katıldığınız aktif kampanyalar burada görünür.",
  },
  {
    value: "payment",
    label: "Ödeme Gerekli",
    statuses: ["notified"],
    emptyTitle: "Ödeme bekleyen kampanya yok",
    emptyDescription: "MOQ'ya ulaşan ve ödeme bildirimi gelen kampanyalar burada görünür.",
  },
  {
    value: "paid",
    label: "Ödendi / İşlemde",
    statuses: ["paid"],
    emptyTitle: "İşlemde kampanya yok",
    emptyDescription: "Ödemesi tamamlanan kampanyalar burada takip edilir.",
  },
  {
    value: "closed",
    label: "Kapalı",
    statuses: ["expired", "cancelled"],
    emptyTitle: "Kapalı kampanya yok",
    emptyDescription: "Süresi dolan veya iptal edilen kayıtlar burada görünür.",
  },
];

interface MyCampaignTabsProps {
  entries: WishlistEntry[];
}

export default function MyCampaignTabs({ entries }: MyCampaignTabsProps) {
  return (
    <Tabs defaultValue="active" className="space-y-6">
      <TabsList className="grid w-full grid-cols-4">
        {TABS.map((tab) => {
          const count = entries.filter((e) =>
            (tab.statuses as string[]).includes(e.status)
          ).length;
          return (
            <TabsTrigger key={tab.value} value={tab.value} className="text-xs sm:text-sm gap-1.5">
              {tab.label}
              {count > 0 && (
                <span className="inline-flex items-center justify-center h-4 min-w-[1rem] px-1 rounded-full bg-blue-600 text-white text-[10px] font-bold leading-none">
                  {count}
                </span>
              )}
            </TabsTrigger>
          );
        })}
      </TabsList>

      {TABS.map((tab) => {
        const filtered = entries.filter((e) =>
          (tab.statuses as string[]).includes(e.status)
        );
        return (
          <TabsContent key={tab.value} value={tab.value}>
            {filtered.length === 0 ? (
              <EmptyState
                title={tab.emptyTitle}
                description={tab.emptyDescription}
                {...(tab.value === "active"
                  ? { actionLabel: "Kampanyaları İncele", actionHref: "/" }
                  : {})}
              />
            ) : (
              <div className="space-y-4">
                {filtered.map((entry) => (
                  <MyCampaignCard key={entry.id} entry={entry} />
                ))}
              </div>
            )}
          </TabsContent>
        );
      })}
    </Tabs>
  );
}
