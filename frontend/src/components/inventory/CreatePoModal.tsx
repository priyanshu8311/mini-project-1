"use client";

import React, { useState } from "react";
import { X, AlertCircle, ShoppingCart } from "lucide-react";
import { Button } from "@/components/ui/Button";
import { createPurchaseOrder, ApiError } from "@/lib/api-client";

export interface CreatePoModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccess: () => void;
  initialSkuId?: string;
  initialSkuCode?: string;
  initialQuantity?: number;
  initialUnitCost?: number | string;
}

export function CreatePoModal({
  isOpen,
  onClose,
  onSuccess,
  initialSkuId,
  initialSkuCode,
  initialQuantity,
  initialUnitCost,
}: CreatePoModalProps) {
  const [skuId, setSkuId] = useState(initialSkuId || "");
  const [quantity, setQuantity] = useState(String(initialQuantity || "50"));
  const [unitCost, setUnitCost] = useState(String(initialUnitCost || "10.00"));
  const [expectedDate, setExpectedDate] = useState(() => {
    const d = new Date();
    d.setDate(d.getDate() + 7);
    return d.toISOString().split("T")[0];
  });
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const [prevInitialSkuId, setPrevInitialSkuId] = useState(initialSkuId);
  if (initialSkuId !== prevInitialSkuId) {
    setPrevInitialSkuId(initialSkuId);
    if (initialSkuId) setSkuId(initialSkuId);
    if (initialQuantity) setQuantity(String(initialQuantity));
    if (initialUnitCost) setUnitCost(String(initialUnitCost));
  }

  if (!isOpen) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMsg(null);

    const qty = parseInt(quantity, 10);
    const cost = parseFloat(unitCost);

    if (!skuId.trim()) {
      setErrorMsg("SKU ID is required to create a purchase order.");
      return;
    }
    if (isNaN(qty) || qty <= 0) {
      setErrorMsg("Quantity ordered must be a positive integer.");
      return;
    }
    if (isNaN(cost) || cost < 0) {
      setErrorMsg("Unit cost must be a non-negative number.");
      return;
    }

    setIsSubmitting(true);
    try {
      await createPurchaseOrder({
        expected_date: expectedDate || null,
        items: [
          {
            sku_id: skuId.trim(),
            quantity_ordered: qty,
            unit_cost: cost,
          },
        ],
      });

      onSuccess();
      onClose();
    } catch (err: unknown) {
      if (err instanceof ApiError) {
        setErrorMsg(err.message);
      } else {
        setErrorMsg("Failed to create purchase order.");
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
            <div className="p-1.5 rounded-md bg-[#eff6ff] text-[#2563eb]">
              <ShoppingCart className="w-5 h-5" />
            </div>
            <div>
              <h2 className="text-lg font-semibold text-[#0f172a]">New Purchase Order</h2>
              {initialSkuCode && (
                <p className="text-xs text-[#64748b]">Item: {initialSkuCode}</p>
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
                SKU UUID *
              </label>
              <input
                type="text"
                required
                value={skuId}
                onChange={(e) => setSkuId(e.target.value)}
                placeholder="Target SKU ID"
                className="w-full rounded-lg border border-[#cbd5e1] px-3 py-2 text-sm text-[#0f172a] focus:border-[#2563eb] focus:outline-none focus:ring-1 focus:ring-[#2563eb]"
              />
            </div>
          )}

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-semibold text-[#334155] uppercase tracking-wider mb-1.5">
                Quantity *
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
                Unit Cost ($)
              </label>
              <input
                type="number"
                step="0.01"
                min="0"
                required
                value={unitCost}
                onChange={(e) => setUnitCost(e.target.value)}
                className="w-full rounded-lg border border-[#cbd5e1] px-3 py-2 text-sm text-[#0f172a] focus:border-[#2563eb] focus:outline-none focus:ring-1 focus:ring-[#2563eb]"
              />
            </div>
          </div>

          <div>
            <label className="block text-xs font-semibold text-[#334155] uppercase tracking-wider mb-1.5">
              Expected Delivery Date
            </label>
            <input
              type="date"
              value={expectedDate}
              onChange={(e) => setExpectedDate(e.target.value)}
              className="w-full rounded-lg border border-[#cbd5e1] px-3 py-2 text-sm text-[#0f172a] focus:border-[#2563eb] focus:outline-none focus:ring-1 focus:ring-[#2563eb]"
            />
          </div>

          <div className="flex items-center justify-end gap-3 pt-4 border-t border-[#e2e8f0]">
            <Button type="button" variant="outline" size="sm" onClick={onClose} disabled={isSubmitting}>
              Cancel
            </Button>
            <Button type="submit" variant="primary" size="sm" isLoading={isSubmitting}>
              Issue Purchase Order
            </Button>
          </div>
        </form>
      </div>
    </div>
  );
}
