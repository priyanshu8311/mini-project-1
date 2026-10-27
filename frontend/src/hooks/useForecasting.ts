import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  getDemandForecasts,
  getReorderRecommendations,
  triggerForecastRun,
} from "@/lib/api-client";

export function useDemandForecasts(params?: {
  sku_id?: string;
  start_date?: string;
  end_date?: string;
  page?: number;
  limit?: number;
}) {
  return useQuery({
    queryKey: [
      "demand-forecasts",
      params?.sku_id,
      params?.start_date,
      params?.end_date,
      params?.page,
      params?.limit,
    ],
    queryFn: () => getDemandForecasts(params),
  });
}

export function useReorderRecommendations() {
  return useQuery({
    queryKey: ["reorder-recommendations"],
    queryFn: () => getReorderRecommendations(),
  });
}

export function useTriggerForecastRun() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (horizonDays: number = 30) => triggerForecastRun(horizonDays),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["demand-forecasts"] });
      queryClient.invalidateQueries({ queryKey: ["reorder-recommendations"] });
      queryClient.invalidateQueries({ queryKey: ["purchasing-suggestions"] });
    },
  });
}
