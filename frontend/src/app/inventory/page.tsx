"use client";

import React, { useState, useEffect } from "react";
import { useQuery } from "@tanstack/react-query";
import {
  Plus,
  Search,
  RefreshCw,
  SlidersHorizontal,
  AlertTriangle,
  Clock,
  ArrowRightLeft,
} from "lucide-react";
import { Button } from "@/components/ui/Button";
import { Badge } from "@/components/ui/Badge";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/Card";
import { DataTable, ColumnDef } from "@/components/ui/DataTable";
import { CreateSkuModal, CategoryOption } from "@/components/inventory/CreateSkuModal";
import { AdjustStockModal } from "@/components/inventory/AdjustStockModal";
import { TransferStockModal } from "@/components/inventory/TransferStockModal";
import { apiClient } from "@/lib/api-client";
import { useAuth } from "@/hooks/useAuth";

export interface SkuItem {
  id: string;
  tenant_id: string;
  product_id: string;
  sku_code: string;
  supplier_id: string | null;
  unit_cost: string | number;
  sales_price: string | number;
  lead_time_days: number;
  created_at: string;
  product_name?: string | null;
  category_name?: string | null;
}

export interface PaginatedSkusResponse {
  data: SkuItem[];
  meta: {
    total: number;
    page: number;
    limit: number;
    total_pages: number;
  };
}

export interface CategoryItem {
  id: string;
  tenant_id: string;
  name: string;
  parent_id: string | null;
}

