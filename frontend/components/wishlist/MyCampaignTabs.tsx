"use client";

import { useState } from "react";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Participant } from "@/features/wishlist/types";
import MyCampaignCard from "./MyCampaignCard";
import EmptyState from "@/components/common/EmptyState";

interface TabDef {
  value: string;
  label: string;
  statuses: Participant["status"][];
  emptyTitle: string;
  emptyDescription: string;
}

const TABS: TabDef[] = [
  {
    value: "active",
    label: "Aktif",
    statuses: ["joined"],
    emptyTitle: "Aktif kampanyanız yok",
    emptyDescription: "Bekleme listesine katıldığınız aktif kampanyalar burada görünür.",
  },
  {
    value: "payment",
    label: "Ödeme Gerekli",
    statuses: ["invited"],
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

/**
 * Priority order for smart default tab selection.
 * "payment" (notified) is shown first because it requires immediate user action.
 */
const DEFAULT_TAB_PRIORITY = ["payment", "active", "paid", "closed"] as const;

function getInitialTab(participants: Participant[]): string {
  for (const tabValue of DEFAULT_TAB_PRIORITY) {
    const tab = TABS.find((t) => t.value === tabValue);
    if (tab && participants.some((p) => (tab.statuses as string[]).includes(p.status))) {
      return tabValue;
    }
  }
  return "active";
}

interface MyCampaignTabsProps {
  participants: Participant[];
}

export default function MyCampaignTabs({ participants }: MyCampaignTabsProps) {
  // Computed once at mount — the tab with the most urgent / populated state opens first
  const [currentTab, setCurrentTab] = useState<string>(() => getInitialTab(participants));

  return (
    <Tabs value={currentTab} onValueChange={setCurrentTab} className="space-y-6">
      <TabsList className="grid w-full grid-cols-4">
        {TABS.map((tab) => {
          const count = participants.filter((p) =>
            (tab.statuses as string[]).includes(p.status)
          ).length;
          return (
            <TabsTrigger
              key={tab.value}
              value={tab.value}
              className="text-xs sm:text-sm gap-1.5"
            >
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
        const filtered = participants.filter((p) =>
          (tab.statuses as string[]).includes(p.status)
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
                {filtered.map((participant) => (
                  <MyCampaignCard key={participant.id} participant={participant} />
                ))}
              </div>
            )}
          </TabsContent>
        );
      })}
    </Tabs>
  );
}
