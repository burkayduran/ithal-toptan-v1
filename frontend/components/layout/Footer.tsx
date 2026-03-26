import Link from "next/link";
import { Heart, Mail } from "lucide-react";

export default function Footer() {
  return (
    <footer className="bg-gray-900 text-gray-300 mt-auto">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-8">
          {/* Brand */}
          <div className="space-y-4">
            <Link href="/" className="flex items-center gap-2.5">
              <div className="w-9 h-9 bg-gradient-to-br from-indigo-500 to-purple-600 rounded-lg flex items-center justify-center">
                <Heart className="w-5 h-5 text-white" />
              </div>
              <span className="font-bold text-xl text-white">
                İthal Toptan
              </span>
            </Link>
            <p className="text-sm leading-relaxed">
              MOQ bazlı grup alımıyla premium ürünleri toptan fiyatına alın.
              Birlikte al, birlikte kazan.
            </p>
          </div>

          {/* Platform */}
          <div>
            <h4 className="font-semibold text-white mb-4">Platform</h4>
            <ul className="space-y-2 text-sm">
              <li>
                <Link
                  href="/campaigns"
                  className="hover:text-white transition-colors"
                >
                  Tüm Kampanyalar
                </Link>
              </li>
              <li>
                <Link
                  href="/my-campaigns"
                  className="hover:text-white transition-colors"
                >
                  Siparişlerim
                </Link>
              </li>
            </ul>
          </div>

          {/* Nasıl Çalışır */}
          <div>
            <h4 className="font-semibold text-white mb-4">Nasıl Çalışır</h4>
            <ul className="space-y-2 text-sm">
              <li>Kampanyayı inceleyin</li>
              <li>Bekleme listesine katılın</li>
              <li>MOQ dolunca ödeme yapın</li>
            </ul>
          </div>

          {/* İletişim */}
          <div>
            <h4 className="font-semibold text-white mb-4">Bize Ulaşın</h4>
            <p className="text-sm mb-4">
              Yeni kampanyalar ve fırsatlardan haberdar olun.
            </p>
            <div className="flex items-center gap-2 text-sm text-gray-400">
              <Mail className="w-4 h-4" />
              <span>info@ithaltoptan.com</span>
            </div>
          </div>
        </div>

        <div className="mt-12 pt-8 border-t border-gray-800 text-sm text-center text-gray-500">
          © {new Date().getFullYear()} İthal Toptan. Tüm hakları saklıdır.
        </div>
      </div>
    </footer>
  );
}
