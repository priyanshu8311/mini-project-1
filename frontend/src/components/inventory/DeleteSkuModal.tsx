"use client";

import React, { useState } from "react";
import { AlertCircle, AlertTriangle, ShieldAlert, X } from "lucide-react";
import { Button } from "@/components/ui/Button";
import { apiClient, ApiError, SkuDeleteResponse } from "@/lib/api-client";
import { SkuItem } from "@/app/inventory/page";

export interface DeleteSkuModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccess: (message: string) => void;
  sku: SkuItem | null;
}

export function DeleteSkuModal({
  isOpen,
  onClose,
  onSuccess,
  sku,
}: DeleteSkuModalProps) {
  const [confirmationCode, setConfirmationCode] = useState("");
  const [isDeleting, setIsDeleting] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const [prevProps, setPrevProps] = useState({ isOpen, skuId: sku?.id });
  if (isOpen !== prevProps.isOpen || sku?.id !== prevProps.skuId) {
    setPrevProps({ isOpen, skuId: sku?.id });
    setConfirmationCode("");
    setErrorMessage(null);
  }

  if (!isOpen || !sku) return null;

  const isConfirmed =
    confirmationCode.trim().toUpperCase() === sku.sku_code.trim().toUpperCase();

  const handleDelete = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!isConfirmed) return;

    setIsDeleting(true);
    setErrorMessage(null);

    try {
      const response = await apiClient<SkuDeleteResponse>(
        `/products/skus/${sku.id}`,
        {
          method: "DELETE",
        }
      );

      onSuccess(
        response.message ||
          `SKU '${sku.sku_code}' has been processed successfully.`
      );
      onClose();
    } catch (err) {
      if (err instanceof ApiError) {
        setErrorMessage(err.message || "Failed to delete SKU.");
      } else if (err instanceof Error) {
        setErrorMessage(err.message);
      } else {
        setErrorMessage("An unexpected error occurred while deleting the SKU.");
      }
    } finally {
      setIsDeleting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/40 backdrop-blur-sm animate-in fade-in duration-200">
      <div className="bg-white rounded-lg shadow-xl max-w-md w-full border border-[#fecaca] overflow-hidden">
        {/* Header */}
        <div className="p-4 bg-[#fef2f2] border-b border-[#fecaca] flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-full bg-[#fee2e2] text-[#dc2626] flex items-center justify-center shrink-0">
              <AlertTriangle className="w-4 h-4" />
            </div>
            <div>
              <h2 className="text-sm font-bold text-[#991b1b]">
                Delete Product SKU
              </h2>
              <p className="text-[11px] text-[#b91c1c]">
                Review dependencies and confirm removal
              </p>
            </div>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="p-1 rounded text-[#991b1b] hover:bg-[#fee2e2]"
            aria-label="Close dialog"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Content & Form */}
        <form onSubmit={handleDelete} className="p-4 space-y-4">
          {errorMessage && (
            <div
              role="alert"
              className="p-3 rounded bg-[#fef2f2] border border-[#fecaca] text-[#dc2626] text-xs flex items-start gap-2"
            >
              <AlertCircle className="w-4 h-4 shrink-0 mt-0.5" />
              <span className="leading-relaxed">{errorMessage}</span>
            </div>
          )}

          {/* Target SKU Card */}
          <div className="space-y-1.5">
            <p className="text-xs text-[#334155] leading-relaxed">
              Are you sure you want to delete this product SKU variant?
            </p>
            <div className="p-3 bg-[#f8fafc] border border-[#e2e8f0] rounded-md space-y-1">
              <div className="flex items-center justify-between">
                <span className="font-mono text-xs font-bold text-[#0f172a] bg-[#f1f5f9] px-2 py-0.5 rounded border border-[#cbd5e1]">
                  {sku.sku_code}
                </span>
                <span className="text-[11px] text-[#64748b]">
                  {sku.category_name || "Uncategorized"}
                </span>
              </div>
              <p className="text-sm font-semibold text-[#0f172a] pt-1">
                {sku.product_name || "Untitled Product"}
              </p>
            </div>
          </div>

          {/* Business Dependency & Archival Notice */}
          <div className="p-3 rounded bg-[#fffbeb] border border-[#fef3c7] text-[#92400e] text-[11px] space-y-1">
            <p className="font-semibold flex items-center gap-1.5">
              <ShieldAlert className="w-3.5 h-3.5 shrink-0" />
              Stock & Transaction Integrity
            </p>
            <ul className="list-disc list-inside space-y-0.5 text-[#b45309]">
              <li>Cannot delete if physical stock on hand is greater than 0.</li>
              <li>
                If historical transactions, sales, or POs exist, the SKU is
                archived to preserve audit logs.
              </li>
              <li>If no history exists, the SKU is permanently removed.</li>
            </ul>
          </div>

          {/* Confirmation Input */}
          <div className="space-y-1.5">
            <label
              htmlFor="confirmSkuCodeInput"
              className="block text-xs font-semibold text-[#0f172a]"
            >
              Type{" "}
              <span className="font-mono text-[#dc2626] font-bold">
                {sku.sku_code}
              </span>{" "}
              to confirm:
            </label>
            <input
              id="confirmSkuCodeInput"
              type="text"
              required
              autoFocus
              value={confirmationCode}
              onChange={(e) => setConfirmationCode(e.target.value)}
              placeholder={sku.sku_code}
              className="w-full h-9 px-3 text-xs bg-white border border-[#cbd5e1] rounded-[4px] focus:outline-none focus:border-[#dc2626]"
            />
          </div>

          {/* Action Buttons */}
          <div className="flex items-center justify-end gap-2 pt-3 border-t border-[#f1f5f9]">
            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={onClose}
              disabled={isDeleting}
            >
              Cancel
            </Button>
            <Button
              type="submit"
              size="sm"
              disabled={!isConfirmed || isDeleting}
              isLoading={isDeleting}
              className="bg-[#dc2626] hover:bg-[#b91c1c] text-white focus:ring-[#dc2626]"
            >
              Confirm Deletion
            </Button>
          </div>
        </form>
      </div>
    </div>
  );
}
