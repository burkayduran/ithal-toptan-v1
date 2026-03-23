"use client";

import { useState } from "react";
import Link from "next/link";
import { Campaign } from "@/features/campaigns/types";
import { Participant } from "@/features/wishlist/types";
import { useAuthStore } from "@/features/auth/store";
import { useJoinCampaign } from "@/features/wishlist/hooks";
import { Button } from "@/components/ui/button";
import ProgressBlock from "./ProgressBlock";
import CountdownBlock from "./CountdownBlock";
import StateNoticeBanner from "./StateNoticeBanner";
import WishlistQuantitySelector from "./WishlistQuantitySelector";
import WishlistSuccessNotice from "./WishlistSuccessNotice";
import { Loader2, ShoppingCart, CreditCard, CheckCircle2 } from "lucide-react";

interface JoinPanelProps {
  campaign: Campaign;
  /** Current user's participant entry for this campaign, if any */
  participant?: Participant | null;
}

export default function JoinPanel({ campaign, participant }: JoinPanelProps) {
  const [quantity, setQuantity] = useState(1);
  const [justJoined, setJustJoined] = useState(false);
  const { user, openAuthModal } = useAuthStore();
  const { mutate: joinCampaign, isPending, error } = useJoinCampaign();

  const canShowProgress =
    campaign.moq != null && campaign.current_participant_count != null;

  // ── If user just joined in this session ──────────────────────────────────
  if (justJoined) {
    return <WishlistSuccessNotice quantity={quantity} campaignTitle={campaign.title} />;
  }

  // ── Already has an invited entry → show payment CTA ──────────────────────
  if (participant?.status === "invited") {
    return (
      <div className="rounded-xl border border-amber-200 bg-amber-50 p-5 space-y-4">
        {canShowProgress && (
          <ProgressBlock
            currentCount={campaign.current_participant_count!}
            targetCount={campaign.moq!}
          />
        )}
        <StateNoticeBanner
          type="warning"
          title="Ödeme bildirimi aldınız"
          message="Hedef sayıya ulaşıldı. Yerinizi onaylamak için ödemeyi tamamlayın."
        />
        {participant.payment_deadline && (
          <div className="space-y-1">
            <p className="text-xs text-gray-500 font-medium">Kalan süre</p>
            <CountdownBlock deadline={participant.payment_deadline} />
          </div>
        )}
        <Link href={`/payment/${participant.id}`}>
          <Button className="w-full gap-2 bg-amber-600 hover:bg-amber-700" size="lg">
            <CreditCard className="h-4 w-4" />
            Ödemeyi Tamamla
          </Button>
        </Link>
      </div>
    );
  }

  // ── Already paid → show confirmation ─────────────────────────────────────
  if (participant?.status === "paid") {
    return (
      <div className="rounded-xl border border-green-200 bg-green-50 p-5 space-y-3">
        <div className="flex items-center gap-2 text-green-700">
          <CheckCircle2 className="h-5 w-5" />
          <p className="font-semibold">Ödeme tamamlandı</p>
        </div>
        <p className="text-sm text-green-600">
          Siparişiniz işleme alındı. Kargo güncellemelerini durum sayfasından takip edebilirsiniz.
        </p>
        <Link href={`/status/${participant.id}`}>
          <Button variant="outline" className="w-full border-green-300 text-green-700 hover:bg-green-100">
            Siparişimi Takip Et →
          </Button>
        </Link>
      </div>
    );
  }

  // ── Entry expired → show recovery message ────────────────────────────────
  if (participant?.status === "expired") {
    return (
      <div className="rounded-xl border border-red-200 bg-red-50 p-5 space-y-3">
        <StateNoticeBanner
          type="error"
          title="Ödeme süreniz doldu"
          message="Bu tur için ödeme pencereniz kapandı. Kampanya sıfırlanırsa yeniden katılabilirsiniz."
        />
        <Link href={`/campaigns/${campaign.id}`}>
          <Button variant="outline" className="w-full border-red-300 text-red-600 hover:bg-red-100">
            Kampanyayı İzle
          </Button>
        </Link>
      </div>
    );
  }

  // ── Backend accepts joins for active + moq_reached ────────────────────────
  const canJoin = campaign.status === "active" || campaign.status === "moq_reached";

  // ── Already in queue (joined) while campaign still active ───────────────
  if (participant?.status === "joined" && canJoin) {
    return (
      <div className="rounded-xl border border-blue-200 bg-blue-50 p-5 space-y-4">
        {canShowProgress && (
          <ProgressBlock
            currentCount={campaign.current_participant_count!}
            targetCount={campaign.moq!}
          />
        )}
        <StateNoticeBanner
          type="info"
          message="Bekleme listesine eklendiniz. Hedef dolduğunda ödeme bildirimi alacaksınız."
        />
        <Link href="/my-campaigns">
          <Button variant="outline" className="w-full">
            Siparişlerime Git →
          </Button>
        </Link>
      </div>
    );
  }

  // ── Join UI (no participant yet, or participant is cancelled) ─────────────
  const handleJoin = () => {
    if (!user) {
      openAuthModal(() => {
        joinCampaign(
          { campaignId: campaign.id, quantity },
          { onSuccess: () => setJustJoined(true) }
        );
      });
      return;
    }
    joinCampaign(
      { campaignId: campaign.id, quantity },
      { onSuccess: () => setJustJoined(true) }
    );
  };

  return (
    <div className="rounded-xl border border-gray-200 bg-white p-5 space-y-5">
      {canShowProgress && (
        <ProgressBlock
          currentCount={campaign.current_participant_count!}
          targetCount={campaign.moq!}
        />
      )}

      {canJoin ? (
        <>
          {campaign.status === "moq_reached" && (
            <StateNoticeBanner
              type="info"
              title="Hedef doldu!"
              message="Katılırsanız ödeme bildirimi alırsınız."
            />
          )}

          <WishlistQuantitySelector quantity={quantity} onChange={setQuantity} />

          {error && (
            <p className="text-sm text-red-600 bg-red-50 rounded-md px-3 py-2">
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
            {isPending
              ? "Kaydediliyor..."
              : campaign.status === "moq_reached"
              ? "Bekleme Listesine Katıl"
              : "Bekleme Listesine Katıl"}
          </Button>

          <p className="text-xs text-gray-400 text-center">
            {campaign.status === "moq_reached"
              ? "Hedef dolduğunda ödeme bildirimi alacaksınız."
              : "Yeterli talep oluştuğunda ödeme bildirimi alacaksınız."}
          </p>
        </>
      ) : campaign.status === "payment_collecting" ? (
        <StateNoticeBanner
          type="warning"
          title="Ödeme toplanıyor"
          message="Bu kampanya için ödeme süreci başlamıştır. Yeni katılım alınmıyor."
        />
      ) : campaign.status === "ordered" ? (
        <div className="text-center py-4 space-y-1">
          <p className="font-semibold text-purple-700">Sipariş verildi</p>
          <p className="text-sm text-gray-500">Ürün tedarik aşamasında.</p>
        </div>
      ) : campaign.status === "delivered" ? (
        <div className="text-center py-4">
          <p className="font-semibold text-gray-700">Teslim edildi</p>
        </div>
      ) : campaign.status === "cancelled" ? (
        <div className="text-center py-4">
          <p className="font-semibold text-red-600">Kampanya iptal edildi</p>
        </div>
      ) : (
        <div className="text-center py-4">
          <p className="text-sm text-gray-500">Bu kampanya şu an aktif değil.</p>
        </div>
      )}
    </div>
  );
}
