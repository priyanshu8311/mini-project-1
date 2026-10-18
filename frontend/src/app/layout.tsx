import type { Metadata } from "next";
import "./globals.css";
import { QueryProvider } from "@/components/providers/QueryProvider";
import { AuthProvider } from "@/hooks/useAuth";
import { AppShell } from "@/components/layout/AppShell";

export const metadata: Metadata = {
  title: "Smart Inventory Management & Demand Forecasting",
  description:
    "Enterprise SaaS for intelligent inventory control, multi-location stock tracking, and ML demand forecasting.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body className="antialiased font-sans">
        <QueryProvider>
          <AuthProvider>
            <AppShell>{children}</AppShell>
          </AuthProvider>
        </QueryProvider>
      </body>
    </html>
  );
}
