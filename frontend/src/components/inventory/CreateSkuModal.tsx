import React, { useState } from "react";
import { X, AlertCircle } from "lucide-react";
import { Button } from "@/components/ui/Button";
import { apiClient, ApiError } from "@/lib/api-client";

export interface CategoryOption {
  id: string;
  name: string;
}

export interface CreateSkuModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccess: () => void;
  categories: CategoryOption[];
}

export function CreateSkuModal({
  isOpen,
  onClose,
  onSuccess,
  categories,
}: CreateSkuModalProps) {
  const [skuCode, setSkuCode] = useState("");
  const [productName, setProductName] = useState("");
  const [categoryId, setCategoryId] = useState("");
  const [unitCost, setUnitCost] = useState("0.00");
  const [salesPrice, setSalesPrice] = useState("0.00");
  const [leadTimeDays, setLeadTimeDays] = useState("7");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  if (!isOpen) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMsg(null);

    const cleanSkuCode = skuCode.trim().toUpperCase();
    const cleanProductName = productName.trim();

    if (!cleanSkuCode) {
      setErrorMsg("SKU code is required.");
      return;
    }
    if (!cleanProductName) {
      setErrorMsg("Product name is required.");
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
      await apiClient("/products/skus", {
        method: "POST",
        body: JSON.stringify({
          sku_code: cleanSkuCode,
          product_name: cleanProductName,
          category_id: categoryId ? categoryId : null,
          unit_cost: parsedUnitCost.toFixed(2),
          sales_price: parsedSalesPrice.toFixed(2),
          lead_time_days: parsedLeadTime,
        }),
      });

      // Reset form
      setSkuCode("");
      setProductName("");
      setCategoryId("");
      setUnitCost("0.00");
      setSalesPrice("0.00");
      setLeadTimeDays("7");
      onSuccess();
      onClose();
    } catch (err) {
      if (err instanceof ApiError) {
        setErrorMsg(err.message || "Failed to create SKU.");
      } else if (err instanceof Error) {
        setErrorMsg(err.message);
      } else {
        setErrorMsg("An unexpected error occurred while creating the SKU.");
      }
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="modal-title"
      className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/50 backdrop-blur-xs transition-opacity"
    >
      <div className="relative w-full max-w-lg rounded-lg border border-[#e2e8f0] bg-white p-6 shadow-xl space-y-5 animate-in fade-in zoom-in-95 duration-150">
        <div className="flex items-center justify-between border-b border-[#f1f5f9] pb-4">
          <div>
            <h2 id="modal-title" className="text-lg font-semibold text-[#0f172a]">
              Add New Catalog SKU
            </h2>
            <p className="text-xs text-[#64748b] mt-0.5">
              Create a new stock-keeping unit with product specifications and pricing.
            </p>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="rounded-md p-1.5 text-[#64748b] hover:bg-[#f1f5f9] hover:text-[#0f172a] focus:outline-none focus:ring-2 focus:ring-[#2563eb]"
            aria-label="Close dialog"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {errorMsg && (
          <div className="flex items-start gap-2.5 rounded-md border border-[#fecaca] bg-[#fef2f2] p-3 text-xs text-[#dc2626]">
            <AlertCircle className="w-4 h-4 shrink-0 mt-0.5" />
            <div className="flex-1 font-medium">{errorMsg}</div>
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div className="space-y-1.5 sm:col-span-1">
              <label htmlFor="sku-code" className="block text-xs font-medium text-[#0f172a]">
                SKU Code <span className="text-[#dc2626]">*</span>
              </label>
              <input
                id="sku-code"
                type="text"
                required
                value={skuCode}
                onChange={(e) => setSkuCode(e.target.value.toUpperCase())}
                placeholder="e.g. ELEC-KEY-001"
                className="w-full h-10 px-3 text-sm rounded-[4px] border border-[#cbd5e1] bg-white text-[#0f172a] placeholder-[#94a3b8] focus:outline-none focus:ring-2 focus:ring-[#2563eb] focus:border-transparent font-mono"
              />
            </div>

            <div className="space-y-1.5 sm:col-span-1">
              <label htmlFor="category-select" className="block text-xs font-medium text-[#0f172a]">
                Category
              </label>
              <select
                id="category-select"
                value={categoryId}
                onChange={(e) => setCategoryId(e.target.value)}
                className="w-full h-10 px-3 text-sm rounded-[4px] border border-[#cbd5e1] bg-white text-[#0f172a] focus:outline-none focus:ring-2 focus:ring-[#2563eb] focus:border-transparent"
              >
                <option value="">Select Category (Optional)</option>
                {categories.map((cat) => (
                  <option key={cat.id} value={cat.id}>
                    {cat.name}
                  </option>
                ))}
              </select>
            </div>
          </div>

          <div className="space-y-1.5">
            <label htmlFor="product-name" className="block text-xs font-medium text-[#0f172a]">
              Product Name <span className="text-[#dc2626]">*</span>
            </label>
            <input
              id="product-name"
              type="text"
              required
              value={productName}
              onChange={(e) => setProductName(e.target.value)}
              placeholder="e.g. Mechanical Ergonomic Keyboard"
              className="w-full h-10 px-3 text-sm rounded-[4px] border border-[#cbd5e1] bg-white text-[#0f172a] placeholder-[#94a3b8] focus:outline-none focus:ring-2 focus:ring-[#2563eb] focus:border-transparent"
            />
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
            <div className="space-y-1.5">
              <label htmlFor="unit-cost" className="block text-xs font-medium text-[#0f172a]">
                Unit Cost ($)
              </label>
              <input
                id="unit-cost"
                type="number"
                step="0.01"
                min="0"
                value={unitCost}
                onChange={(e) => setUnitCost(e.target.value)}
                className="w-full h-10 px-3 text-sm rounded-[4px] border border-[#cbd5e1] bg-white text-[#0f172a] focus:outline-none focus:ring-2 focus:ring-[#2563eb] focus:border-transparent"
              />
            </div>

            <div className="space-y-1.5">
              <label htmlFor="sales-price" className="block text-xs font-medium text-[#0f172a]">
                Sales Price ($)
              </label>
              <input
                id="sales-price"
                type="number"
                step="0.01"
                min="0"
                value={salesPrice}
                onChange={(e) => setSalesPrice(e.target.value)}
                className="w-full h-10 px-3 text-sm rounded-[4px] border border-[#cbd5e1] bg-white text-[#0f172a] focus:outline-none focus:ring-2 focus:ring-[#2563eb] focus:border-transparent"
              />
            </div>

            <div className="space-y-1.5">
              <label htmlFor="lead-time" className="block text-xs font-medium text-[#0f172a]">
                Lead Time (days)
              </label>
              <input
                id="lead-time"
                type="number"
                step="1"
                min="0"
                value={leadTimeDays}
                onChange={(e) => setLeadTimeDays(e.target.value)}
                className="w-full h-10 px-3 text-sm rounded-[4px] border border-[#cbd5e1] bg-white text-[#0f172a] focus:outline-none focus:ring-2 focus:ring-[#2563eb] focus:border-transparent"
              />
            </div>
          </div>

          <div className="flex items-center justify-end gap-2 pt-4 border-t border-[#f1f5f9]">
            <Button
              type="button"
              variant="outline"
              size="md"
              onClick={onClose}
              disabled={isSubmitting}
            >
              Cancel
            </Button>
            <Button
              type="submit"
              variant="primary"
              size="md"
              isLoading={isSubmitting}
            >
              Create SKU
            </Button>
          </div>
        </form>
      </div>
    </div>
  );
}
