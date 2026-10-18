import React from "react";
import { cn } from "@/lib/utils";

export interface BadgeProps extends React.HTMLAttributes<HTMLSpanElement> {
  variant?: "success" | "warning" | "error" | "info" | "neutral";
  icon?: React.ReactNode;
}

export function Badge({
  className,
  variant = "neutral",
  icon,
  children,
  ...props
}: BadgeProps) {
  const variantStyles = {
    success: "bg-[#f0fdf4] text-[#16a34a] border-[#bbf7d0]",
    warning: "bg-[#fffbeb] text-[#d97706] border-[#fde68a]",
    error: "bg-[#fef2f2] text-[#dc2626] border-[#fecaca]",
    info: "bg-[#f0f9ff] text-[#0284c7] border-[#bae6fd]",
    neutral: "bg-[#f8fafc] text-[#475569] border-[#e2e8f0]",
  };

  return (
    <span
      className={cn(
        "inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-medium border select-none",
        variantStyles[variant],
        className
      )}
      {...props}
    >
      {icon && <span className="inline-block shrink-0">{icon}</span>}
      {children}
    </span>
  );
}
