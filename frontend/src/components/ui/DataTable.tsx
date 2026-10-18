import React from "react";
import { ArrowDown, ArrowUp, ArrowUpDown, ChevronLeft, ChevronRight } from "lucide-react";
import { cn } from "@/lib/utils";
import { Button } from "./Button";
import { Skeleton } from "./Skeleton";

export interface ColumnDef<T> {
  header: string;
  accessorKey?: keyof T;
  cell?: (row: T) => React.ReactNode;
  sortable?: boolean;
  sortKey?: string;
  className?: string;
  align?: "left" | "center" | "right";
}

export interface PaginationProps {
  page: number;
  limit: number;
  total: number;
  totalPages: number;
  onPageChange: (page: number) => void;
}

export interface DataTableProps<T> {
  columns: ColumnDef<T>[];
  data: T[];
  isLoading?: boolean;
  emptyTitle?: string;
  emptyDescription?: string;
  emptyAction?: React.ReactNode;
  pagination?: PaginationProps;
  sortBy?: string;
  sortOrder?: "asc" | "desc";
  onSort?: (key: string) => void;
  className?: string;
}

export function DataTable<T extends { id?: string | number }>({
  columns,
  data,
  isLoading = false,
  emptyTitle = "No records found",
  emptyDescription = "There are currently no items to display matching the criteria.",
  emptyAction,
  pagination,
  sortBy,
  sortOrder = "desc",
  onSort,
  className,
}: DataTableProps<T>) {
  const getSortIcon = (col: ColumnDef<T>) => {
    const key = col.sortKey || (col.accessorKey as string);
    if (!col.sortable || !key) return null;
    if (sortBy === key) {
      return sortOrder === "asc" ? (
        <ArrowUp className="w-3.5 h-3.5 text-[#2563eb]" />
      ) : (
        <ArrowDown className="w-3.5 h-3.5 text-[#2563eb]" />
      );
    }
    return <ArrowUpDown className="w-3.5 h-3.5 text-[#94a3b8] opacity-50 hover:opacity-100" />;
  };

  const handleHeaderClick = (col: ColumnDef<T>) => {
    const key = col.sortKey || (col.accessorKey as string);
    if (col.sortable && key && onSort) {
      onSort(key);
    }
  };

  const skeletonRows = Array.from({ length: 5 });

  return (
    <div className={cn("w-full space-y-4", className)}>
      <div className="overflow-x-auto rounded-lg border border-[#e2e8f0] bg-white shadow-xs">
        <table className="w-full text-left text-sm text-[#0f172a] border-collapse">
          <thead className="bg-[#f8fafc] border-b border-[#e2e8f0] text-xs font-semibold uppercase tracking-wider text-[#475569]">
            <tr>
              {columns.map((col, idx) => {
                const isSortable = col.sortable && (col.sortKey || col.accessorKey);
                return (
                  <th
                    key={idx}
                    scope="col"
                    onClick={() => handleHeaderClick(col)}
                    className={cn(
                      "px-4 py-3 select-none",
                      col.align === "right" && "text-right",
                      col.align === "center" && "text-center",
                      isSortable && "cursor-pointer hover:bg-[#f1f5f9] transition-colors",
                      col.className
                    )}
                  >
                    <div
                      className={cn(
                        "inline-flex items-center gap-1.5",
                        col.align === "right" && "justify-end",
                        col.align === "center" && "justify-center"
                      )}
                    >
                      <span>{col.header}</span>
                      {getSortIcon(col)}
                    </div>
                  </th>
                );
              })}
            </tr>
          </thead>
          <tbody className="divide-y divide-[#f1f5f9]">
            {isLoading ? (
              skeletonRows.map((_, rIdx) => (
                <tr key={rIdx} className="hover:bg-[#f8fafc]">
                  {columns.map((col, cIdx) => (
                    <td key={cIdx} className="px-4 py-3.5">
                      <Skeleton className="h-4 w-3/4" />
                    </td>
                  ))}
                </tr>
              ))
            ) : data.length === 0 ? (
              <tr>
                <td colSpan={columns.length} className="px-4 py-12 text-center">
                  <div className="flex flex-col items-center justify-center space-y-2">
                    <p className="text-sm font-medium text-[#0f172a]">{emptyTitle}</p>
                    <p className="text-xs text-[#64748b] max-w-sm">{emptyDescription}</p>
                    {emptyAction && <div className="pt-2">{emptyAction}</div>}
                  </div>
                </td>
              </tr>
            ) : (
              data.map((row, rowIdx) => (
                <tr
                  key={row.id ?? rowIdx}
                  className="transition-colors hover:bg-[#f8fafc] focus-within:bg-[#f8fafc]"
                >
                  {columns.map((col, colIdx) => (
                    <td
                      key={colIdx}
                      className={cn(
                        "px-4 py-3.5 text-sm",
                        col.align === "right" && "text-right",
                        col.align === "center" && "text-center",
                        col.className
                      )}
                    >
                      {col.cell
                        ? col.cell(row)
                        : col.accessorKey
                        ? (row[col.accessorKey] as React.ReactNode)
                        : null}
                    </td>
                  ))}
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {pagination && (
        <div className="flex flex-col sm:flex-row items-center justify-between gap-3 px-1 text-xs text-[#64748b]">
          <div>
            Showing{" "}
            <span className="font-medium text-[#0f172a]">
              {pagination.total === 0 ? 0 : (pagination.page - 1) * pagination.limit + 1}
            </span>{" "}
            to{" "}
            <span className="font-medium text-[#0f172a]">
              {Math.min(pagination.page * pagination.limit, pagination.total)}
            </span>{" "}
            of <span className="font-medium text-[#0f172a]">{pagination.total}</span> items
          </div>
          <div className="flex items-center gap-2">
            <span className="text-xs text-[#64748b]">
              Page {pagination.page} of {Math.max(1, pagination.totalPages)}
            </span>
            <div className="flex items-center gap-1">
              <Button
                variant="outline"
                size="sm"
                disabled={pagination.page <= 1 || isLoading}
                onClick={() => pagination.onPageChange(pagination.page - 1)}
                aria-label="Previous page"
              >
                <ChevronLeft className="w-4 h-4" />
              </Button>
              <Button
                variant="outline"
                size="sm"
                disabled={pagination.page >= pagination.totalPages || isLoading}
                onClick={() => pagination.onPageChange(pagination.page + 1)}
                aria-label="Next page"
              >
                <ChevronRight className="w-4 h-4" />
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
