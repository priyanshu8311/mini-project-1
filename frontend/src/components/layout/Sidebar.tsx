"use client";

import React from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  LayoutDashboard,
  Package,
  TrendingUp,
  ShoppingCart,
  Settings,
  Users,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { useAuth } from "@/hooks/useAuth";

interface SidebarProps {
  isOpen?: boolean;
  onClose?: () => void;
}

const BASE_NAV_ITEMS = [
  { name: "Dashboard", href: "/", icon: LayoutDashboard },
  { name: "Inventory", href: "/inventory", icon: Package },
  { name: "Demand Forecasting", href: "/forecasting", icon: TrendingUp },
  { name: "Replenishment & POs", href: "/purchasing", icon: ShoppingCart },
  { name: "Settings", href: "/settings", icon: Settings },
];

export function Sidebar({ isOpen, onClose }: SidebarProps) {
  const pathname = usePathname();
  const { isAdmin } = useAuth();

  const navItems = isAdmin
    ? [
        ...BASE_NAV_ITEMS.slice(0, 4),
        { name: "Team & Roles", href: "/settings/users", icon: Users },
        ...BASE_NAV_ITEMS.slice(4),
      ]
    : BASE_NAV_ITEMS;

  return (
    <>
      {/* Mobile Backdrop */}
      {isOpen && (
        <div
          onClick={onClose}
          className="fixed inset-0 bg-black/40 z-40 md:hidden"
          aria-hidden="true"
        />
      )}

      {/* Sidebar Panel */}
      <aside
        className={cn(
          "w-[240px] bg-white border-r border-[#e2e8f0] flex flex-col fixed inset-y-0 left-0 z-40 pt-[60px] transition-transform duration-200 ease-in-out md:translate-x-0",
          isOpen ? "translate-x-0" : "-translate-x-full md:translate-x-0"
        )}
      >
        <div className="p-4 flex-1 flex flex-col gap-1 overflow-y-auto">
          <div className="text-[11px] font-semibold uppercase tracking-wider text-[#94a3b8] px-3 mb-2">
            Main Navigation
          </div>

          {navItems.map((item) => {
            const Icon = item.icon;
            const isActive =
              item.href === "/"
                ? pathname === "/"
                : pathname.startsWith(item.href);

            return (
              <Link
                key={item.href}
                href={item.href}
                onClick={onClose}
                className={cn(
                  "flex items-center gap-3 px-3 py-2.5 rounded-[4px] text-sm font-medium transition-colors select-none focus:outline-none focus:ring-2 focus:ring-[#2563eb]",
                  isActive
                    ? "bg-[#eff6ff] text-[#2563eb] font-semibold"
                    : "text-[#475569] hover:bg-[#f8fafc] hover:text-[#0f172a]"
                )}
              >
                <Icon
                  className={cn(
                    "w-4 h-4 shrink-0",
                    isActive ? "text-[#2563eb]" : "text-[#64748b]"
                  )}
                />
                <span>{item.name}</span>
              </Link>
            );
          })}
        </div>

        {/* Footer info adhering to DESIGN.md subtle footer */}
        <div className="p-4 border-t border-[#f1f5f9] text-[11px] text-[#94a3b8]">
          <p>Smart Inventory v0.1.0</p>
          <p className="text-[10px] text-[#cbd5e1]">PostgreSQL • FastAPI • Next.js</p>
        </div>
      </aside>
    </>
  );
}
