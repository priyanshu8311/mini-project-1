"use client";

import React, { useState, useRef, useEffect } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import {
  AlertTriangle,
  Bell,
  CheckCheck,
  CheckCircle2,
  ExternalLink,
  LogOut,
  Search,
  ShieldCheck,
  Trash2,
  TrendingUp,
  User,
} from "lucide-react";
import { useAuth } from "@/hooks/useAuth";

interface HeaderProps {
  onToggleSidebar?: () => void;
}

interface NotificationItem {
  id: string;
  type: "warning" | "info" | "success" | "system";
  title: string;
  message: string;
  time: string;
  read: boolean;
  link?: string;
}

const INITIAL_NOTIFICATIONS: NotificationItem[] = [
  {
    id: "notif-1",
    type: "warning",
    title: "Low Safety Stock Alert",
    message: "SKUs below minimum reorder threshold. Check replenishment orders.",
    time: "10m ago",
    read: false,
    link: "/inventory",
  },
  {
    id: "notif-2",
    type: "info",
    title: "Demand Forecast Ready",
    message: "Machine learning velocity pipeline computed 30-day projections.",
    time: "1h ago",
    read: false,
    link: "/forecasting",
  },
  {
    id: "notif-3",
    type: "success",
    title: "Multi-Tenant Workspace Active",
    message: "Ledger transaction auditing and RBAC policies are active.",
    time: "2h ago",
    read: false,
    link: "/",
  },
];

