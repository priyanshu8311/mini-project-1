"use client";

import React, { useState } from "react";
import Link from "next/link";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  Card,
  CardHeader,
  CardTitle,
  CardDescription,
  CardContent,
} from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import {
  getShopifyConfig,
  saveShopifyConfig,
  testShopifyConnection,
  type ShopifyConfigPayload,
} from "@/lib/api-client";

export default function SettingsPage() {
  const queryClient = useQueryClient();

  const [isModalOpen, setIsModalOpen] = useState<boolean>(false);
  const [feedback, setFeedback] = useState<{ type: "success" | "error"; message: string } | null>(null);

  // Form State
  const [shopDomain, setShopDomain] = useState<string>("");
  const [accessToken, setAccessToken] = useState<string>("");
  const [shopifyLocationId, setShopifyLocationId] = useState<string>("");
  const [webhookSecret, setWebhookSecret] = useState<string>("");
  const [autoSyncStock, setAutoSyncStock] = useState<boolean>(true);

  // React Query for Shopify Configuration
  const {
    data: shopifyConfig,
    isLoading,
    isError,
  } = useQuery({
    queryKey: ["shopify-config"],
    queryFn: getShopifyConfig,
    retry: false,
  });

  // Save Mutation
  const saveMutation = useMutation({
    mutationFn: (payload: ShopifyConfigPayload) => saveShopifyConfig(payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["shopify-config"] });
      setFeedback({ type: "success", message: "Shopify configuration saved successfully!" });
      setIsModalOpen(false);
      setAccessToken(""); // Clear plain token from state
    },
    onError: (err: Error) => {
      setFeedback({ type: "error", message: err.message || "Failed to save configuration" });
    },
  });

  // Test Connection Mutation
  const testMutation = useMutation({
    mutationFn: testShopifyConnection,
    onSuccess: (result) => {
      if (result.success) {
        setFeedback({
          type: "success",
          message: `Connected to ${result.shop_name || "Shopify"} (${result.currency || "USD"}).`,
        });
      } else {
        setFeedback({ type: "error", message: result.message });
      }
    },
    onError: (err: Error) => {
      setFeedback({ type: "error", message: err.message || "Connection test failed" });
    },
  });

  const handleOpenModal = () => {
    if (shopifyConfig) {
      setShopDomain(shopifyConfig.shop_domain);
      setShopifyLocationId(shopifyConfig.shopify_location_id || "");
      setAutoSyncStock(shopifyConfig.auto_sync_stock);
    }
    setAccessToken("");
    setIsModalOpen(true);
  };

  const handleSave = (e: React.FormEvent) => {
    e.preventDefault();
    setFeedback(null);
    saveMutation.mutate({
      shop_domain: shopDomain,
      access_token: accessToken,
      shopify_location_id: shopifyLocationId.trim() || null,
      webhook_secret: webhookSecret.trim() || null,
      auto_sync_stock: autoSyncStock,
    });
  };

  const handleTestConnection = () => {
    setFeedback(null);
    testMutation.mutate();
  };

  const isConnected = !isLoading && !isError && !!shopifyConfig;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-[#0f172a]">
            Settings & Integrations
          </h1>
          <p className="text-sm text-[#64748b] mt-1">
            Multi-channel synchronization, webhooks, and sales platform configurations.
          </p>
        </div>
      </div>

      {feedback && (
        <div
          role="alert"
          className={`p-4 rounded-lg text-sm border flex items-center justify-between ${
            feedback.type === "success"
              ? "bg-emerald-50 text-emerald-800 border-emerald-200"
              : "bg-rose-50 text-rose-800 border-rose-200"
          }`}
        >
          <span>{feedback.message}</span>
          <button
            onClick={() => setFeedback(null)}
            className="text-xs font-semibold underline ml-4 hover:opacity-80"
          >
            Dismiss
          </button>
        </div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {/* User Management & RBAC */}
        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <CardTitle>User Management & RBAC</CardTitle>
              <Badge variant="info">Admin</Badge>
            </div>
            <CardDescription>
              Manage organization users, invite team members, and configure role-based permissions.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <Link href="/settings/users">
              <Button variant="primary" size="sm">Manage Users & Roles</Button>
            </Link>
          </CardContent>
        </Card>

        {/* Shopify Integration */}
        <Card className="flex flex-col justify-between">
          <CardHeader>
            <div className="flex items-center justify-between">
              <CardTitle>Shopify Integration</CardTitle>
              {isLoading ? (
                <Badge variant="neutral">Loading...</Badge>
              ) : isConnected ? (
                <Badge variant="success">Connected</Badge>
              ) : (
                <Badge variant="neutral">Not Connected</Badge>
              )}
            </div>
            <CardDescription>
              Two-way inventory and order synchronization with Shopify stores.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            {isConnected && shopifyConfig && (
              <div className="text-xs text-[#64748b] space-y-1 bg-[#f8fafc] p-3 rounded border border-[#e2e8f0]">
                <p><span className="font-medium text-[#334155]">Store:</span> {shopifyConfig.shop_domain}</p>
                <p><span className="font-medium text-[#334155]">Token:</span> {shopifyConfig.masked_access_token}</p>
                <p>
                  <span className="font-medium text-[#334155]">Last Sync:</span>{" "}
                  {shopifyConfig.last_sync_at
                    ? new Date(shopifyConfig.last_sync_at).toLocaleString()
                    : "Never"}
                </p>
                <p>
                  <span className="font-medium text-[#334155]">Auto-Sync:</span>{" "}
                  {shopifyConfig.auto_sync_stock ? "Enabled" : "Disabled"}
                </p>
              </div>
            )}

            <div className="flex items-center gap-2 pt-2">
              <Button
                variant={isConnected ? "outline" : "primary"}
                size="sm"
                onClick={handleOpenModal}
              >
                {isConnected ? "Edit Configuration" : "Connect Shopify"}
              </Button>

              {isConnected && (
                <Button
                  variant="outline"
                  size="sm"
                  onClick={handleTestConnection}
                  isLoading={testMutation.isPending}
                >
                  Test Connection
                </Button>
              )}
            </div>
          </CardContent>
        </Card>

        {/* Square POS Integration */}
        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <CardTitle>Square POS Integration</CardTitle>
              <Badge variant="neutral">Not Connected</Badge>
            </div>
            <CardDescription>
              Real-time POS sale stock decrement and catalog sync.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <Button variant="outline" size="sm" disabled>
              Coming Soon
            </Button>
          </CardContent>
        </Card>
      </div>

      {/* Shopify Configuration Modal */}
      {isModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm p-4">
          <div className="bg-white rounded-xl shadow-xl border border-[#e2e8f0] w-full max-w-lg overflow-hidden animate-in fade-in-50 zoom-in-95 duration-150">
            <div className="px-6 py-4 border-b border-[#e2e8f0] flex items-center justify-between">
              <div>
                <h3 className="text-lg font-semibold text-[#0f172a]">
                  {isConnected ? "Edit Shopify Connection" : "Connect Shopify Store"}
                </h3>
                <p className="text-xs text-[#64748b] mt-0.5">
                  Credentials are encrypted using AES-256-GCM before storage.
                </p>
              </div>
              <button
                type="button"
                onClick={() => setIsModalOpen(false)}
                className="text-[#64748b] hover:text-[#0f172a] text-lg font-bold"
              >
                &times;
              </button>
            </div>

            <form onSubmit={handleSave} className="p-6 space-y-4">
              <div>
                <label className="block text-xs font-semibold text-[#334155] uppercase tracking-wider mb-1">
                  Shop Domain *
                </label>
                <input
                  type="text"
                  required
                  placeholder="my-brand.myshopify.com"
                  value={shopDomain}
                  onChange={(e) => setShopDomain(e.target.value)}
                  className="w-full px-3 py-2 text-sm rounded-lg border border-[#cbd5e1] focus:outline-none focus:ring-2 focus:ring-indigo-500"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-[#334155] uppercase tracking-wider mb-1">
                  Admin API Access Token *
                </label>
                <input
                  type="password"
                  required={!isConnected}
                  placeholder={isConnected ? "Leave blank to keep existing token" : "shpat_xxxxxxxxxxxxxxxx"}
                  value={accessToken}
                  onChange={(e) => setAccessToken(e.target.value)}
                  className="w-full px-3 py-2 text-sm rounded-lg border border-[#cbd5e1] focus:outline-none focus:ring-2 focus:ring-indigo-500"
                />
                <p className="text-[11px] text-[#64748b] mt-1">
                  Generated from your Shopify Custom App with write_inventory, read_orders permissions.
                </p>
              </div>

              <div>
                <label className="block text-xs font-semibold text-[#334155] uppercase tracking-wider mb-1">
                  Shopify Location ID (Optional)
                </label>
                <input
                  type="text"
                  placeholder="e.g. 81928391823"
                  value={shopifyLocationId}
                  onChange={(e) => setShopifyLocationId(e.target.value)}
                  className="w-full px-3 py-2 text-sm rounded-lg border border-[#cbd5e1] focus:outline-none focus:ring-2 focus:ring-indigo-500"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-[#334155] uppercase tracking-wider mb-1">
                  Webhook Secret (Optional)
                </label>
                <input
                  type="password"
                  placeholder="Webhook signing secret from Shopify notifications settings"
                  value={webhookSecret}
                  onChange={(e) => setWebhookSecret(e.target.value)}
                  className="w-full px-3 py-2 text-sm rounded-lg border border-[#cbd5e1] focus:outline-none focus:ring-2 focus:ring-indigo-500"
                />
              </div>

              <div className="flex items-center gap-2 pt-1">
                <input
                  type="checkbox"
                  id="auto_sync"
                  checked={autoSyncStock}
                  onChange={(e) => setAutoSyncStock(e.target.checked)}
                  className="rounded border-[#cbd5e1] text-indigo-600 focus:ring-indigo-500"
                />
                <label htmlFor="auto_sync" className="text-xs text-[#334155]">
                  Automatically push inventory updates to Shopify when stock changes
                </label>
              </div>

              <div className="flex items-center justify-end gap-3 pt-4 border-t border-[#e2e8f0]">
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
                  isLoading={saveMutation.isPending}
                >
                  Save Configuration
                </Button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
