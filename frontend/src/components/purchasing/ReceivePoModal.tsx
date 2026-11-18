"use client";

import React, { useState, useEffect } from "react";
import { X, AlertCircle, PackageCheck, Plus } from "lucide-react";
import { Button } from "@/components/ui/Button";
import { apiClient, ApiError, PurchaseOrder, receivePurchaseOrder } from "@/lib/api-client";

export interface ReceivePoModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccess: () => void;
  purchaseOrder: PurchaseOrder | null;
}

export function ReceivePoModal({
  isOpen,
  onClose,
  onSuccess,
  purchaseOrder,
}: ReceivePoModalProps) {
  const [locationId, setLocationId] = useState("");
  const [locations, setLocations] = useState<Array<{ id: string; name: string }>>([]);
  const [isLocationsLoaded, setIsLocationsLoaded] = useState(false);
  const [isCreatingLocation, setIsCreatingLocation] = useState(false);
  const isLoadingLocations = !isLocationsLoaded;
  const [receiveAmounts, setReceiveAmounts] = useState<Record<string, number>>(() => {
    const initialMap: Record<string, number> = {};
    if (purchaseOrder) {
      for (const item of purchaseOrder.items) {
        const remaining = Math.max(0, item.quantity_ordered - item.quantity_received);
        initialMap[item.id] = remaining;
      }
    }
    return initialMap;
  });
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const [prevPoId, setPrevPoId] = useState(purchaseOrder?.id);
  if (purchaseOrder?.id !== prevPoId) {
    setPrevPoId(purchaseOrder?.id);
    const initialMap: Record<string, number> = {};
    if (purchaseOrder) {
      for (const item of purchaseOrder.items) {
        const remaining = Math.max(0, item.quantity_ordered - item.quantity_received);
        initialMap[item.id] = remaining;
      }
    }
    setReceiveAmounts(initialMap);
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
          setLocationId((curr) => (res.some((l) => l.id === curr) ? curr : res[0].id));
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

  if (!isOpen || !purchaseOrder) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMsg(null);

    if (!locationId) {
      setErrorMsg("Please select a destination warehouse location.");
      return;
    }

    const itemsToReceive = Object.entries(receiveAmounts)
      .filter(([, qty]) => qty > 0)
      .map(([poItemId, qty]) => ({
        po_item_id: poItemId,
        quantity_to_receive: qty,
      }));

    if (itemsToReceive.length === 0) {
      setErrorMsg("No items selected with positive quantities to receive.");
      return;
    }

    setIsSubmitting(true);
    try {
      await receivePurchaseOrder(purchaseOrder.id, {
        location_id: locationId,
        items: itemsToReceive,
      });

      onSuccess();
      onClose();
    } catch (err: unknown) {
      if (err instanceof ApiError) {
        setErrorMsg(err.message);
      } else {
        setErrorMsg("Failed to receive goods into inventory.");
      }
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleQtyChange = (itemId: string, maxQty: number, valStr: string) => {
    const val = parseInt(valStr, 10);
    const safeVal = isNaN(val) ? 0 : Math.min(Math.max(0, val), maxQty);
    setReceiveAmounts((prev) => ({
      ...prev,
      [itemId]: safeVal,
    }));
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4 backdrop-blur-xs">
      <div className="relative w-full max-w-lg rounded-xl bg-white shadow-2xl border border-[#e2e8f0]">
        <div className="flex items-center justify-between border-b border-[#e2e8f0] px-6 py-4">
          <div className="flex items-center gap-2">
            <div className="p-1.5 rounded-md bg-[#ecfdf5] text-[#059669]">
              <PackageCheck className="w-5 h-5" />
            </div>
            <div>
              <h2 className="text-lg font-semibold text-[#0f172a]">Receive Shipment</h2>
              <p className="text-xs text-[#64748b]">PO #{purchaseOrder.id.slice(0, 8).toUpperCase()}</p>
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

          <div>
            <div className="flex items-center justify-between mb-1.5">
              <label className="block text-xs font-semibold text-[#334155] uppercase tracking-wider">
                Receiving Destination Warehouse *
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
                <option value="">Loading warehouses...</option>
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

          <div>
            <label className="block text-xs font-semibold text-[#334155] uppercase tracking-wider mb-1.5">
              Items to Receive
            </label>
            <div className="divide-y divide-[#f1f5f9] border border-[#e2e8f0] rounded-lg overflow-hidden max-h-60 overflow-y-auto">
              {purchaseOrder.items.map((item) => {
                const remaining = Math.max(0, item.quantity_ordered - item.quantity_received);
                const isFulfilled = remaining === 0;

                return (
                  <div key={item.id} className="p-3 flex items-center justify-between gap-4 bg-white hover:bg-[#f8fafc]">
                    <div className="min-w-0">
                      <p className="text-sm font-medium text-[#0f172a] truncate">
                        {item.sku_code || item.sku_id.slice(0, 8)}
                      </p>
                      <p className="text-xs text-[#64748b]">
                        Ordered: {item.quantity_ordered} | Recv: {item.quantity_received} | Due: {remaining}
                      </p>
                    </div>

                    <div className="w-24 shrink-0">
                      <input
                        type="number"
                        min="0"
                        max={remaining}
                        disabled={isFulfilled}
                        value={receiveAmounts[item.id] ?? 0}
                        onChange={(e) => handleQtyChange(item.id, remaining, e.target.value)}
                        className="w-full rounded-md border border-[#cbd5e1] px-2.5 py-1 text-sm text-right text-[#0f172a] focus:border-[#2563eb] focus:outline-none focus:ring-1 focus:ring-[#2563eb] disabled:bg-[#f1f5f9] disabled:text-[#94a3b8]"
                      />
                    </div>
                  </div>
                );
              })}
            </div>
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
              Confirm Stock Receipt
            </Button>
          </div>
        </form>
      </div>
    </div>
  );
}
