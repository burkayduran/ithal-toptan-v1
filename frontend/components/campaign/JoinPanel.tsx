"use client";

import { useState } from "react";
import { Campaign } from "@/features/campaigns/types";
import { useAuthStore } from "@/features/auth/store";
import { useJoinWishlist } from "@/features/wishlist/hooks";
import { Button } from "@/components/ui/button";
import WishlistQuantitySelector from "./WishlistQuantitySelector";
import WishlistSuccessNotice from "./WishlistSuccessNotice";
import ProgressBlock from "./ProgressBlock";
import { Loader2, ShoppingCart } from "lucide-react";

interface JoinPanelProps {
  campaign: Campaign;
}

export default function JoinPanel({ campaign }: JoinPanelProps) {
  const [quantity, setQuantity] = useState(1);
  const [joined, setJoined] = useState(false);
  const { user, openAuthModal } = useAuthStore();
  const { mutate: joinWishlist, isPending, error } = useJoinWishlist();

  const handleJoin = () => {
    if (!user) {
      // Defer join until after auth
      openAuthModal(() => {
        joinWishlist(
          { requestId: campaign.id, campaignSlug: campaign.slug, quantity },
          { onSuccess: () => setJoined(true) }
        );
      });
      return;
    }

    joinWishlist(
      { requestId: campaign.id, campaignSlug: campaign.slug, quantity },
      { onSuccess: () => setJoined(true) }
    );
  };

  if (joined) {
    return <WishlistSuccessNotice quantity={quantity} campaignTitle={campaign.title} />;
  }

  return (
    <div className="rounded-xl border border-gray-200 bg-white p-5 space-y-5">
      <ProgressBlock currentCount={campaign.currentCount} targetCount={campaign.targetCount} />

      {campaign.status === "active" ? (
        <>
          <WishlistQuantitySelector quantity={quantity} onChange={setQuantity} />

          {error && (
            <p className="text-sm text-red-600">
              {(error as Error).message || "Bir hata oluştu."}
            </p>
          )}

          <Button
            className="w-full gap-2"
            size="lg"
            onClick={handleJoin}
            disabled={isPending}
          >
            {isPending ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <ShoppingCart className="h-4 w-4" />
            )}
            {isPending ? "Kaydediliyor..." : "Bekleme Listesine Katıl"}
          </Button>

          <p className="text-xs text-gray-400 text-center">
            Ödeme yalnızca MOQ dolduğunda talep edilir.
          </p>
        </>
      ) : campaign.status === "moq_reached" ? (
        <div className="text-center py-3">
          <p className="font-semibold text-blue-700">Hedef doldu!</p>
          <p className="text-sm text-gray-500 mt-1">Ödeme bildirimi bekleniyor.</p>
        </div>
      ) : (
        <div className="text-center py-3">
          <p className="text-sm text-gray-500">Bu kampanya kapanmıştır.</p>
        </div>
      )}
    </div>
  );
}
