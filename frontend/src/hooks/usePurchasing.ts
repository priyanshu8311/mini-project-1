import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  CreatePurchaseOrderPayload,
  getPurchaseOrders,
  getPurchasingSuggestions,
  createPurchaseOrder,
  receivePurchaseOrder,
  ReceivePurchaseOrderPayload,
} from "@/lib/api-client";

export function usePurchaseOrders(params?: {
  status?: string;
  page?: number;
  limit?: number;
}) {
  return useQuery({
    queryKey: ["purchase-orders", params?.status, params?.page, params?.limit],
    queryFn: () => getPurchaseOrders(params),
  });
}

export function usePurchasingSuggestions() {
  return useQuery({
    queryKey: ["purchasing-suggestions"],
    queryFn: () => getPurchasingSuggestions(),
  });
}

export function useCreatePurchaseOrder() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: CreatePurchaseOrderPayload) => createPurchaseOrder(payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["purchase-orders"] });
      queryClient.invalidateQueries({ queryKey: ["purchasing-suggestions"] });
    },
  });
}

export function useReceivePurchaseOrder() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({
      orderId,
      payload,
    }: {
      orderId: string;
      payload: ReceivePurchaseOrderPayload;
    }) => receivePurchaseOrder(orderId, payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["purchase-orders"] });
      queryClient.invalidateQueries({ queryKey: ["purchasing-suggestions"] });
      queryClient.invalidateQueries({ queryKey: ["inventory-levels"] });
      queryClient.invalidateQueries({ queryKey: ["skus"] });
    },
  });
}
