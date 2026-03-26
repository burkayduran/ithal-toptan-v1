import { MessageCircle, Mail } from "lucide-react";
import { Button } from "@/components/ui/button";

interface SupportBlockProps {
  /** Optional compact variant for use inside cards */
  compact?: boolean;
}

export default function SupportBlock({ compact = false }: SupportBlockProps) {
  if (compact) {
    return (
      <p className="text-xs text-gray-400">
        Sorun mu yaşıyorsunuz?{" "}
        <a
          href="mailto:destek@ithaltoptan.com"
          className="text-blue-600 underline hover:text-blue-700"
        >
          Bize yazın
        </a>
      </p>
    );
  }

  return (
    <div className="rounded-xl border border-gray-200 bg-white p-5 space-y-3">
      <p className="font-semibold text-gray-900 text-sm">Yardıma mı ihtiyacınız var?</p>
      <p className="text-sm text-gray-500">
        Siparişinizle ilgili sorularınız için destek ekibimize ulaşabilirsiniz.
      </p>
      <div className="flex flex-wrap gap-2">
        <a href="mailto:destek@ithaltoptan.com">
          <Button variant="outline" size="sm" className="gap-1.5">
            <Mail className="h-3.5 w-3.5" />
            E-posta Gönder
          </Button>
        </a>
        <a href="https://wa.me/905000000000" target="_blank" rel="noopener noreferrer">
          <Button variant="outline" size="sm" className="gap-1.5">
            <MessageCircle className="h-3.5 w-3.5" />
            WhatsApp
          </Button>
        </a>
      </div>
    </div>
  );
}
