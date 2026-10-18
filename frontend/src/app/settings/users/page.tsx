"use client";

import React, { useState } from "react";
import Link from "next/link";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  AlertCircle,
  ArrowLeft,
  CheckCircle2,
  Lock,
  Mail,
  Plus,
  Shield,
  ShieldAlert,
  UserCheck,
  UserX,
  Users,
  X,
} from "lucide-react";
import { useAuth } from "@/hooks/useAuth";
import {
  apiClient,
  type UserListResponse,
  type UserResponse,
} from "@/lib/api-client";
import { Button } from "@/components/ui/Button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";

const SYSTEM_ROLES = [
  {
    role: "Admin",
    description: "Full tenant administration, user management, and configuration.",
  },
  {
    role: "Inventory Manager",
    description: "Full stock CRUD, SKU management, transfer approval, and forecasting.",
  },
  {
    role: "Purchaser",
    description: "View forecasts and stock levels, generate and manage purchase orders.",
  },
  {
    role: "Warehouse Staff",
    description: "Stock ledger updates via receiving shipments and dispatching stock.",
  },
  {
    role: "Analyst",
    description: "Read-only analytics, report export, and batch demand forecast jobs.",
  },
  {
    role: "Viewer",
    description: "Read-only access to inventory dashboards and general reports.",
  },
];

