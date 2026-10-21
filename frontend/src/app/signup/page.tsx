"use client";

import React, { useState } from "react";
import Link from "next/link";
import {
  AlertCircle,
  Building2,
  CheckCircle2,
  Lock,
  Mail,
  ShieldCheck,
  XCircle,
} from "lucide-react";
import { useAuth } from "@/hooks/useAuth";
import { Button } from "@/components/ui/Button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";

export default function SignupPage() {
  const { register, isLoading } = useAuth();
  const [organizationName, setOrganizationName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [formError, setFormError] = useState<string | null>(null);

  // Real-time password criteria verification
  const hasMinLength = password.length >= 8;
  const hasUppercase = /[A-Z]/.test(password);
  const hasLowercase = /[a-z]/.test(password);
  const hasDigitOrSpecial = /[\d\W_]/.test(password);
  const isPasswordValid =
    hasMinLength && hasUppercase && hasLowercase && hasDigitOrSpecial;
  const passwordsMatch = password.length > 0 && password === confirmPassword;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setFormError(null);

    if (!organizationName.trim()) {
      setFormError("Please enter your company or organization name.");
      return;
    }

    if (!email.trim()) {
      setFormError("Please enter your work email address.");
      return;
    }

    if (!isPasswordValid) {
      setFormError(
        "Password must be at least 8 characters and include uppercase, lowercase, and a number or symbol."
      );
      return;
    }

    if (password !== confirmPassword) {
      setFormError("Passwords do not match. Please re-enter to confirm.");
      return;
    }

    try {
      await register(organizationName.trim(), email.trim(), password);
    } catch (err: unknown) {
      if (err instanceof Error) {
        setFormError(err.message);
      } else {
        setFormError("An unexpected error occurred during registration.");
      }
    }
  };

  return (
    <div className="w-full min-h-[85vh] flex items-center justify-center py-10 px-4 sm:px-6 lg:px-8">
      <div className="w-full max-w-md space-y-6">
        {/* Brand Header */}
        <div className="text-center space-y-2">
          <div className="inline-flex items-center justify-center w-12 h-12 rounded-xl bg-[#2563eb] text-white font-bold text-xl shadow-md">
            SI
          </div>
          <h1 className="text-2xl font-bold tracking-tight text-[#0f172a]">
            Create Organization Workspace
          </h1>
          <p className="text-sm text-[#64748b]">
            Get started with AI-driven inventory control and demand forecasting
          </p>
        </div>

        {/* Signup Form Card */}
        <Card className="shadow-sm border-[#e2e8f0]">
          <CardHeader className="space-y-1">
            <CardTitle className="text-lg">Register Tenant Organization</CardTitle>
            <CardDescription>
              Create your company account. You will be assigned the initial Admin role.
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
              {/* Organization Name */}
              <div className="space-y-1.5">
                <label
                  htmlFor="orgName"
                  className="block text-xs font-semibold text-[#0f172a]"
                >
                  Organization / Company Name <span className="text-[#dc2626]">*</span>
                </label>
                <div className="relative">
                  <Building2 className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-[#94a3b8]" />
                  <input
                    id="orgName"
                    type="text"
                    required
                    value={organizationName}
                    onChange={(e) => setOrganizationName(e.target.value)}
                    placeholder="Acme Distribution Corp"
                    className="w-full h-10 pl-9 pr-3 text-sm bg-white border border-[#cbd5e1] rounded-[4px] text-[#0f172a] placeholder-[#94a3b8] focus:outline-none focus:border-[#2563eb] focus:ring-1 focus:ring-[#2563eb]"
                  />
                </div>
              </div>

              {/* Work Email */}
              <div className="space-y-1.5">
                <label
                  htmlFor="signupEmail"
                  className="block text-xs font-semibold text-[#0f172a]"
                >
                  Admin Work Email <span className="text-[#dc2626]">*</span>
                </label>
                <div className="relative">
                  <Mail className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-[#94a3b8]" />
                  <input
                    id="signupEmail"
                    type="email"
                    autoComplete="email"
                    required
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    placeholder="admin@company.com"
                    className="w-full h-10 pl-9 pr-3 text-sm bg-white border border-[#cbd5e1] rounded-[4px] text-[#0f172a] placeholder-[#94a3b8] focus:outline-none focus:border-[#2563eb] focus:ring-1 focus:ring-[#2563eb]"
                  />
                </div>
              </div>

              {/* Password */}
              <div className="space-y-1.5">
                <label
                  htmlFor="signupPassword"
                  className="block text-xs font-semibold text-[#0f172a]"
                >
                  Admin Password <span className="text-[#dc2626]">*</span>
                </label>
                <div className="relative">
                  <Lock className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-[#94a3b8]" />
                  <input
                    id="signupPassword"
                    type="password"
                    autoComplete="new-password"
                    required
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    placeholder="••••••••••••"
                    className="w-full h-10 pl-9 pr-3 text-sm bg-white border border-[#cbd5e1] rounded-[4px] text-[#0f172a] placeholder-[#94a3b8] focus:outline-none focus:border-[#2563eb] focus:ring-1 focus:ring-[#2563eb]"
                  />
                </div>

                {/* Password Strength Checklist */}
                {password.length > 0 && (
                  <div className="p-2.5 bg-[#f8fafc] border border-[#e2e8f0] rounded-[4px] space-y-1 text-[11px] text-[#64748b]">
                    <div className="font-medium text-[#0f172a] mb-1">
                      Password Requirements:
                    </div>
                    <div className="grid grid-cols-2 gap-1">
                      <span
                        className={`flex items-center gap-1.5 ${
                          hasMinLength ? "text-[#16a34a]" : "text-[#94a3b8]"
                        }`}
                      >
                        {hasMinLength ? (
                          <CheckCircle2 className="w-3.5 h-3.5" />
                        ) : (
                          <XCircle className="w-3.5 h-3.5" />
                        )}
                        8+ characters
                      </span>
                      <span
                        className={`flex items-center gap-1.5 ${
                          hasUppercase ? "text-[#16a34a]" : "text-[#94a3b8]"
                        }`}
                      >
                        {hasUppercase ? (
                          <CheckCircle2 className="w-3.5 h-3.5" />
                        ) : (
                          <XCircle className="w-3.5 h-3.5" />
                        )}
                        Uppercase (A-Z)
                      </span>
                      <span
                        className={`flex items-center gap-1.5 ${
                          hasLowercase ? "text-[#16a34a]" : "text-[#94a3b8]"
                        }`}
                      >
                        {hasLowercase ? (
                          <CheckCircle2 className="w-3.5 h-3.5" />
                        ) : (
                          <XCircle className="w-3.5 h-3.5" />
                        )}
                        Lowercase (a-z)
                      </span>
                      <span
                        className={`flex items-center gap-1.5 ${
                          hasDigitOrSpecial
                            ? "text-[#16a34a]"
                            : "text-[#94a3b8]"
                        }`}
                      >
                        {hasDigitOrSpecial ? (
                          <CheckCircle2 className="w-3.5 h-3.5" />
                        ) : (
                          <XCircle className="w-3.5 h-3.5" />
                        )}
                        Number or symbol
                      </span>
                    </div>
                  </div>
                )}
              </div>

              {/* Confirm Password */}
              <div className="space-y-1.5">
                <label
                  htmlFor="confirmPassword"
                  className="block text-xs font-semibold text-[#0f172a]"
                >
                  Confirm Password <span className="text-[#dc2626]">*</span>
                </label>
                <div className="relative">
                  <Lock className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-[#94a3b8]" />
                  <input
                    id="confirmPassword"
                    type="password"
                    autoComplete="new-password"
                    required
                    value={confirmPassword}
                    onChange={(e) => setConfirmPassword(e.target.value)}
                    placeholder="••••••••••••"
                    className="w-full h-10 pl-9 pr-3 text-sm bg-white border border-[#cbd5e1] rounded-[4px] text-[#0f172a] placeholder-[#94a3b8] focus:outline-none focus:border-[#2563eb] focus:ring-1 focus:ring-[#2563eb]"
                  />
                </div>
                {confirmPassword.length > 0 && !passwordsMatch && (
                  <p className="text-[11px] text-[#dc2626]">
                    Passwords do not match yet.
                  </p>
                )}
              </div>

              {/* Submit Button */}
              <Button
                type="submit"
                variant="primary"
                size="md"
                isLoading={isLoading}
                disabled={!isPasswordValid || !passwordsMatch || !organizationName.trim()}
                className="w-full mt-2"
              >
                Create Workspace & Sign In
              </Button>
            </form>

            <div className="text-center pt-2">
              <p className="text-xs text-[#64748b]">
                Already have an account?{" "}
                <Link
                  href="/login"
                  className="text-[#2563eb] font-medium hover:underline focus:outline-none focus:ring-1 focus:ring-[#2563eb] rounded"
                >
                  Sign in to existing workspace
                </Link>
              </p>
            </div>

            {/* Security Notice */}
            <div className="pt-2 border-t border-[#f1f5f9] flex items-center justify-between text-[11px] text-[#64748b]">
              <span className="flex items-center gap-1">
                <ShieldCheck className="w-3.5 h-3.5 text-[#16a34a]" />
                Multi-Tenant Isolated DB
              </span>
              <Badge variant="neutral">Bcrypt • JWT</Badge>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
