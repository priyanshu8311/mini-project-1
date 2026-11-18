"use client";

import React, { useState, useEffect } from "react";
import { X, AlertCircle, SlidersHorizontal, Plus } from "lucide-react";
import { Button } from "@/components/ui/Button";
import { apiClient, ApiError } from "@/lib/api-client";

export interface AdjustStockModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccess: () => void;
  skuId?: string;
  skuCode?: string;
  locationId?: string;
}

export function AdjustStockModal({
  isOpen,
  onClose,
  onSuccess,
  skuId: initialSkuId,
  skuCode: initialSkuCode,
  locationId: initialLocationId,
}: AdjustStockModalProps) {
  const [skuId, setSkuId] = useState(initialSkuId || "");
  const [locationId, setLocationId] = useState(initialLocationId || "");
  const [direction, setDirection] = useState<"add" | "remove">("add");
  const [quantity, setQuantity] = useState("1");
  const [reason, setReason] = useState("Cycle Count Reconciliation");
  const [locations, setLocations] = useState<Array<{ id: string; name: string }>>([]);
  const [isLocationsLoaded, setIsLocationsLoaded] = useState(false);
  const [isCreatingLocation, setIsCreatingLocation] = useState(false);
  const isLoadingLocations = !isLocationsLoaded;
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const [prevProps, setPrevProps] = useState({ initialSkuId, initialLocationId });
  if (initialSkuId !== prevProps.initialSkuId || initialLocationId !== prevProps.initialLocationId) {
    setPrevProps({ initialSkuId, initialLocationId });
    if (initialSkuId) setSkuId(initialSkuId);
    if (initialLocationId) setLocationId(initialLocationId);
  }

  const createDefaultWarehouse = async () => {
    setIsCreatingLocation(true);
    try {
      const created = await apiClient<{ id: string; name: string }>("/locations", {
        method: "POST",
        body: JSON.stringify({
          name: "Main Warehouse",
          type: "Warehouse",
          address: "Primary Facility",
        }),
      });
      setLocations((prev) => (prev.some((l) => l.id === created.id) ? prev : [...prev, created]));
      setLocationId(created.id);
    } catch (err: unknown) {
      if (err instanceof ApiError) {
        setErrorMsg(`Failed to setup warehouse: ${err.message}`);
      } else {
        setErrorMsg("Failed to setup default warehouse location.");
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
          setLocationId((curr) => (curr && res.some((l) => l.id === curr) ? curr : res[0].id));
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
              setLocationId(created.id);
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
      setErrorMsg("Quantity must be a positive integer.");
      return;
    }
    if (!skuId) {
      setErrorMsg("SKU ID is required.");
      return;
    }
    if (!locationId) {
      setErrorMsg("Please select a storage location.");
      return;
    }

    const delta = direction === "add" ? qty : -qty;

    setIsSubmitting(true);
    try {
      await apiClient("/inventory/transactions", {
        method: "POST",
        body: JSON.stringify({
          transaction_type: "Adjust",
          sku_id: skuId,
          location_id: locationId,
          quantity_change: delta,
          reason: reason.trim() || "Manual adjustment",
        }),
      });

      onSuccess();
      onClose();
    } catch (err: unknown) {
      if (err instanceof ApiError) {
        setErrorMsg(err.message);
      } else {
        setErrorMsg("Failed to adjust inventory stock.");
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
              <SlidersHorizontal className="w-5 h-5" />
            </div>
            <div>
              <h2 className="text-lg font-semibold text-[#0f172a]">Adjust Stock Level</h2>
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

          <div>
            <div className="flex items-center justify-between mb-1.5">
              <label className="block text-xs font-semibold text-[#334155] uppercase tracking-wider">
                Storage Location *
              </label>
              {locations.length === 0 && !isLoadingLocations && (
                <button
                  type="button"
                  onClick={createDefaultWarehouse}
                  disabled={isCreatingLocation}
                  className="inline-flex items-center gap-1 text-xs font-medium text-[#2563eb] hover:text-[#1d4ed8] underline disabled:opacity-50"
                >
                  <Plus className="w-3.5 h-3.5" />
                  <span>{isCreatingLocation ? "Provisioning..." : "Add Main Warehouse"}</span>
                </button>
              )}
            </div>
            <select
              required
              value={locationId}
              onChange={(e) => setLocationId(e.target.value)}
              disabled={isLoadingLocations || isCreatingLocation || locations.length === 0}
              className="w-full rounded-lg border border-[#cbd5e1] px-3 py-2 text-sm text-[#0f172a] focus:border-[#2563eb] focus:outline-none focus:ring-1 focus:ring-[#2563eb] disabled:bg-[#f1f5f9] disabled:text-[#94a3b8]"
            >
              {isLoadingLocations ? (
                <option value="">Loading locations...</option>
              ) : isCreatingLocation ? (
                <option value="">Setting up default warehouse...</option>
              ) : locations.length === 0 ? (
                <option value="">No warehouse found — click &quot;Add Main Warehouse&quot;</option>
              ) : (
                locations.map((loc) => (
                  <option key={loc.id} value={loc.id}>
                    {loc.name}
                  </option>
                ))
              )}
            </select>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-semibold text-[#334155] uppercase tracking-wider mb-1.5">
                Adjustment Action
              </label>
              <select
                value={direction}
                onChange={(e) => setDirection(e.target.value as "add" | "remove")}
                className="w-full rounded-lg border border-[#cbd5e1] px-3 py-2 text-sm text-[#0f172a] focus:border-[#2563eb] focus:outline-none focus:ring-1 focus:ring-[#2563eb]"
              >
                <option value="add">Increase (+)</option>
                <option value="remove">Decrease (-)</option>
              </select>
            </div>

            <div>
              <label className="block text-xs font-semibold text-[#334155] uppercase tracking-wider mb-1.5">
                Quantity Units *
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
          </div>

          <div>
            <label className="block text-xs font-semibold text-[#334155] uppercase tracking-wider mb-1.5">
              Reason / Memo
            </label>
            <input
              type="text"
              value={reason}
              onChange={(e) => setReason(e.target.value)}
              placeholder="e.g. Cycle count discrepancy, Damaged inventory"
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
              disabled={isSubmitting || isLoadingLocations || isCreatingLocation || !locationId}
            >
              Confirm Adjustment
            </Button>
          </div>
        </form>
      </div>
    </div>
  );
}
