import React from "react";
import { cn } from "@/lib/utils";

export interface SkeletonProps extends React.HTMLAttributes<HTMLDivElement> {
  variant?: "rectangular" | "circular" | "rounded";
}

export function Skeleton({
  className,
  variant = "rounded",
  ...props
}: SkeletonProps) {
  const variantStyles = {
    rectangular: "rounded-none",
    circular: "rounded-full",
    rounded: "rounded-md",
  };

  return (
    <div
      className={cn(
        "animate-pulse bg-[#e2e8f0]/80",
        variantStyles[variant],
        className
      )}
      aria-hidden="true"
      {...props}
    />
  );
}
