"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { Heart, Mail } from "lucide-react";

export default function Footer() {
  const pathname = usePathname();
  if (pathname.startsWith("/admin")) return null;
  return (
    <footer className="bg-gray-900 text-gray-300 mt-auto">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
          {/* Brand */}
          <div className="space-y-3">
            <Link href="/" className="flex items-center gap-2.5">
              <div className="w-9 h-9 bg-gradient-to-br from-indigo-500 to-purple-600 rounded-lg flex items-center justify-center">
                <Heart className="w-5 h-5 text-white" />
              </div>
              <span className="font-bold text-xl text-white">İthal Toptan</span>
            </Link>
            <div className="flex items-center gap-2 text-sm text-gray-400">
              <Mail className="w-4 h-4 flex-shrink-0" />
              <span>info@ithaltoptan.com</span>
            </div>
          </div>

          {/* Platform */}
          <div>
            <h4 className="font-semibold text-white mb-4">Platform</h4>
            <ul className="space-y-2 text-sm">
              <li>
                <Link href="/campaigns" className="hover:text-white transition-colors">
                  Tüm Kampanyalar
                </Link>
              </li>
              <li>
                <Link href="/my-campaigns" className="hover:text-white transition-colors">
                  Siparişlerim
                </Link>
              </li>
            </ul>
          </div>

          {/* Legal */}
          <div>
            <h4 className="font-semibold text-white mb-4">Yasal</h4>
            <ul className="space-y-2 text-sm">
              <li>
                <span className="text-gray-500 cursor-not-allowed">KVKK Aydınlatma Metni</span>
              </li>
              <li>
                <span className="text-gray-500 cursor-not-allowed">Mesafeli Satış Sözleşmesi</span>
              </li>
              <li>
                <span className="text-gray-500 cursor-not-allowed">İade ve İptal Politikası</span>
              </li>
              <li>
                <span className="text-gray-500 cursor-not-allowed">Kullanım Şartları</span>
              </li>
            </ul>
          </div>
        </div>

        <div className="mt-10 pt-8 border-t border-gray-800 text-sm text-center text-gray-500">
          © {new Date().getFullYear()} İthal Toptan. Tüm hakları saklıdır.
        </div>
      </div>
    </footer>
  );
}
