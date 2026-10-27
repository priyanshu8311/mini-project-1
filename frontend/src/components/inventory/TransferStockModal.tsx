"use client";

import React, { useState, useEffect } from "react";
import { X, AlertCircle, ArrowRightLeft } from "lucide-react";
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
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const [prevSkuId, setPrevSkuId] = useState(initialSkuId);
  if (initialSkuId !== prevSkuId) {
    setPrevSkuId(initialSkuId);
    if (initialSkuId) setSkuId(initialSkuId);
  }

  useEffect(() => {
    if (!isOpen) return;
    let isCancelled = false;
    apiClient<Array<{ id: string; name: string }>>("/locations")
      .then((res) => {
        if (!isCancelled) {
          setLocations(res);
          if (res.length >= 2) {
            setSourceLocId((curr) => curr || res[0].id);
            setTargetLocId((curr) => curr || res[1].id);
          } else if (res.length === 1) {
            setSourceLocId((curr) => curr || res[0].id);
          }
        }
      })
      .catch(() => {});
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

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-semibold text-[#334155] uppercase tracking-wider mb-1.5">
                From Location *
              </label>
              <select
                required
                value={sourceLocId}
                onChange={(e) => setSourceLocId(e.target.value)}
                className="w-full rounded-lg border border-[#cbd5e1] px-3 py-2 text-sm text-[#0f172a] focus:border-[#2563eb] focus:outline-none focus:ring-1 focus:ring-[#2563eb]"
              >
                {locations.map((loc) => (
                  <option key={loc.id} value={loc.id}>
                    {loc.name}
                  </option>
                ))}
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
                className="w-full rounded-lg border border-[#cbd5e1] px-3 py-2 text-sm text-[#0f172a] focus:border-[#2563eb] focus:outline-none focus:ring-1 focus:ring-[#2563eb]"
              >
                {locations.map((loc) => (
                  <option key={loc.id} value={loc.id}>
                    {loc.name}
                  </option>
                ))}
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
            <Button type="submit" variant="primary" size="sm" isLoading={isSubmitting}>
              Execute Transfer
            </Button>
          </div>
        </form>
      </div>
    </div>
  );
}
