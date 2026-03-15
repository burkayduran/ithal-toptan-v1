import Link from "next/link";
import { ShoppingBag } from "lucide-react";

export default function Footer() {
  return (
    <footer className="border-t bg-gray-50 mt-auto">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
          <div>
            <Link href="/" className="flex items-center gap-2 font-bold text-lg text-gray-900 mb-3">
              <ShoppingBag className="h-5 w-5 text-blue-600" />
              İthal <span className="text-blue-600">Toptan</span>
            </Link>
            <p className="text-sm text-gray-500 leading-relaxed">
              MOQ bazlı grup alımıyla premium ürünleri toptan fiyatına alın.
            </p>
          </div>

          <div>
            <h4 className="font-semibold text-gray-900 mb-3 text-sm uppercase tracking-wide">Platform</h4>
            <ul className="space-y-2 text-sm text-gray-500">
              <li><Link href="/" className="hover:text-gray-700 transition-colors">Kampanyalar</Link></li>
              <li><Link href="/my-campaigns" className="hover:text-gray-700 transition-colors">Siparişlerim</Link></li>
            </ul>
          </div>

          <div>
            <h4 className="font-semibold text-gray-900 mb-3 text-sm uppercase tracking-wide">Nasıl Çalışır</h4>
            <ul className="space-y-2 text-sm text-gray-500">
              <li>Kampanyayı inceleyin</li>
              <li>Bekleme listesine katılın</li>
              <li>MOQ dolunca ödeme yapın</li>
            </ul>
          </div>
        </div>

        <div className="mt-10 pt-6 border-t text-center text-xs text-gray-400">
          © {new Date().getFullYear()} İthal Toptan. Tüm hakları saklıdır.
        </div>
      </div>
    </footer>
  );
}
