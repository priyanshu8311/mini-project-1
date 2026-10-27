"use client";

import React, { useState } from "react";
import {
  Play,
  TrendingUp,
  AlertTriangle,
  Layers,
  Sparkles,
  Calendar,
  CheckCircle2,
  RefreshCw,
  Plus,
} from "lucide-react";
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Skeleton } from "@/components/ui/Skeleton";
import {
  useDemandForecasts,
  useReorderRecommendations,
  useTriggerForecastRun,
} from "@/hooks/useForecasting";
import { CreatePoModal } from "@/components/inventory/CreatePoModal";
import { ReorderRecommendationItem } from "@/lib/api-client";

export default function ForecastingPage() {
  const [activeTab, setActiveTab] = useState<"recommendations" | "predictions">("recommendations");
  const [selectedSkuFilter, setSelectedSkuFilter] = useState<string>("");
  const [horizonDays, setHorizonDays] = useState<number>(30);
  const [poModalSku, setPoModalSku] = useState<{
    id: string;
    code: string;
    qty: number;
  } | null>(null);

  // Queries
  const {
    data: forecastsData,
    isLoading: isForecastsLoading,
    refetch: refetchForecasts,
  } = useDemandForecasts({
    sku_id: selectedSkuFilter || undefined,
    limit: 50,
  });

  const {
    data: recsData,
    isLoading: isRecsLoading,
    refetch: refetchRecs,
  } = useReorderRecommendations();

  // Trigger Forecast Mutation
  const triggerMutation = useTriggerForecastRun();

  const handleTriggerRun = () => {
    triggerMutation.mutate(horizonDays, {
      onSuccess: () => {
        refetchForecasts();
        refetchRecs();
      },
    });
  };

  const forecasts = forecastsData?.data || [];
  const recommendations = recsData || [];

  // Summary Metrics
  const totalPredictions = forecastsData?.meta?.total || forecasts.length;
  const criticalItems = recommendations.filter((r) => r.urgency === "Critical" || r.urgency === "High").length;
  const avgDailyVelocity =
    recommendations.length > 0
      ? (
          recommendations.reduce((acc, r) => acc + r.predicted_daily_demand, 0) /
          recommendations.length
        ).toFixed(1)
      : "0.0";

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-[#0f172a]">
            Demand Forecasting & Replenishment
          </h1>
          <p className="text-sm text-[#64748b] mt-1">
            Machine learning time-series intelligence predicting SKU velocity and dynamic reorder points.
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-3">
          <div className="flex items-center gap-2">
            <label htmlFor="horizon-select" className="text-xs font-medium text-[#64748b]">
              Horizon:
            </label>
            <select
              id="horizon-select"
              value={horizonDays}
              onChange={(e) => setHorizonDays(Number(e.target.value))}
              className="text-xs rounded-md border border-[#cbd5e1] bg-white px-2.5 py-1.5 text-[#0f172a] focus:border-[#2563eb] focus:outline-none"
            >
              <option value={7}>7 Days</option>
              <option value={14}>14 Days</option>
              <option value={30}>30 Days</option>
              <option value={60}>60 Days</option>
              <option value={90}>90 Days</option>
            </select>
          </div>
          <Button
            variant="outline"
            size="sm"
            onClick={() => {
              refetchForecasts();
              refetchRecs();
            }}
          >
            <RefreshCw className="w-4 h-4 mr-1.5" />
            Refresh
          </Button>
          <Button
            variant="primary"
            size="sm"
            onClick={handleTriggerRun}
            isLoading={triggerMutation.isPending}
          >
            <Play className="w-4 h-4 mr-1.5 fill-current" />
            {triggerMutation.isPending ? "Computing Models..." : `Trigger Run (${horizonDays}d)`}
          </Button>
        </div>
      </div>

      {/* Success / Status Banner */}
      {triggerMutation.isSuccess && (
        <div className="flex items-center gap-2.5 rounded-lg border border-[#bbf7d0] bg-[#f0fdf4] p-3.5 text-sm text-[#15803d]">
          <CheckCircle2 className="w-5 h-5 shrink-0" />
          <span>{triggerMutation.data?.message || "Forecast models updated successfully."}</span>
        </div>
      )}

      {/* Metrics Row */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold uppercase tracking-wider text-[#64748b]">
                Active Predictions
              </span>
              <div className="p-2 rounded-lg bg-[#eff6ff] text-[#2563eb]">
                <Layers className="w-4 h-4" />
              </div>
            </div>
            <p className="text-2xl font-bold text-[#0f172a] mt-2">{totalPredictions}</p>
            <span className="text-xs text-[#64748b]">Next {horizonDays} days forward projection</span>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold uppercase tracking-wider text-[#64748b]">
                Avg Daily Velocity
              </span>
              <div className="p-2 rounded-lg bg-[#f0fdf4] text-[#16a34a]">
                <TrendingUp className="w-4 h-4" />
              </div>
            </div>
            <p className="text-2xl font-bold text-[#0f172a] mt-2">{avgDailyVelocity} units/day</p>
            <span className="text-xs text-[#64748b]">Catalog-wide demand rate</span>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold uppercase tracking-wider text-[#64748b]">
                Urgent Replenishments
              </span>
              <div className="p-2 rounded-lg bg-[#fef2f2] text-[#dc2626]">
                <AlertTriangle className="w-4 h-4" />
              </div>
            </div>
            <p className="text-2xl font-bold text-[#0f172a] mt-2">{criticalItems}</p>
            <span className="text-xs text-[#dc2626]">Stock-out risk within lead time</span>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold uppercase tracking-wider text-[#64748b]">
                Model Pipeline
              </span>
              <div className="p-2 rounded-lg bg-[#faf5ff] text-[#9333ea]">
                <Sparkles className="w-4 h-4" />
              </div>
            </div>
            <p className="text-2xl font-bold text-[#0f172a] mt-2">Active</p>
            <span className="text-xs text-[#64748b]">Moving Avg & Exp. Smoothing</span>
          </CardContent>
        </Card>
      </div>

      {/* Navigation Tabs */}
      <div className="flex border-b border-[#e2e8f0] gap-8">
        <button
          onClick={() => setActiveTab("recommendations")}
          className={`pb-3 text-sm font-semibold transition-colors border-b-2 -mb-px ${
            activeTab === "recommendations"
              ? "border-[#2563eb] text-[#2563eb]"
              : "border-transparent text-[#64748b] hover:text-[#0f172a]"
          }`}
        >
          Replenishment Recommendations ({recommendations.length})
        </button>
        <button
          onClick={() => setActiveTab("predictions")}
          className={`pb-3 text-sm font-semibold transition-colors border-b-2 -mb-px ${
            activeTab === "predictions"
              ? "border-[#2563eb] text-[#2563eb]"
              : "border-transparent text-[#64748b] hover:text-[#0f172a]"
          }`}
        >
          Raw Time-Series Predictions ({forecasts.length})
        </button>
      </div>

      {/* Tab 1: Replenishment Recommendations */}
      {activeTab === "recommendations" && (
        <Card>
          <CardHeader>
            <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
              <div>
                <CardTitle>Suggested Purchase Orders</CardTitle>
                <CardDescription>
                  Synthesized from daily sales velocity, safety stock targets, and vendor lead times.
                </CardDescription>
              </div>
            </div>
          </CardHeader>
          <CardContent>
            {isRecsLoading ? (
              <div className="space-y-3">
                <Skeleton className="h-12 w-full" />
                <Skeleton className="h-12 w-full" />
                <Skeleton className="h-12 w-full" />
              </div>
            ) : recommendations.length === 0 ? (
              <div className="py-12 text-center text-sm text-[#64748b] border border-dashed border-[#cbd5e1] rounded-lg">
                <p className="font-medium text-[#0f172a]">No reorder recommendations</p>
                <p className="text-xs text-[#94a3b8] mt-1">
                  Trigger a forecast run or record sales to generate automated purchase recommendations.
                </p>
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-left text-sm border-collapse">
                  <thead>
                    <tr className="border-b border-[#e2e8f0] text-xs font-semibold uppercase tracking-wider text-[#64748b]">
                      <th className="py-3 px-4">SKU / Item</th>
                      <th className="py-3 px-4">Current Stock</th>
                      <th className="py-3 px-4">Daily Demand</th>
                      <th className="py-3 px-4">Lead Time</th>
                      <th className="py-3 px-4">Days of Supply</th>
                      <th className="py-3 px-4">Suggested Order</th>
                      <th className="py-3 px-4">Urgency</th>
                      <th className="py-3 px-4 text-right">Action</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-[#f1f5f9]">
                    {recommendations.map((item: ReorderRecommendationItem) => {
                      const urgencyVariant: "error" | "warning" | "info" | "neutral" =
                        item.urgency === "Critical"
                          ? "error"
                          : item.urgency === "High"
                          ? "warning"
                          : item.urgency === "Medium"
                          ? "info"
                          : "neutral";

                      return (
                        <tr key={item.sku_id} className="hover:bg-[#f8fafc] transition-colors">
                          <td className="py-3.5 px-4 font-medium text-[#0f172a]">
                            <div>{item.sku_code}</div>
                            {item.product_name && (
                              <div className="text-xs text-[#64748b]">{item.product_name}</div>
                            )}
                          </td>
                          <td className="py-3.5 px-4 font-semibold text-[#0f172a]">
                            {item.current_stock} units
                          </td>
                          <td className="py-3.5 px-4 text-[#475569]">
                            {item.predicted_daily_demand} / day
                          </td>
                          <td className="py-3.5 px-4 text-[#475569]">{item.lead_time_days} days</td>
                          <td className="py-3.5 px-4 text-[#475569]">
                            {item.days_of_supply > 365 ? "> 1 year" : `${item.days_of_supply} days`}
                          </td>
                          <td className="py-3.5 px-4 font-semibold text-[#2563eb]">
                            +{item.suggested_order_qty} units
                          </td>
                          <td className="py-3.5 px-4">
                            <Badge variant={urgencyVariant}>{item.urgency}</Badge>
                          </td>
                          <td className="py-3.5 px-4 text-right">
                            <Button
                              variant="outline"
                              size="sm"
                              onClick={() =>
                                setPoModalSku({
                                  id: item.sku_id,
                                  code: item.sku_code,
                                  qty: item.suggested_order_qty,
                                })
                              }
                            >
                              <Plus className="w-3.5 h-3.5 mr-1" />
                              Order
                            </Button>
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            )}
          </CardContent>
        </Card>
      )}

      {/* Tab 2: Raw Predictions */}
      {activeTab === "predictions" && (
        <Card>
          <CardHeader>
            <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
              <div>
                <CardTitle>Daily Demand Forecasts</CardTitle>
                <CardDescription>
                  Time-series model predictions with 80% confidence lower and upper bounds.
                </CardDescription>
              </div>
              <div className="flex flex-wrap items-center gap-3">
                <input
                  type="text"
                  placeholder="Filter by SKU ID or code..."
                  value={selectedSkuFilter}
                  onChange={(e) => setSelectedSkuFilter(e.target.value)}
                  className="text-xs rounded-md border border-[#cbd5e1] bg-white px-3 py-1.5 text-[#0f172a] placeholder-[#94a3b8] focus:border-[#2563eb] focus:outline-none w-52"
                />
                <div className="flex items-center gap-1.5 text-xs text-[#64748b]">
                  <Calendar className="w-4 h-4" />
                  <span>Horizon: {horizonDays} days</span>
                </div>
              </div>
            </div>
          </CardHeader>
          <CardContent>
            {isForecastsLoading ? (
              <div className="space-y-3">
                <Skeleton className="h-12 w-full" />
                <Skeleton className="h-12 w-full" />
                <Skeleton className="h-12 w-full" />
              </div>
            ) : forecasts.length === 0 ? (
              <div className="py-12 text-center text-sm text-[#64748b] border border-dashed border-[#cbd5e1] rounded-lg">
                <p className="font-medium text-[#0f172a]">No forecast jobs generated yet</p>
                <p className="text-xs text-[#94a3b8] mt-1">
                  Click &ldquo;Trigger Forecast Run&rdquo; above to compute daily demand predictions.
                </p>
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-left text-sm border-collapse">
                  <thead>
                    <tr className="border-b border-[#e2e8f0] text-xs font-semibold uppercase tracking-wider text-[#64748b]">
                      <th className="py-3 px-4">Forecast Date</th>
                      <th className="py-3 px-4">SKU Code</th>
                      <th className="py-3 px-4">Predicted Demand</th>
                      <th className="py-3 px-4">Confidence Range</th>
                      <th className="py-3 px-4">Generated At</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-[#f1f5f9]">
                    {forecasts.map((fc) => (
                      <tr key={fc.id} className="hover:bg-[#f8fafc] transition-colors">
                        <td className="py-3 px-4 font-medium text-[#0f172a]">
                          {fc.forecast_date}
                        </td>
                        <td className="py-3 px-4 text-[#475569]">
                          <span className="font-mono text-xs">{fc.sku_code || fc.sku_id.slice(0, 8)}</span>
                          {fc.product_name && (
                            <div className="text-xs text-[#64748b]">{fc.product_name}</div>
                          )}
                        </td>
                        <td className="py-3 px-4 font-semibold text-[#2563eb]">
                          {fc.predicted_demand} units
                        </td>
                        <td className="py-3 px-4 text-xs text-[#64748b]">
                          [{fc.confidence_lower} – {fc.confidence_upper} units]
                        </td>
                        <td className="py-3 px-4 text-xs text-[#94a3b8]">
                          {new Date(fc.generated_at).toLocaleString()}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </CardContent>
        </Card>
      )}

      {/* Create PO Modal from Recommendation */}
      {poModalSku && (
        <CreatePoModal
          isOpen={true}
          onClose={() => setPoModalSku(null)}
          onSuccess={() => {
            setPoModalSku(null);
            refetchRecs();
          }}
          initialSkuId={poModalSku.id}
          initialSkuCode={poModalSku.code}
          initialQuantity={poModalSku.qty}
        />
      )}
    </div>
  );
}