export function Header({ onToggleSidebar }: HeaderProps) {
  const { user, logout } = useAuth();
  const router = useRouter();
  const [notificationsOpen, setNotificationsOpen] = useState(false);
  const [notifications, setNotifications] = useState<NotificationItem[]>(INITIAL_NOTIFICATIONS);
  const dropdownRef = useRef<HTMLDivElement>(null);
  const bellButtonRef = useRef<HTMLButtonElement>(null);

  const unreadCount = notifications.filter((n) => !n.read).length;

  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (
        dropdownRef.current &&
        !dropdownRef.current.contains(event.target as Node) &&
        bellButtonRef.current &&
        !bellButtonRef.current.contains(event.target as Node)
      ) {
        setNotificationsOpen(false);
      }
    }

    function handleKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape") {
        setNotificationsOpen(false);
      }
    }

    if (notificationsOpen) {
      document.addEventListener("mousedown", handleClickOutside);
      document.addEventListener("keydown", handleKeyDown);
    }
    return () => {
      document.removeEventListener("mousedown", handleClickOutside);
      document.removeEventListener("keydown", handleKeyDown);
    };
  }, [notificationsOpen]);

  const markAllAsRead = () => {
    setNotifications((prev) => prev.map((n) => ({ ...n, read: true })));
  };

  const markOneAsRead = (id: string, link?: string) => {
    setNotifications((prev) =>
      prev.map((n) => (n.id === id ? { ...n, read: true } : n))
    );
    if (link) {
      setNotificationsOpen(false);
      router.push(link);
    }
  };

  const clearAll = () => {
    setNotifications([]);
  };

  const getNotificationIcon = (type: NotificationItem["type"]) => {
    switch (type) {
      case "warning":
        return <AlertTriangle className="w-4 h-4 text-[#d97706]" />;
      case "info":
        return <TrendingUp className="w-4 h-4 text-[#2563eb]" />;
      case "success":
        return <CheckCircle2 className="w-4 h-4 text-[#16a34a]" />;
      case "system":
      default:
        return <ShieldCheck className="w-4 h-4 text-[#475569]" />;
    }
  };

  const getNotificationBg = (type: NotificationItem["type"]) => {
    switch (type) {
      case "warning":
        return "bg-[#fef3c7] border-[#fde68a]";
      case "info":
        return "bg-[#eff6ff] border-[#bfdbfe]";
      case "success":
        return "bg-[#f0fdf4] border-[#bbf7d0]";
      case "system":
      default:
        return "bg-[#f1f5f9] border-[#e2e8f0]";
    }
  };

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
        {/* Notifications Popover */}
        <div className="relative">
          <button
            ref={bellButtonRef}
            type="button"
            onClick={() => setNotificationsOpen((prev) => !prev)}
            aria-label="View notifications"
            aria-expanded={notificationsOpen}
            aria-haspopup="dialog"
            className="relative p-2 rounded-full text-[#64748b] hover:bg-[#f1f5f9] hover:text-[#0f172a] focus:outline-none focus:ring-2 focus:ring-[#2563eb] transition-colors"
          >
            <Bell className="w-5 h-5" />
            {unreadCount > 0 && (
              <span className="absolute top-1.5 right-1.5 min-w-[16px] h-4 px-1 bg-[#dc2626] text-white text-[10px] font-bold rounded-full flex items-center justify-center ring-2 ring-white">
                {unreadCount}
              </span>
            )}
          </button>

          {notificationsOpen && (
            <div
              ref={dropdownRef}
              role="dialog"
              aria-label="Notifications panel"
              className="absolute right-0 top-full mt-2 w-80 sm:w-96 rounded-lg bg-white border border-[#e2e8f0] shadow-xl z-50 overflow-hidden animate-in fade-in zoom-in-95 duration-150"
            >
              {/* Header */}
              <div className="flex items-center justify-between px-4 py-3 border-b border-[#f1f5f9] bg-[#f8fafc]">
                <div className="flex items-center gap-2">
                  <span className="font-semibold text-sm text-[#0f172a]">Notifications</span>
                  {unreadCount > 0 && (
                    <span className="px-2 py-0.5 rounded-full text-[11px] font-medium bg-[#dbeafe] text-[#1d4ed8]">
                      {unreadCount} new
                    </span>
                  )}
                </div>
                <div className="flex items-center gap-2 text-xs">
                  {unreadCount > 0 && (
                    <button
                      type="button"
                      onClick={markAllAsRead}
                      className="text-[#2563eb] hover:underline flex items-center gap-1 font-medium"
                      title="Mark all as read"
                    >
                      <CheckCheck className="w-3.5 h-3.5" />
                      Mark all read
                    </button>
                  )}
                  {notifications.length > 0 && (
                    <button
                      type="button"
                      onClick={clearAll}
                      className="text-[#64748b] hover:text-[#dc2626] p-1 rounded"
                      title="Clear notifications"
                      aria-label="Clear all notifications"
                    >
                      <Trash2 className="w-3.5 h-3.5" />
                    </button>
                  )}
                </div>
              </div>

              {/* Notification List */}
              <div className="max-h-[380px] overflow-y-auto divide-y divide-[#f1f5f9]">
                {notifications.length === 0 ? (
                  <div className="p-8 text-center space-y-2">
                    <CheckCircle2 className="w-8 h-8 text-[#16a34a] mx-auto opacity-70" />
                    <p className="text-sm font-medium text-[#0f172a]">All caught up!</p>
                    <p className="text-xs text-[#64748b]">
                      No active alerts or stock warnings across your tenant locations.
                    </p>
                  </div>
                ) : (
                  notifications.map((item) => (
                    <div
                      key={item.id}
                      onClick={() => markOneAsRead(item.id, item.link)}
                      className={`p-3.5 flex items-start gap-3 transition-colors cursor-pointer hover:bg-[#f8fafc] ${
                        !item.read ? "bg-[#f8fafc]/60" : "bg-white"
                      }`}
                    >
                      <div
                        className={`w-7 h-7 rounded-lg border flex items-center justify-center shrink-0 mt-0.5 ${getNotificationBg(
                          item.type
                        )}`}
                      >
                        {getNotificationIcon(item.type)}
                      </div>
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center justify-between gap-1">
                          <p
                            className={`text-xs truncate ${
                              !item.read
                                ? "font-semibold text-[#0f172a]"
                                : "font-medium text-[#334155]"
                            }`}
                          >
                            {item.title}
                          </p>
                          <span className="text-[10px] text-[#94a3b8] shrink-0">
                            {item.time}
                          </span>
                        </div>
                        <p className="text-[11px] text-[#64748b] line-clamp-2 mt-0.5 leading-relaxed">
                          {item.message}
                        </p>
                        {item.link && (
                          <span className="inline-flex items-center gap-1 text-[11px] font-medium text-[#2563eb] hover:underline mt-1.5">
                            View details
                            <ExternalLink className="w-3 h-3" />
                          </span>
                        )}
                      </div>
                      {!item.read && (
                        <span className="w-2 h-2 rounded-full bg-[#2563eb] shrink-0 mt-2" />
                      )}
                    </div>
                  ))
                )}
              </div>

              {/* Footer */}
              <div className="p-2.5 bg-[#f8fafc] border-t border-[#f1f5f9] text-center">
                <Link
                  href="/inventory"
                  onClick={() => setNotificationsOpen(false)}
                  className="text-xs font-medium text-[#2563eb] hover:underline inline-flex items-center gap-1"
                >
                  View Inventory Health & Stock Levels →
                </Link>
              </div>
            </div>
          )}
        </div>

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

