"use client";

import React, { useState } from "react";
import { AlertCircle, Edit2, X } from "lucide-react";
import { Button } from "@/components/ui/Button";
import { apiClient, ApiError } from "@/lib/api-client";
import { SkuItem } from "@/app/inventory/page";

export interface EditSkuModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccess: () => void;
  sku: SkuItem | null;
}

export function EditSkuModal({
  isOpen,
  onClose,
  onSuccess,
  sku,
}: EditSkuModalProps) {
  const [skuCode, setSkuCode] = useState(sku?.sku_code || "");
  const [unitCost, setUnitCost] = useState(sku ? String(sku.unit_cost) : "0.00");
  const [salesPrice, setSalesPrice] = useState(sku ? String(sku.sales_price) : "0.00");
  const [leadTimeDays, setLeadTimeDays] = useState(sku ? String(sku.lead_time_days) : "7");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const [prevProps, setPrevProps] = useState({ isOpen, skuId: sku?.id });
  if (isOpen !== prevProps.isOpen || sku?.id !== prevProps.skuId) {
    setPrevProps({ isOpen, skuId: sku?.id });
    if (sku && isOpen) {
      setSkuCode(sku.sku_code);
      setUnitCost(String(sku.unit_cost));
      setSalesPrice(String(sku.sales_price));
      setLeadTimeDays(String(sku.lead_time_days));
      setErrorMsg(null);
    }
  }

  if (!isOpen || !sku) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMsg(null);

    const cleanSkuCode = skuCode.trim().toUpperCase();
    if (!cleanSkuCode) {
      setErrorMsg("SKU code is required.");
      return;
    }

    const parsedUnitCost = parseFloat(unitCost);
    const parsedSalesPrice = parseFloat(salesPrice);
    const parsedLeadTime = parseInt(leadTimeDays, 10);

    if (isNaN(parsedUnitCost) || parsedUnitCost < 0) {
      setErrorMsg("Unit cost must be a valid non-negative number.");
      return;
    }
    if (isNaN(parsedSalesPrice) || parsedSalesPrice < 0) {
      setErrorMsg("Sales price must be a valid non-negative number.");
      return;
    }
    if (isNaN(parsedLeadTime) || parsedLeadTime < 0) {
      setErrorMsg("Lead time must be a valid non-negative integer.");
      return;
    }

    setIsSubmitting(true);
    try {
      await apiClient(`/products/skus/${sku.id}`, {
        method: "PUT",
        body: JSON.stringify({
          sku_code: cleanSkuCode,
          unit_cost: parsedUnitCost.toFixed(2),
          sales_price: parsedSalesPrice.toFixed(2),
          lead_time_days: parsedLeadTime,
        }),
      });

      onSuccess();
      onClose();
    } catch (err) {
      if (err instanceof ApiError) {
        setErrorMsg(err.message || "Failed to update SKU.");
      } else if (err instanceof Error) {
        setErrorMsg(err.message);
      } else {
        setErrorMsg("An unexpected error occurred while updating the SKU.");
      }
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/40 backdrop-blur-sm animate-in fade-in duration-200">
      <div className="bg-white rounded-lg shadow-xl max-w-md w-full border border-[#cbd5e1] overflow-hidden">
        {/* Header */}
        <div className="p-4 bg-[#f8fafc] border-b border-[#e2e8f0] flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-full bg-[#eff6ff] text-[#2563eb] flex items-center justify-center shrink-0">
              <Edit2 className="w-4 h-4" />
            </div>
            <div>
              <h2 className="text-sm font-bold text-[#0f172a]">
                Edit Product SKU
              </h2>
              <p className="text-[11px] text-[#64748b]">
                {sku.product_name || "Catalog Product"}
              </p>
            </div>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="p-1 rounded text-[#64748b] hover:bg-[#f1f5f9]"
            aria-label="Close dialog"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Content Form */}
        <form onSubmit={handleSubmit} className="p-4 space-y-4">
          {errorMsg && (
            <div
              role="alert"
              className="p-3 rounded bg-[#fef2f2] border border-[#fecaca] text-[#dc2626] text-xs flex items-start gap-2"
            >
              <AlertCircle className="w-4 h-4 shrink-0 mt-0.5" />
              <span>{errorMsg}</span>
            </div>
          )}

          <div>
            <label
              htmlFor="editSkuCodeInput"
              className="block text-xs font-semibold text-[#0f172a] mb-1"
            >
              SKU Code
            </label>
            <input
              id="editSkuCodeInput"
              type="text"
              required
              value={skuCode}
              onChange={(e) => setSkuCode(e.target.value)}
              placeholder="e.g. ELEC-PHN-001"
              className="w-full h-9 px-3 text-xs bg-white border border-[#cbd5e1] rounded-[4px] focus:outline-none focus:border-[#2563eb] font-mono"
            />
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label
                htmlFor="editUnitCostInput"
                className="block text-xs font-semibold text-[#0f172a] mb-1"
              >
                Unit Cost ($)
              </label>
              <input
                id="editUnitCostInput"
                type="number"
                step="0.01"
                min="0"
                required
                value={unitCost}
                onChange={(e) => setUnitCost(e.target.value)}
                placeholder="0.00"
                className="w-full h-9 px-3 text-xs bg-white border border-[#cbd5e1] rounded-[4px] focus:outline-none focus:border-[#2563eb] font-mono"
              />
            </div>
            <div>
              <label
                htmlFor="editSalesPriceInput"
                className="block text-xs font-semibold text-[#0f172a] mb-1"
              >
                Sales Price ($)
              </label>
              <input
                id="editSalesPriceInput"
                type="number"
                step="0.01"
                min="0"
                required
                value={salesPrice}
                onChange={(e) => setSalesPrice(e.target.value)}
                placeholder="0.00"
                className="w-full h-9 px-3 text-xs bg-white border border-[#cbd5e1] rounded-[4px] focus:outline-none focus:border-[#2563eb] font-mono"
              />
            </div>
          </div>

          <div>
            <label
              htmlFor="editLeadTimeInput"
              className="block text-xs font-semibold text-[#0f172a] mb-1"
            >
              Supplier Lead Time (Days)
            </label>
            <input
              id="editLeadTimeInput"
              type="number"
              min="0"
              required
              value={leadTimeDays}
              onChange={(e) => setLeadTimeDays(e.target.value)}
              placeholder="7"
              className="w-full h-9 px-3 text-xs bg-white border border-[#cbd5e1] rounded-[4px] focus:outline-none focus:border-[#2563eb]"
            />
          </div>

          <div className="flex items-center justify-end gap-2 pt-3 border-t border-[#f1f5f9]">
            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={onClose}
              disabled={isSubmitting}
            >
              Cancel
            </Button>
            <Button
              type="submit"
              variant="primary"
              size="sm"
              disabled={isSubmitting}
              isLoading={isSubmitting}
            >
              Save Changes
            </Button>
          </div>
        </form>
      </div>
    </div>
  );
}
