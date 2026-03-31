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
  Users,
  ShieldAlert,
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
  {
    href: "/admin/demand-users",
    label: "Demand Users",
    icon: Users,
    exact: false,
  },
  {
    href: "/admin/fraud-watch",
    label: "Fraud Watch",
    icon: ShieldAlert,
    exact: false,
  },
];

export default function AdminSidebar() {
  const pathname = usePathname();

  return (
    <aside className="w-56 flex-shrink-0 bg-gray-900 text-white flex flex-col">
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
    </aside>
  );
}
