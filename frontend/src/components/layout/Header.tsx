"use client";

import React from "react";
import Link from "next/link";
import { Bell, LogOut, Search, User } from "lucide-react";
import { useAuth } from "@/hooks/useAuth";

interface HeaderProps {
  onToggleSidebar?: () => void;
}

export function Header({ onToggleSidebar }: HeaderProps) {
  const { user, logout } = useAuth();

  return (
    <header className="h-[60px] bg-white border-b border-[#e2e8f0] px-4 md:px-6 flex items-center justify-between sticky top-0 z-30">
      <div className="flex items-center gap-3">
        <button
          type="button"
          onClick={onToggleSidebar}
          aria-label="Toggle navigation menu"
          className="md:hidden p-2 rounded text-[#64748b] hover:bg-[#f1f5f9] hover:text-[#0f172a] focus:outline-none focus:ring-2 focus:ring-[#2563eb]"
        >
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
          </svg>
        </button>

        <Link href="/" className="flex items-center gap-2">
          <div className="w-8 h-8 rounded bg-[#2563eb] text-white flex items-center justify-center font-bold text-sm">
            SI
          </div>
          <span className="font-semibold text-base text-[#0f172a] hidden sm:inline">
            SmartInventory
          </span>
        </Link>
      </div>

      {/* Global Search Bar */}
      <div className="flex-1 max-w-md mx-4 hidden md:block">
        <div className="relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-[#94a3b8]" />
          <input
            type="search"
            placeholder="Search SKU, item name, or category..."
            className="w-full h-9 pl-9 pr-4 text-sm bg-[#f8fafc] border border-[#cbd5e1] rounded-[4px] focus:outline-none focus:border-[#2563eb] focus:bg-white text-[#0f172a] placeholder-[#94a3b8]"
          />
        </div>
      </div>

      {/* Quick Actions & User Area */}
      <div className="flex items-center gap-2 sm:gap-4">
        <button
          type="button"
          aria-label="View notifications"
          className="relative p-2 rounded-full text-[#64748b] hover:bg-[#f1f5f9] hover:text-[#0f172a] focus:outline-none focus:ring-2 focus:ring-[#2563eb]"
        >
          <Bell className="w-5 h-5" />
          <span className="absolute top-1.5 right-1.5 w-2 h-2 bg-[#dc2626] rounded-full" />
        </button>

        <div className="h-6 w-px bg-[#e2e8f0]" />

        {user ? (
          <div className="flex items-center gap-2 sm:gap-3">
            <div className="flex items-center gap-2">
              <div className="w-8 h-8 rounded-full bg-[#f1f5f9] border border-[#cbd5e1] flex items-center justify-center text-[#475569]">
                <User className="w-4 h-4" />
              </div>
              <div className="hidden lg:flex flex-col text-left">
                <span className="text-xs font-semibold text-[#0f172a] truncate max-w-[140px]">
                  {user.email}
                </span>
                <span className="text-[10px] text-[#2563eb] font-medium">
                  {user.role}
                </span>
              </div>
            </div>

            <button
              type="button"
              onClick={logout}
              title="Sign Out"
              aria-label="Sign Out"
              className="p-1.5 rounded text-[#64748b] hover:bg-[#fef2f2] hover:text-[#dc2626] transition-colors focus:outline-none focus:ring-2 focus:ring-[#dc2626]"
            >
              <LogOut className="w-4 h-4" />
            </button>
          </div>
        ) : (
          <Link
            href="/login"
            className="inline-flex items-center justify-center h-8 px-3 text-xs font-medium rounded-[4px] bg-[#2563eb] text-white hover:bg-[#1d4ed8] transition-colors focus:outline-none focus:ring-2 focus:ring-[#2563eb]"
          >
            Sign In
          </Link>
        )}
      </div>
    </header>
  );
}