export default function UserManagementPage() {
  const { user: currentUser, isAdmin, isLoading: authLoading } = useAuth();
  const queryClient = useQueryClient();

  const [actionSuccess, setActionSuccess] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  // Modal State for Adding New User
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [newEmail, setNewEmail] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [newRole, setNewRole] = useState("Viewer");
  const [modalError, setModalError] = useState<string | null>(null);

  // React Query for tenant users
  const {
    data: usersData,
    isLoading: usersLoading,
    error: queryError,
  } = useQuery({
    queryKey: ["users"],
    queryFn: () => apiClient<UserListResponse>("/users"),
    enabled: !authLoading && isAdmin,
  });

  const users = usersData?.data || [];

  // Create User Mutation
  const createUserMutation = useMutation({
    mutationFn: (payload: { email: string; password: string; role: string }) =>
      apiClient<UserResponse>("/users", {
        method: "POST",
        body: JSON.stringify(payload),
      }),
    onSuccess: (data) => {
      setActionSuccess(`User '${data.email}' created successfully.`);
      setIsModalOpen(false);
      setNewEmail("");
      setNewPassword("");
      setNewRole("Viewer");
      setModalError(null);
      queryClient.invalidateQueries({ queryKey: ["users"] });
    },
    onError: (err) => {
      setModalError(
        err instanceof Error ? err.message : "Failed to provision user."
      );
    },
  });

  // Toggle Status Mutation
  const toggleStatusMutation = useMutation({
    mutationFn: ({ userId, isActive }: { userId: string; isActive: boolean }) =>
      apiClient<UserResponse>(`/users/${userId}/status`, {
        method: "PATCH",
        body: JSON.stringify({ is_active: isActive }),
      }),
    onSuccess: (data) => {
      const statusLabel = data.is_active ? "activated" : "deactivated";
      setActionSuccess(`User '${data.email}' has been ${statusLabel}.`);
      queryClient.invalidateQueries({ queryKey: ["users"] });
    },
    onError: (err) => {
      setError(
        err instanceof Error ? err.message : "Failed to update user status."
      );
    },
  });

  const handleCreateUser = (e: React.FormEvent) => {
    e.preventDefault();
    setModalError(null);
    createUserMutation.mutate({
      email: newEmail.trim(),
      password: newPassword,
      role: newRole,
    });
  };

  const handleToggleStatus = (userToUpdate: UserResponse) => {
    setActionSuccess(null);
    setError(null);

    if (userToUpdate.id === currentUser?.id) {
      setError("You cannot deactivate your own administrative account.");
      return;
    }

    toggleStatusMutation.mutate({
      userId: userToUpdate.id,
      isActive: !userToUpdate.is_active,
    });
  };

  // 403 Forbidden State if non-admin accesses this route
  if (!authLoading && !isAdmin) {
    return (
      <div className="min-h-[60vh] flex items-center justify-center p-4">
        <Card className="max-w-md w-full border-[#fecaca] shadow-sm">
          <CardHeader className="text-center space-y-2">
            <div className="w-12 h-12 rounded-full bg-[#fef2f2] text-[#dc2626] mx-auto flex items-center justify-center">
              <ShieldAlert className="w-6 h-6" />
            </div>
            <CardTitle className="text-lg text-[#dc2626]">
              403 Forbidden - Access Restricted
            </CardTitle>
            <CardDescription>
              User management and role assignment requires the Administrator role
              within your corporate workspace.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="p-3 bg-[#f8fafc] border border-[#e2e8f0] rounded text-xs text-[#64748b]">
              Your current role is{" "}
              <span className="font-semibold text-[#0f172a]">
                {currentUser?.role || "Unknown"}
              </span>
              . If you need administrative privileges, please contact your
              organization supervisor.
            </div>
            <Link href="/">
              <Button variant="outline" className="w-full">
                <ArrowLeft className="w-4 h-4 mr-2" />
                Return to Dashboard
              </Button>
            </Link>
          </CardContent>
        </Card>
      </div>
    );
  }

  const effectiveError =
    error || (queryError instanceof Error ? queryError.message : null);

  return (
    <div className="space-y-6">
      {/* Header with Navigation & Action */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <Link
              href="/settings"
              className="text-xs text-[#64748b] hover:text-[#0f172a] inline-flex items-center gap-1"
            >
              <ArrowLeft className="w-3.5 h-3.5" />
              Settings
            </Link>
          </div>
          <h1 className="text-2xl font-bold tracking-tight text-[#0f172a] flex items-center gap-2">
            <Users className="w-6 h-6 text-[#2563eb]" />
            Team Members & Roles
          </h1>
          <p className="text-sm text-[#64748b] mt-1">
            Manage your organization workspace users, roles, and granular access permissions.
          </p>
        </div>

        <Button
          variant="primary"
          onClick={() => {
            setModalError(null);
            setIsModalOpen(true);
          }}
        >
          <Plus className="w-4 h-4 mr-1.5" />
          Add Team Member
        </Button>
      </div>

      {/* Success Notification Banner */}
      {actionSuccess && (
        <div
          role="alert"
          className="p-3 rounded-[4px] bg-[#f0fdf4] border border-[#bbf7d0] text-[#16a34a] text-xs flex items-center justify-between"
        >
          <div className="flex items-center gap-2">
            <CheckCircle2 className="w-4 h-4 shrink-0" />
            <span>{actionSuccess}</span>
          </div>
          <button
            type="button"
            onClick={() => setActionSuccess(null)}
            className="text-[#16a34a] hover:opacity-80"
          >
            <X className="w-3.5 h-3.5" />
          </button>
        </div>
      )}

      {/* Global Error Banner */}
      {effectiveError && (
        <div
          role="alert"
          className="p-3 rounded-[4px] bg-[#fef2f2] border border-[#fecaca] text-[#dc2626] text-xs flex items-center justify-between"
        >
          <div className="flex items-center gap-2">
            <AlertCircle className="w-4 h-4 shrink-0" />
            <span>{effectiveError}</span>
          </div>
          <button
            type="button"
            onClick={() => setError(null)}
            className="text-[#dc2626] hover:opacity-80"
          >
            <X className="w-3.5 h-3.5" />
          </button>
        </div>
      )}

      {/* Users Table Card */}
      <Card>
        <CardHeader className="flex flex-row items-center justify-between">
          <div>
            <CardTitle>Workspace Users</CardTitle>
            <CardDescription>
              All accounts belonging strictly to your tenant organization.
            </CardDescription>
          </div>
          <Badge variant="info">{users.length} Total Users</Badge>
        </CardHeader>
        <CardContent className="p-0">
          {usersLoading ? (
            <div className="p-8 text-center text-xs text-[#64748b]">
              Loading user registry...
            </div>
          ) : users.length === 0 ? (
            <div className="p-8 text-center text-xs text-[#64748b]">
              No users found. Click &quot;Add Team Member&quot; to provision an account.
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead className="bg-[#f8fafc] text-[#64748b] border-y border-[#e2e8f0]">
                  <tr>
                    <th className="py-3 px-4 font-semibold">User Email</th>
                    <th className="py-3 px-4 font-semibold">Assigned Role</th>
                    <th className="py-3 px-4 font-semibold">Account Status</th>
                    <th className="py-3 px-4 font-semibold">Created Date</th>
                    <th className="py-3 px-4 font-semibold text-right">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-[#f1f5f9]">
                  {users.map((u) => {
                    const isSelf = u.id === currentUser?.id;
                    return (
                      <tr key={u.id} className="hover:bg-[#f8fafc]">
                        <td className="py-3 px-4 font-medium text-[#0f172a]">
                          <div className="flex items-center gap-2">
                            <span>{u.email}</span>
                            {isSelf && (
                              <Badge variant="neutral" className="text-[10px]">
                                You
                              </Badge>
                            )}
                          </div>
                        </td>
                        <td className="py-3 px-4">
                          <span className="inline-flex items-center gap-1 font-medium text-[#2563eb]">
                            <Shield className="w-3.5 h-3.5" />
                            {u.role}
                          </span>
                        </td>
                        <td className="py-3 px-4">
                          {u.is_active ? (
                            <Badge variant="success" icon={<CheckCircle2 className="w-3 h-3" />}>
                              Active
                            </Badge>
                          ) : (
                            <Badge variant="error" icon={<X className="w-3 h-3" />}>
                              Deactivated
                            </Badge>
                          )}
                        </td>
                        <td className="py-3 px-4 text-[#64748b]">
                          {new Date(u.created_at).toLocaleDateString()}
                        </td>
                        <td className="py-3 px-4 text-right">
                          {isSelf ? (
                            <span className="text-[11px] text-[#94a3b8] italic">
                              Active Admin
                            </span>
                          ) : (
                            <Button
                              variant={u.is_active ? "ghost" : "outline"}
                              size="sm"
                              onClick={() => handleToggleStatus(u)}
                              className={
                                u.is_active
                                  ? "text-[#dc2626] hover:bg-[#fef2f2] hover:text-[#b91c1c]"
                                  : "text-[#16a34a] hover:bg-[#f0fdf4]"
                              }
                            >
                              {u.is_active ? (
                                <>
                                  <UserX className="w-3.5 h-3.5 mr-1" />
                                  Deactivate
                                </>
                              ) : (
                                <>
                                  <UserCheck className="w-3.5 h-3.5 mr-1" />
                                  Activate
                                </>
                              )}
                            </Button>
                          )}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Role Definitions Reference Card */}
      <Card>
        <CardHeader>
          <CardTitle>Role Permissions Matrix (PRD.md)</CardTitle>
          <CardDescription>
            Overview of access privileges enforced across server-side API endpoints.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
            {SYSTEM_ROLES.map((r) => (
              <div
                key={r.role}
                className="p-3 rounded border border-[#e2e8f0] bg-[#f8fafc] space-y-1"
              >
                <div className="font-semibold text-xs text-[#0f172a] flex items-center justify-between">
                  <span>{r.role}</span>
                  <Badge variant="neutral">{r.role}</Badge>
                </div>
                <p className="text-[11px] text-[#64748b] leading-relaxed">
                  {r.description}
                </p>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* Modal: Create User */}
      {isModalOpen && (
        <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-lg shadow-xl max-w-md w-full border border-[#e2e8f0] overflow-hidden">
            <div className="p-4 border-b border-[#e2e8f0] flex items-center justify-between">
              <h2 className="text-base font-bold text-[#0f172a]">
                Add Team Member
              </h2>
              <button
                type="button"
                onClick={() => setIsModalOpen(false)}
                className="p-1 rounded text-[#94a3b8] hover:text-[#0f172a]"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <form onSubmit={handleCreateUser} className="p-4 space-y-4">
              {modalError && (
                <div
                  role="alert"
                  className="p-3 rounded bg-[#fef2f2] border border-[#fecaca] text-[#dc2626] text-xs flex items-start gap-2"
                >
                  <AlertCircle className="w-4 h-4 shrink-0 mt-0.5" />
                  <span>{modalError}</span>
                </div>
              )}

              {/* Email */}
              <div className="space-y-1">
                <label
                  htmlFor="memberEmail"
                  className="block text-xs font-semibold text-[#0f172a]"
                >
                  Work Email <span className="text-[#dc2626]">*</span>
                </label>
                <div className="relative">
                  <Mail className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-[#94a3b8]" />
                  <input
                    id="memberEmail"
                    type="email"
                    required
                    value={newEmail}
                    onChange={(e) => setNewEmail(e.target.value)}
                    placeholder="teammate@company.com"
                    className="w-full h-9 pl-9 pr-3 text-xs bg-white border border-[#cbd5e1] rounded-[4px] focus:outline-none focus:border-[#2563eb]"
                  />
                </div>
              </div>

              {/* Password */}
              <div className="space-y-1">
                <label
                  htmlFor="memberPassword"
                  className="block text-xs font-semibold text-[#0f172a]"
                >
                  Initial Password <span className="text-[#dc2626]">*</span>
                </label>
                <div className="relative">
                  <Lock className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-[#94a3b8]" />
                  <input
                    id="memberPassword"
                    type="password"
                    required
                    value={newPassword}
                    onChange={(e) => setNewPassword(e.target.value)}
                    placeholder="Min 8 chars, Aa, 123/!"
                    className="w-full h-9 pl-9 pr-3 text-xs bg-white border border-[#cbd5e1] rounded-[4px] focus:outline-none focus:border-[#2563eb]"
                  />
                </div>
                <p className="text-[10px] text-[#64748b]">
                  Must include uppercase, lowercase, and a digit or symbol.
                </p>
              </div>

              {/* Role */}
              <div className="space-y-1">
                <label
                  htmlFor="memberRole"
                  className="block text-xs font-semibold text-[#0f172a]"
                >
                  Assigned Role <span className="text-[#dc2626]">*</span>
                </label>
                <select
                  id="memberRole"
                  value={newRole}
                  onChange={(e) => setNewRole(e.target.value)}
                  className="w-full h-9 px-3 text-xs bg-white border border-[#cbd5e1] rounded-[4px] focus:outline-none focus:border-[#2563eb]"
                >
                  {SYSTEM_ROLES.map((r) => (
                    <option key={r.role} value={r.role}>
                      {r.role}
                    </option>
                  ))}
                </select>
              </div>

              {/* Modal Actions */}
              <div className="flex items-center justify-end gap-2 pt-3 border-t border-[#f1f5f9]">
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  onClick={() => setIsModalOpen(false)}
                >
                  Cancel
                </Button>
                <Button
                  type="submit"
                  variant="primary"
                  size="sm"
                  isLoading={createUserMutation.isPending}
                >
                  Provision User
                </Button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
