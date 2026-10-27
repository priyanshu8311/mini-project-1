"use client";

import React, { useState } from "react";
import {
  Plus,
  RefreshCw,
  ShoppingBag,
  PackageCheck,
  Clock,
  CheckCircle,
  Truck,
  ArrowRight,
} from "lucide-react";
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Skeleton } from "@/components/ui/Skeleton";
import {
  usePurchaseOrders,
  usePurchasingSuggestions,
} from "@/hooks/usePurchasing";
import { CreatePoModal } from "@/components/inventory/CreatePoModal";
import { ReceivePoModal } from "@/components/purchasing/ReceivePoModal";
import { PurchaseOrder, PurchasingSuggestion } from "@/lib/api-client";

export default function PurchasingPage() {
  const [statusFilter, setStatusFilter] = useState<string>("");
  const [page, setPage] = useState<number>(1);
  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false);
  const [receivingPo, setReceivingPo] = useState<PurchaseOrder | null>(null);
  const [selectedSuggestion, setSelectedSuggestion] = useState<PurchasingSuggestion | null>(null);

  // Queries
  const {
    data: poData,
    isLoading: isPoLoading,
    refetch: refetchPos,
  } = usePurchaseOrders({
    status: statusFilter || undefined,
    page,
    limit: 50,
  });

  const {
    data: suggestions,
    isLoading: isSuggestionsLoading,
    refetch: refetchSuggestions,
  } = usePurchasingSuggestions();

  const purchaseOrders = poData?.data || [];
  const suggestionList = suggestions || [];

  // Metrics
  const activeOrdersCount = poData?.meta?.total || purchaseOrders.length;
  const pendingReceiptCount = purchaseOrders.filter(
    (po) => po.status === "Sent" || po.status === "Partially Received"
  ).length;
  const completedCount = purchaseOrders.filter((po) => po.status === "Completed").length;

  const handleRefresh = () => {
    refetchPos();
    refetchSuggestions();
  };

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-[#0f172a]">
            Replenishment & Purchase Orders
          </h1>
          <p className="text-sm text-[#64748b] mt-1">
            Vendor purchase order workflows, atomic goods receipt, and lead-time-aware stock replenishment.
          </p>
        </div>
        <div className="flex items-center gap-3">
          <Button variant="outline" size="sm" onClick={handleRefresh}>
            <RefreshCw className="w-4 h-4 mr-1.5" />
            Refresh
          </Button>
          <Button variant="primary" size="sm" onClick={() => setIsCreateModalOpen(true)}>
            <Plus className="w-4 h-4 mr-1.5" />
            Create Purchase Order
          </Button>
        </div>
      </div>

      {/* Metrics Row */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold uppercase tracking-wider text-[#64748b]">
                Total Orders
              </span>
              <div className="p-2 rounded-lg bg-[#eff6ff] text-[#2563eb]">
                <ShoppingBag className="w-4 h-4" />
              </div>
            </div>
            <p className="text-2xl font-bold text-[#0f172a] mt-2">{activeOrdersCount}</p>
            <span className="text-xs text-[#64748b]">Across all statuses</span>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold uppercase tracking-wider text-[#64748b]">
                Awaiting Delivery
              </span>
              <div className="p-2 rounded-lg bg-[#fffbeb] text-[#d97706]">
                <Truck className="w-4 h-4" />
              </div>
            </div>
            <p className="text-2xl font-bold text-[#0f172a] mt-2">{pendingReceiptCount}</p>
            <span className="text-xs text-[#d97706]">Sent or Partially Received</span>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold uppercase tracking-wider text-[#64748b]">
                Reorder Suggestions
              </span>
              <div className="p-2 rounded-lg bg-[#fef2f2] text-[#dc2626]">
                <Clock className="w-4 h-4" />
              </div>
            </div>
            <p className="text-2xl font-bold text-[#0f172a] mt-2">{suggestionList.length}</p>
            <span className="text-xs text-[#64748b]">Items below safety threshold</span>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold uppercase tracking-wider text-[#64748b]">
                Completed Orders
              </span>
              <div className="p-2 rounded-lg bg-[#f0fdf4] text-[#16a34a]">
                <CheckCircle className="w-4 h-4" />
              </div>
            </div>
            <p className="text-2xl font-bold text-[#0f172a] mt-2">{completedCount}</p>
            <span className="text-xs text-[#16a34a]">Fully restocked to inventory</span>
          </CardContent>
        </Card>
      </div>

      {/* Suggested Reorders Panel */}
      {suggestionList.length > 0 && (
        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <div>
                <CardTitle>Automated Replenishment Suggestions</CardTitle>
                <CardDescription>
                  Items currently at or below reorder points requiring vendor replenishment.
                </CardDescription>
              </div>
              <Badge variant="warning">{suggestionList.length} Items</Badge>
            </div>
          </CardHeader>
          <CardContent>
            {isSuggestionsLoading ? (
              <Skeleton className="h-20 w-full" />
            ) : (
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
                {suggestionList.slice(0, 6).map((item) => (
                  <div
                    key={item.sku_id}
                    className="p-3.5 border border-[#e2e8f0] rounded-lg bg-[#f8fafc] flex flex-col justify-between gap-3"
                  >
                    <div>
                      <div className="flex items-center justify-between gap-2">
                        <span className="font-semibold text-sm text-[#0f172a] truncate">
                          {item.sku_code}
                        </span>
                        <Badge
                          variant={
                            item.urgency === "High"
                              ? "error"
                              : item.urgency === "Medium"
                              ? "warning"
                              : "neutral"
                          }
                        >
                          {item.urgency}
                        </Badge>
                      </div>
                      {item.product_name && (
                        <p className="text-xs text-[#64748b] truncate mt-0.5">{item.product_name}</p>
                      )}
                      <p className="text-xs text-[#475569] mt-2">
                        On Hand: <strong className="text-[#0f172a]">{item.current_on_hand}</strong> / ROP:{" "}
                        {item.reorder_point}
                      </p>
                    </div>

                    <div className="flex items-center justify-between pt-2 border-t border-[#e2e8f0]">
                      <span className="text-xs font-medium text-[#2563eb]">
                        Order: +{item.suggested_reorder_quantity}
                      </span>
                      <Button
                        variant="primary"
                        size="sm"
                        onClick={() => setSelectedSuggestion(item)}
                      >
                        Create PO
                        <ArrowRight className="w-3.5 h-3.5 ml-1" />
                      </Button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      )}

      {/* Purchase Orders Table */}
      <Card>
        <CardHeader>
          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
            <div>
              <CardTitle>Purchase Order Register</CardTitle>
              <CardDescription>
                Track draft, sent, and received vendor orders.
              </CardDescription>
            </div>
            {/* Status Filter Tabs */}
            <div className="flex flex-wrap gap-1 bg-[#f1f5f9] p-1 rounded-lg">
              {["", "Draft", "Sent", "Partially Received", "Completed"].map((st) => (
                <button
                  key={st}
                  onClick={() => setStatusFilter(st)}
                  className={`px-3 py-1 text-xs font-semibold rounded-md transition-colors ${
                    statusFilter === st
                      ? "bg-white text-[#0f172a] shadow-xs"
                      : "text-[#64748b] hover:text-[#0f172a]"
                  }`}
                >
                  {st || "All"}
                </button>
              ))}
            </div>
          </div>
        </CardHeader>
        <CardContent>
          {isPoLoading ? (
            <div className="space-y-3">
              <Skeleton className="h-12 w-full" />
              <Skeleton className="h-12 w-full" />
              <Skeleton className="h-12 w-full" />
            </div>
          ) : purchaseOrders.length === 0 ? (
            <div className="py-12 text-center text-sm text-[#64748b] border border-dashed border-[#cbd5e1] rounded-lg">
              <p className="font-medium text-[#0f172a]">No purchase orders found</p>
              <p className="text-xs text-[#94a3b8] mt-1">
                {statusFilter
                  ? `No orders currently matching status "${statusFilter}".`
                  : "Click 'Create Purchase Order' to initiate vendor replenishment."}
              </p>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-left text-sm border-collapse">
                <thead>
                  <tr className="border-b border-[#e2e8f0] text-xs font-semibold uppercase tracking-wider text-[#64748b]">
                    <th className="py-3 px-4">PO Reference</th>
                    <th className="py-3 px-4">Status</th>
                    <th className="py-3 px-4">Items / Ordered</th>
                    <th className="py-3 px-4">Expected Delivery</th>
                    <th className="py-3 px-4">Created Date</th>
                    <th className="py-3 px-4 text-right">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-[#f1f5f9]">
                  {purchaseOrders.map((po) => {
                    const totalOrdered = po.items.reduce((acc, i) => acc + i.quantity_ordered, 0);
                    const totalReceived = po.items.reduce((acc, i) => acc + i.quantity_received, 0);
                    const isFullyReceived = po.status === "Completed";

                    const statusVariant: "success" | "warning" | "info" | "neutral" =
                      po.status === "Completed"
                        ? "success"
                        : po.status === "Partially Received"
                        ? "warning"
                        : po.status === "Sent"
                        ? "info"
                        : "neutral";

                    return (
                      <tr key={po.id} className="hover:bg-[#f8fafc] transition-colors">
                        <td className="py-3.5 px-4 font-mono font-medium text-[#0f172a]">
                          PO-{po.id.slice(0, 8).toUpperCase()}
                        </td>
                        <td className="py-3.5 px-4">
                          <Badge variant={statusVariant}>{po.status}</Badge>
                        </td>
                        <td className="py-3.5 px-4 text-[#475569]">
                          <span className="font-semibold text-[#0f172a]">{po.items.length} line items</span>
                          <div className="text-xs text-[#64748b]">
                            {totalReceived} / {totalOrdered} units received
                          </div>
                        </td>
                        <td className="py-3.5 px-4 text-[#475569]">
                          {po.expected_date ? (
                            <span className="flex items-center gap-1.5">
                              <Clock className="w-3.5 h-3.5 text-[#94a3b8]" />
                              {po.expected_date}
                            </span>
                          ) : (
                            <span className="text-[#94a3b8] italic">Unscheduled</span>
                          )}
                        </td>
                        <td className="py-3.5 px-4 text-xs text-[#64748b]">
                          {new Date(po.created_at).toLocaleDateString()}
                        </td>
                        <td className="py-3.5 px-4 text-right">
                          {!isFullyReceived && (
                            <Button
                              variant="outline"
                              size="sm"
                              onClick={() => setReceivingPo(po)}
                            >
                              <PackageCheck className="w-3.5 h-3.5 mr-1" />
                              Receive Goods
                            </Button>
                          )}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>

              {poData?.meta && poData.meta.total_pages > 1 && (
                <div className="flex items-center justify-between pt-4 border-t border-[#e2e8f0]">
                  <span className="text-xs text-[#64748b]">
                    Page {poData.meta.page} of {poData.meta.total_pages}
                  </span>
                  <div className="flex gap-2">
                    <Button
                      variant="outline"
                      size="sm"
                      disabled={page <= 1}
                      onClick={() => setPage((p) => Math.max(1, p - 1))}
                    >
                      Previous
                    </Button>
                    <Button
                      variant="outline"
                      size="sm"
                      disabled={page >= poData.meta.total_pages}
                      onClick={() => setPage((p) => p + 1)}
                    >
                      Next
                    </Button>
                  </div>
                </div>
              )}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Create PO Modal */}
      {(isCreateModalOpen || selectedSuggestion) && (
        <CreatePoModal
          isOpen={true}
          onClose={() => {
            setIsCreateModalOpen(false);
            setSelectedSuggestion(null);
          }}
          onSuccess={() => {
            setIsCreateModalOpen(false);
            setSelectedSuggestion(null);
            handleRefresh();
          }}
          initialSkuId={selectedSuggestion?.sku_id}
          initialSkuCode={selectedSuggestion?.sku_code}
          initialQuantity={selectedSuggestion?.suggested_reorder_quantity}
          initialUnitCost={selectedSuggestion?.unit_cost}
        />
      )}

      {/* Receive PO Modal */}
      {receivingPo && (
        <ReceivePoModal
          isOpen={true}
          onClose={() => setReceivingPo(null)}
          onSuccess={() => {
            setReceivingPo(null);
            handleRefresh();
          }}
          purchaseOrder={receivingPo}
        />
      )}
    </div>
  );
}