export default function InventoryPage() {
  const { user } = useAuth();
  const [page, setPage] = useState<number>(1);
  const [limit] = useState<number>(10);
  const [searchInput, setSearchInput] = useState<string>("");
  const [debouncedSearch, setDebouncedSearch] = useState<string>("");
  const [selectedCategory, setSelectedCategory] = useState<string>("");
  const [sortBy, setSortBy] = useState<string>("created_at");
  const [sortOrder, setSortOrder] = useState<"asc" | "desc">("desc");
  const [isModalOpen, setIsModalOpen] = useState<boolean>(false);
  const [isAdjustModalOpen, setIsAdjustModalOpen] = useState<boolean>(false);
  const [isTransferModalOpen, setIsTransferModalOpen] = useState<boolean>(false);

  // Debounce search input
  useEffect(() => {
    const handler = setTimeout(() => {
      setDebouncedSearch(searchInput);
      setPage(1);
    }, 300);
    return () => clearTimeout(handler);
  }, [searchInput]);

  // Query SKUs
  const {
    data: skusResponse,
    isLoading: isSkusLoading,
    isError: isSkusError,
    error: skusError,
    refetch: refetchSkus,
  } = useQuery<PaginatedSkusResponse>({
    queryKey: [
      "skus",
      page,
      limit,
      debouncedSearch,
      selectedCategory,
      sortBy,
      sortOrder,
    ],
    queryFn: () => {
      const params = new URLSearchParams({
        page: String(page),
        limit: String(limit),
        sort_by: sortBy,
        sort_order: sortOrder,
      });
      if (debouncedSearch.trim()) {
        params.append("search", debouncedSearch.trim());
      }
      if (selectedCategory) {
        params.append("category_id", selectedCategory);
      }
      return apiClient<PaginatedSkusResponse>(`/products/skus?${params.toString()}`);
    },
  });

  // Query Categories
  const { data: categoriesResponse } = useQuery<CategoryItem[]>({
    queryKey: ["categories"],
    queryFn: () => apiClient<CategoryItem[]>("/products/categories"),
  });

  const categories: CategoryOption[] = (categoriesResponse || []).map((cat) => ({
    id: cat.id,
    name: cat.name,
  }));

  const canWriteCatalog =
    user?.role === "Admin" || user?.role === "Inventory Manager";

  const handleSort = (key: string) => {
    if (sortBy === key) {
      setSortOrder(sortOrder === "asc" ? "desc" : "asc");
    } else {
      setSortBy(key);
      setSortOrder("asc");
    }
    setPage(1);
  };

  const formatCurrency = (val: string | number) => {
    const num = typeof val === "number" ? val : parseFloat(val);
    if (isNaN(num)) return "$0.00";
    return new Intl.NumberFormat("en-US", {
      style: "currency",
      currency: "USD",
    }).format(num);
  };

  const columns: ColumnDef<SkuItem>[] = [
    {
      header: "SKU Code",
      accessorKey: "sku_code",
      sortable: true,
      sortKey: "sku_code",
      cell: (row) => (
        <span className="font-mono text-xs font-semibold px-2 py-1 rounded bg-[#f1f5f9] text-[#0f172a] border border-[#e2e8f0]">
          {row.sku_code}
        </span>
      ),
    },
    {
      header: "Product / Category",
      sortable: true,
      sortKey: "product_name",
      cell: (row) => (
        <div className="flex flex-col">
          <span className="font-medium text-[#0f172a]">
            {row.product_name || "Untitled Product"}
          </span>
          <div className="mt-1">
            {row.category_name ? (
              <Badge variant="neutral" className="text-[10px] py-0 px-2">
                {row.category_name}
              </Badge>
            ) : (
              <span className="text-[11px] text-[#94a3b8]">Uncategorized</span>
            )}
          </div>
        </div>
      ),
    },
    {
      header: "Unit Cost",
      accessorKey: "unit_cost",
      sortable: true,
      sortKey: "unit_cost",
      align: "right",
      cell: (row) => (
        <span className="text-xs font-mono text-[#475569]">
          {formatCurrency(row.unit_cost)}
        </span>
      ),
    },
    {
      header: "Sales Price",
      accessorKey: "sales_price",
      sortable: true,
      sortKey: "sales_price",
      align: "right",
      cell: (row) => (
        <span className="text-xs font-mono font-medium text-[#0f172a]">
          {formatCurrency(row.sales_price)}
        </span>
      ),
    },
    {
      header: "Lead Time",
      accessorKey: "lead_time_days",
      sortable: true,
      sortKey: "lead_time_days",
      align: "center",
      cell: (row) => (
        <span className="inline-flex items-center gap-1 text-xs text-[#64748b]">
          <Clock className="w-3.5 h-3.5 text-[#94a3b8]" />
          {row.lead_time_days}d
        </span>
      ),
    },
    {
      header: "Status",
      align: "center",
      cell: () => (
        <Badge variant="success" className="text-[11px]">
          Active
        </Badge>
      ),
    },
  ];

  return (
    <div className="space-y-6">
      {/* Top Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-[#0f172a]">
            Catalog & SKU Management
          </h1>
          <p className="text-sm text-[#64748b] mt-1">
            Centralized master product records, SKU definitions, and multi-location tracking.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={() => refetchSkus()}
            title="Refresh Catalog"
          >
            <RefreshCw className="w-4 h-4 mr-1.5" />
            Refresh
          </Button>
          <Button
            variant="outline"
            size="sm"
            onClick={() => setIsAdjustModalOpen(true)}
            title="Adjust Stock Level"
          >
            <SlidersHorizontal className="w-4 h-4 mr-1.5" />
            Adjust Stock
          </Button>
          <Button
            variant="outline"
            size="sm"
            onClick={() => setIsTransferModalOpen(true)}
            title="Transfer Stock Between Locations"
          >
            <ArrowRightLeft className="w-4 h-4 mr-1.5" />
            Transfer Stock
          </Button>
          {canWriteCatalog && (
            <Button
              variant="primary"
              size="sm"
              onClick={() => setIsModalOpen(true)}
            >
              <Plus className="w-4 h-4 mr-1.5" />
              Add SKU
            </Button>
          )}
        </div>
      </div>

      {/* Main Content Card */}
      <Card>
        <CardHeader>
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
            <div>
              <CardTitle>Catalog Master SKUs</CardTitle>
              <CardDescription className="mt-1">
                Filter by product category or search by SKU code and product name.
              </CardDescription>
            </div>
            <div className="flex items-center gap-2">
              <span className="text-xs text-[#64748b]">
                Total Items:{" "}
                <span className="font-semibold text-[#0f172a]">
                  {skusResponse?.meta.total ?? 0}
                </span>
              </span>
            </div>
          </div>

          {/* Filters Bar */}
          <div className="flex flex-col sm:flex-row items-center gap-3 pt-3">
            <div className="relative w-full sm:w-72">
              <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-[#94a3b8]" />
              <input
                type="text"
                value={searchInput}
                onChange={(e) => setSearchInput(e.target.value)}
                placeholder="Search SKU or product..."
                className="w-full h-9 pl-9 pr-3 text-xs rounded-[4px] border border-[#cbd5e1] bg-white text-[#0f172a] placeholder-[#94a3b8] focus:outline-none focus:ring-2 focus:ring-[#2563eb] focus:border-transparent"
              />
            </div>

            <div className="flex items-center gap-2 w-full sm:w-auto">
              <div className="relative w-full sm:w-56">
                <SlidersHorizontal className="w-3.5 h-3.5 absolute left-3 top-1/2 -translate-y-1/2 text-[#94a3b8]" />
                <select
                  value={selectedCategory}
                  onChange={(e) => {
                    setSelectedCategory(e.target.value);
                    setPage(1);
                  }}
                  className="w-full h-9 pl-8 pr-3 text-xs rounded-[4px] border border-[#cbd5e1] bg-white text-[#0f172a] focus:outline-none focus:ring-2 focus:ring-[#2563eb] focus:border-transparent"
                >
                  <option value="">All Categories</option>
                  {categories.map((c) => (
                    <option key={c.id} value={c.id}>
                      {c.name}
                    </option>
                  ))}
                </select>
              </div>

              {(searchInput || selectedCategory) && (
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => {
                    setSearchInput("");
                    setSelectedCategory("");
                    setPage(1);
                  }}
                  className="text-xs h-9"
                >
                  Clear Filters
                </Button>
              )}
            </div>
          </div>
        </CardHeader>

        <CardContent>
          {isSkusError ? (
            <div className="flex flex-col items-center justify-center py-12 text-center rounded-lg border border-[#fecaca] bg-[#fef2f2] p-6 text-xs text-[#dc2626]">
              <AlertTriangle className="w-8 h-8 text-[#dc2626] mb-2" />
              <p className="font-semibold text-sm">Unable to load catalog data</p>
              <p className="text-[#991b1b] mt-1 max-w-md">
                {(skusError as Error)?.message || "A network or server error occurred."}
              </p>
              <Button
                variant="outline"
                size="sm"
                onClick={() => refetchSkus()}
                className="mt-4 border-[#fca5a5] text-[#b91c1c] hover:bg-[#fee2e2]"
              >
                Retry Request
              </Button>
            </div>
          ) : (
            <DataTable<SkuItem>
              columns={columns}
              data={skusResponse?.data || []}
              isLoading={isSkusLoading}
              sortBy={sortBy}
              sortOrder={sortOrder}
              onSort={handleSort}
              emptyTitle="No catalog SKUs found"
              emptyDescription={
                debouncedSearch || selectedCategory
                  ? "No SKUs match your active filter criteria. Try resetting your search."
                  : "Get started by adding your first product SKU to the catalog master."
              }
              emptyAction={
                canWriteCatalog && !debouncedSearch && !selectedCategory ? (
                  <Button
                    variant="primary"
                    size="sm"
                    onClick={() => setIsModalOpen(true)}
                  >
                    <Plus className="w-4 h-4 mr-1.5" />
                    Create First SKU
                  </Button>
                ) : undefined
              }
              pagination={
                skusResponse?.meta
                  ? {
                      page: skusResponse.meta.page,
                      limit: skusResponse.meta.limit,
                      total: skusResponse.meta.total,
                      totalPages: skusResponse.meta.total_pages,
                      onPageChange: (newPage) => setPage(newPage),
                    }
                  : undefined
              }
            />
          )}
        </CardContent>
      </Card>

      {/* Create SKU Modal */}
      <CreateSkuModal
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        onSuccess={() => {
          refetchSkus();
        }}
        categories={categories}
      />

      {/* Adjust Stock Modal */}
      <AdjustStockModal
        isOpen={isAdjustModalOpen}
        onClose={() => setIsAdjustModalOpen(false)}
        onSuccess={() => {
          refetchSkus();
        }}
      />

      {/* Transfer Stock Modal */}
      <TransferStockModal
        isOpen={isTransferModalOpen}
        onClose={() => setIsTransferModalOpen(false)}
        onSuccess={() => {
          refetchSkus();
        }}
      />
    </div>
  );
}
