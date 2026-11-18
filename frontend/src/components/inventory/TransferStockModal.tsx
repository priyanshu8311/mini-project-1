"use client";

import React, { useState, useEffect } from "react";
import { X, AlertCircle, ArrowRightLeft, Plus } from "lucide-react";
import { Button } from "@/components/ui/Button";
import { apiClient, ApiError } from "@/lib/api-client";

export interface TransferStockModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccess: () => void;
  skuId?: string;
  skuCode?: string;
}

export function TransferStockModal({
  isOpen,
  onClose,
  onSuccess,
  skuId: initialSkuId,
  skuCode: initialSkuCode,
}: TransferStockModalProps) {
  const [skuId, setSkuId] = useState(initialSkuId || "");
  const [sourceLocId, setSourceLocId] = useState("");
  const [targetLocId, setTargetLocId] = useState("");
  const [quantity, setQuantity] = useState("1");
  const [reason, setReason] = useState("Inter-warehouse rebalancing");
  const [locations, setLocations] = useState<Array<{ id: string; name: string }>>([]);
  const [isLocationsLoaded, setIsLocationsLoaded] = useState(false);
  const [isCreatingLocation, setIsCreatingLocation] = useState(false);
  const isLoadingLocations = !isLocationsLoaded;
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const [prevSkuId, setPrevSkuId] = useState(initialSkuId);
  if (initialSkuId !== prevSkuId) {
    setPrevSkuId(initialSkuId);
    if (initialSkuId) setSkuId(initialSkuId);
  }

  const createLocation = async (name: string, type: "Warehouse" | "Store", address: string) => {
    setIsCreatingLocation(true);
    try {
      const created = await apiClient<{ id: string; name: string }>("/locations", {
        method: "POST",
        body: JSON.stringify({ name, type, address }),
      });
      setLocations((prev) => {
        const next = prev.some((l) => l.id === created.id) ? prev : [...prev, created];
        if (next.length >= 2) {
          setSourceLocId((curr) => curr || next[0].id);
          setTargetLocId((curr) => (curr && curr !== next[0].id ? curr : next[1].id));
        } else if (next.length === 1) {
          setSourceLocId((curr) => curr || next[0].id);
        }
        return next;
      });
    } catch (err: unknown) {
      if (err instanceof ApiError) {
        setErrorMsg(`Failed to setup location: ${err.message}`);
      } else {
        setErrorMsg("Failed to setup location.");
      }
    } finally {
      setIsCreatingLocation(false);
    }
  };

  useEffect(() => {
    if (!isOpen) return;
    let isCancelled = false;
    apiClient<Array<{ id: string; name: string }>>("/locations")
      .then(async (res) => {
        if (isCancelled) return;
        if (res && res.length > 0) {
          setLocations(res);
          if (res.length >= 2) {
            setSourceLocId((curr) => curr || res[0].id);
            setTargetLocId((curr) => (curr && curr !== res[0].id ? curr : res[1].id));
          } else if (res.length === 1) {
            setSourceLocId((curr) => curr || res[0].id);
          }
        } else {
          try {
            const created = await apiClient<{ id: string; name: string }>("/locations", {
              method: "POST",
              body: JSON.stringify({
                name: "Main Warehouse",
                type: "Warehouse",
                address: "Primary Facility",
              }),
            });
            if (!isCancelled) {
              setLocations([created]);
              setSourceLocId(created.id);
            }
          } catch {
            // Handled gracefully
          }
        }
      })
      .catch((err) => {
        console.error("Failed to load locations", err);
      })
      .finally(() => {
        if (!isCancelled) {
          setIsLocationsLoaded(true);
        }
      });

    return () => {
      isCancelled = true;
    };
  }, [isOpen]);

  if (!isOpen) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMsg(null);

    const qty = parseInt(quantity, 10);
    if (isNaN(qty) || qty <= 0) {
      setErrorMsg("Transfer quantity must be a positive integer.");
      return;
    }
    if (!skuId) {
      setErrorMsg("SKU ID is required.");
      return;
    }
    if (!sourceLocId) {
      setErrorMsg("Source location is required.");
      return;
    }
    if (!targetLocId) {
      setErrorMsg("Destination location is required.");
      return;
    }
    if (sourceLocId === targetLocId) {
      setErrorMsg("Source and destination locations cannot be the same.");
      return;
    }

    setIsSubmitting(true);
    try {
      await apiClient("/inventory/transactions", {
        method: "POST",
        body: JSON.stringify({
          transaction_type: "Transfer",
          sku_id: skuId,
          location_id: sourceLocId,
          target_location_id: targetLocId,
          quantity_change: qty,
          reason: reason.trim() || "Stock relocation",
        }),
      });

      onSuccess();
      onClose();
    } catch (err: unknown) {
      if (err instanceof ApiError) {
        setErrorMsg(err.message);
      } else {
        setErrorMsg("Failed to complete stock transfer.");
      }
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4 backdrop-blur-xs">
      <div className="relative w-full max-w-md rounded-xl bg-white shadow-2xl border border-[#e2e8f0]">
        <div className="flex items-center justify-between border-b border-[#e2e8f0] px-6 py-4">
          <div className="flex items-center gap-2">
            <div className="p-1.5 rounded-md bg-[#f1f5f9] text-[#0f172a]">
              <ArrowRightLeft className="w-5 h-5" />
            </div>
            <div>
              <h2 className="text-lg font-semibold text-[#0f172a]">Transfer Stock</h2>
              {initialSkuCode && (
                <p className="text-xs text-[#64748b]">SKU: {initialSkuCode}</p>
              )}
            </div>
          </div>
          <button
            onClick={onClose}
            className="text-[#94a3b8] hover:text-[#0f172a] transition-colors p-1"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="p-6 space-y-4">
          {errorMsg && (
            <div className="flex items-start gap-2.5 rounded-lg border border-[#fecaca] bg-[#fef2f2] p-3 text-sm text-[#b91c1c]">
              <AlertCircle className="w-5 h-5 shrink-0 mt-0.5" />
              <span>{errorMsg}</span>
            </div>
          )}

          {!initialSkuId && (
            <div>
              <label className="block text-xs font-semibold text-[#334155] uppercase tracking-wider mb-1.5">
                SKU ID *
              </label>
              <input
                type="text"
                required
                value={skuId}
                onChange={(e) => setSkuId(e.target.value)}
                placeholder="UUID of SKU"
                className="w-full rounded-lg border border-[#cbd5e1] px-3 py-2 text-sm text-[#0f172a] focus:border-[#2563eb] focus:outline-none focus:ring-1 focus:ring-[#2563eb]"
              />
            </div>
          )}

          {locations.length < 2 && !isLoadingLocations && (
            <div className="rounded-lg border border-[#fde68a] bg-[#fffbeb] p-3 text-xs text-[#92400e] flex items-center justify-between">
              <span>Stock transfer requires at least 2 locations.</span>
              <button
                type="button"
                onClick={() => createLocation("Retail Storefront", "Store", "Storefront Facility")}
                disabled={isCreatingLocation}
                className="inline-flex items-center gap-1 font-semibold underline ml-2 hover:text-[#78350f] disabled:opacity-50"
              >
                <Plus className="w-3.5 h-3.5" />
                <span>{isCreatingLocation ? "Creating..." : "Add Secondary Location"}</span>
              </button>
            </div>
          )}

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-semibold text-[#334155] uppercase tracking-wider mb-1.5">
                From Location *
              </label>
              <select
                required
                value={sourceLocId}
                onChange={(e) => setSourceLocId(e.target.value)}
                disabled={isLoadingLocations || isCreatingLocation || locations.length === 0}
                className="w-full rounded-lg border border-[#cbd5e1] px-3 py-2 text-sm text-[#0f172a] focus:border-[#2563eb] focus:outline-none focus:ring-1 focus:ring-[#2563eb] disabled:bg-[#f1f5f9] disabled:text-[#94a3b8]"
              >
                {isLoadingLocations ? (
                  <option value="">Loading...</option>
                ) : locations.length === 0 ? (
                  <option value="">No locations found</option>
                ) : (
                  locations.map((loc) => (
                    <option key={loc.id} value={loc.id}>
                      {loc.name}
                    </option>
                  ))
                )}
              </select>
            </div>

            <div>
              <label className="block text-xs font-semibold text-[#334155] uppercase tracking-wider mb-1.5">
                To Destination *
              </label>
              <select
                required
                value={targetLocId}
                onChange={(e) => setTargetLocId(e.target.value)}
                disabled={isLoadingLocations || isCreatingLocation || locations.length === 0}
                className="w-full rounded-lg border border-[#cbd5e1] px-3 py-2 text-sm text-[#0f172a] focus:border-[#2563eb] focus:outline-none focus:ring-1 focus:ring-[#2563eb] disabled:bg-[#f1f5f9] disabled:text-[#94a3b8]"
              >
                {isLoadingLocations ? (
                  <option value="">Loading...</option>
                ) : locations.length === 0 ? (
                  <option value="">No locations found</option>
                ) : (
                  locations.map((loc) => (
                    <option key={loc.id} value={loc.id}>
                      {loc.name}
                    </option>
                  ))
                )}
              </select>
            </div>
          </div>

          <div>
            <label className="block text-xs font-semibold text-[#334155] uppercase tracking-wider mb-1.5">
              Quantity to Transfer *
            </label>
            <input
              type="number"
              min="1"
              required
              value={quantity}
              onChange={(e) => setQuantity(e.target.value)}
              className="w-full rounded-lg border border-[#cbd5e1] px-3 py-2 text-sm text-[#0f172a] focus:border-[#2563eb] focus:outline-none focus:ring-1 focus:ring-[#2563eb]"
            />
          </div>

          <div>
            <label className="block text-xs font-semibold text-[#334155] uppercase tracking-wider mb-1.5">
              Transfer Reason
            </label>
            <input
              type="text"
              value={reason}
              onChange={(e) => setReason(e.target.value)}
              placeholder="e.g. Replenish retail floor, Inter-store rebalancing"
              className="w-full rounded-lg border border-[#cbd5e1] px-3 py-2 text-sm text-[#0f172a] focus:border-[#2563eb] focus:outline-none focus:ring-1 focus:ring-[#2563eb]"
            />
          </div>

          <div className="flex items-center justify-end gap-3 pt-4 border-t border-[#e2e8f0]">
            <Button type="button" variant="outline" size="sm" onClick={onClose} disabled={isSubmitting}>
              Cancel
            </Button>
            <Button
              type="submit"
              variant="primary"
              size="sm"
              isLoading={isSubmitting}
              disabled={isSubmitting || isLoadingLocations || isCreatingLocation || !sourceLocId || !targetLocId || locations.length < 2}
            >
              Execute Transfer
            </Button>
          </div>
        </form>
      </div>
    </div>
  );
}
