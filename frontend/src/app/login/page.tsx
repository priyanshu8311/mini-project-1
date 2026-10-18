"use client";

import React, { useState } from "react";
import Link from "next/link";
import { AlertCircle, Lock, Mail, ShieldCheck } from "lucide-react";
import { useAuth } from "@/hooks/useAuth";
import { Button } from "@/components/ui/Button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";

export default function LoginPage() {
  const { login, isLoading } = useAuth();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [formError, setFormError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setFormError(null);

    if (!email.trim() || !password) {
      setFormError("Please enter both email address and password.");
      return;
    }

    try {
      await login(email, password);
    } catch (err: unknown) {
      if (err instanceof Error) {
        setFormError(err.message);
      } else {
        setFormError("An unexpected error occurred during login.");
      }
    }
  };

  return (
    <div className="min-h-[80vh] flex items-center justify-center py-12 px-4 sm:px-6 lg:px-8">
      <div className="w-full max-w-md space-y-6">
        {/* Brand Header */}
        <div className="text-center space-y-2">
          <div className="inline-flex items-center justify-center w-12 h-12 rounded-xl bg-[#2563eb] text-white font-bold text-xl shadow-md">
            SI
          </div>
          <h1 className="text-2xl font-bold tracking-tight text-[#0f172a]">
            Sign in to SmartInventory
          </h1>
          <p className="text-sm text-[#64748b]">
            Enterprise Inventory Management & Demand Forecasting
          </p>
        </div>

        {/* Login Form Card */}
        <Card className="shadow-sm border-[#e2e8f0]">
          <CardHeader className="space-y-1">
            <CardTitle className="text-lg">Account Login</CardTitle>
            <CardDescription>
              Enter your corporate credentials to access your tenant workspace.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            {formError && (
              <div
                role="alert"
                aria-live="polite"
                className="p-3 rounded-[4px] bg-[#fef2f2] border border-[#fecaca] text-[#dc2626] text-xs flex items-start gap-2"
              >
                <AlertCircle className="w-4 h-4 shrink-0 mt-0.5" />
                <span className="leading-relaxed">{formError}</span>
              </div>
            )}

            <form onSubmit={handleSubmit} className="space-y-4">
              {/* Email Address */}
              <div className="space-y-1.5">
                <label
                  htmlFor="email"
                  className="block text-xs font-semibold text-[#0f172a]"
                >
                  Work Email <span className="text-[#dc2626]">*</span>
                </label>
                <div className="relative">
                  <Mail className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-[#94a3b8]" />
                  <input
                    id="email"
                    type="email"
                    autoComplete="email"
                    required
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    placeholder="name@company.com"
                    className="w-full h-10 pl-9 pr-3 text-sm bg-white border border-[#cbd5e1] rounded-[4px] text-[#0f172a] placeholder-[#94a3b8] focus:outline-none focus:border-[#2563eb] focus:ring-1 focus:ring-[#2563eb]"
                  />
                </div>
              </div>

              {/* Password */}
              <div className="space-y-1.5">
                <div className="flex items-center justify-between">
                  <label
                    htmlFor="password"
                    className="block text-xs font-semibold text-[#0f172a]"
                  >
                    Password <span className="text-[#dc2626]">*</span>
                  </label>
                  <Link
                    href="#"
                    className="text-xs text-[#2563eb] hover:underline focus:outline-none focus:ring-1 focus:ring-[#2563eb] rounded"
                  >
                    Forgot password?
                  </Link>
                </div>
                <div className="relative">
                  <Lock className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-[#94a3b8]" />
                  <input
                    id="password"
                    type="password"
                    autoComplete="current-password"
                    required
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    placeholder="••••••••"
                    className="w-full h-10 pl-9 pr-3 text-sm bg-white border border-[#cbd5e1] rounded-[4px] text-[#0f172a] placeholder-[#94a3b8] focus:outline-none focus:border-[#2563eb] focus:ring-1 focus:ring-[#2563eb]"
                  />
                </div>
              </div>

              {/* Submit Button */}
              <Button
                type="submit"
                variant="primary"
                size="md"
                isLoading={isLoading}
                className="w-full mt-2"
              >
                Sign In
              </Button>
            </form>

            <div className="text-center pt-2">
              <p className="text-xs text-[#64748b]">
                New organization?{" "}
                <Link
                  href="/signup"
                  className="text-[#2563eb] font-medium hover:underline focus:outline-none focus:ring-1 focus:ring-[#2563eb] rounded"
                >
                  Register your company workspace
                </Link>
              </p>
            </div>

            {/* Security Notice */}
            <div className="pt-2 border-t border-[#f1f5f9] flex items-center justify-between text-[11px] text-[#64748b]">
              <span className="flex items-center gap-1">
                <ShieldCheck className="w-3.5 h-3.5 text-[#16a34a]" />
                Tenant Data Isolated
              </span>
              <Badge variant="neutral">JWT • RBAC</Badge>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
