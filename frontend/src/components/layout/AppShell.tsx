"use client";

import React, { useState, useEffect } from "react";
import { usePathname, useRouter } from "next/navigation";
import { useAuth } from "@/hooks/useAuth";
import { Header } from "./Header";
import { Sidebar } from "./Sidebar";
import { Loader2 } from "lucide-react";

export function AppShell({ children }: { children: React.ReactNode }) {
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const pathname = usePathname();
  const router = useRouter();
  const { user, isLoading, isAuthenticated } = useAuth();

  const isAuthPage = pathname === "/login" || pathname === "/signup";

  useEffect(() => {
    if (isLoading) return;

    if (isAuthenticated && isAuthPage) {
      router.replace("/");
    } else if (!isAuthenticated && !isAuthPage) {
      router.replace(`/login?redirect=${encodeURIComponent(pathname)}`);
    }
  }, [isAuthenticated, isAuthPage, isLoading, pathname, router]);

  // Auth pages (login, signup) render without the sidebar
  if (isAuthPage) {
    return (
      <div className="min-h-screen flex flex-col bg-[#f8fafc]">
        <Header onToggleSidebar={() => {}} />
        <main className="flex-1 flex flex-col items-center justify-center p-4">
          {children}
        </main>
      </div>
    );
  }

  // Loading state while verifying token
  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-[#f8fafc]">
        <div className="flex flex-col items-center gap-3">
          <Loader2 className="w-8 h-8 text-[#2563eb] animate-spin" />
          <p className="text-xs text-[#64748b]">Verifying corporate credentials...</p>
        </div>
      </div>
    );
  }

  // Not authenticated and not on auth page (during redirect transition)
  if (!user) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-[#f8fafc]">
        <div className="flex flex-col items-center gap-3">
          <Loader2 className="w-8 h-8 text-[#2563eb] animate-spin" />
          <p className="text-xs text-[#64748b]">Redirecting to authentication portal...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen flex flex-col bg-[#f8fafc]">
      <Header onToggleSidebar={() => setSidebarOpen((prev) => !prev)} />
      <div className="flex flex-1">
        <Sidebar isOpen={sidebarOpen} onClose={() => setSidebarOpen(false)} />
        <main className="flex-1 md:pl-[240px] flex flex-col">
          <div className="flex-1 w-full max-w-[1200px] mx-auto p-4 md:p-6">
            {children}
          </div>
        </main>
      </div>
    </div>
  );
}

