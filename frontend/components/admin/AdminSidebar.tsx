"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/utils";
import {
  LayoutDashboard,
  Package,
  Tags,
  ClipboardList,
  ChevronRight,
} from "lucide-react";

const NAV = [
  { href: "/admin", label: "Dashboard", icon: LayoutDashboard, exact: true },
  { href: "/admin/products", label: "Ürünler", icon: Package, exact: false },
  { href: "/admin/categories", label: "Kategoriler", icon: Tags, exact: false },
  {
    href: "/admin/product-requests",
    label: "Ürün İstekleri",
    icon: ClipboardList,
    exact: false,
  },
];

export default function AdminSidebar() {
  const pathname = usePathname();

  return (
    <aside className="w-56 flex-shrink-0 bg-gray-900 text-white flex flex-col">
      {/* Brand */}
      <div className="px-4 py-4 border-b border-gray-700">
        <p className="text-xs font-bold uppercase tracking-widest text-gray-400">
          Admin Panel
        </p>
      </div>

      {/* Nav */}
      <nav className="flex-1 py-3 space-y-0.5 px-2">
        {NAV.map(({ href, label, icon: Icon, exact }) => {
          const active = exact ? pathname === href : pathname.startsWith(href);
          return (
            <Link
              key={href}
              href={href}
              className={cn(
                "flex items-center gap-2.5 px-3 py-2 rounded-lg text-sm font-medium transition-colors",
                active
                  ? "bg-blue-600 text-white"
                  : "text-gray-300 hover:bg-gray-800 hover:text-white"
              )}
            >
              <Icon className="h-4 w-4 flex-shrink-0" />
              <span className="flex-1">{label}</span>
              {active && <ChevronRight className="h-3 w-3 opacity-60" />}
            </Link>
          );
        })}
      </nav>

      {/* Back to site */}
      <div className="px-4 py-3 border-t border-gray-700">
        <Link
          href="/"
          className="text-xs text-gray-400 hover:text-gray-200 transition-colors"
        >
          ← Siteye dön
        </Link>
      </div>
    </aside>
  );
}
