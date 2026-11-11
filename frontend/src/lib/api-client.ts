export interface ApiErrorDetail {
  field?: string;
  issue: string;
}

export interface ApiErrorResponse {
  error: {
    code: string;
    message: string;
    details?: ApiErrorDetail[];
  };
}

export class ApiError extends Error {
  public code: string;
  public status: number;
  public details?: ApiErrorDetail[];

  constructor(status: number, errorData: ApiErrorResponse["error"]) {
    super(errorData.message);
    this.name = "ApiError";
    this.status = status;
    this.code = errorData.code;
    this.details = errorData.details;
  }
}

export interface UserResponse {
  id: string;
  tenant_id: string;
  email: string;
  role: string;
  is_active: boolean;
  created_at: string;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
  user: UserResponse;
}

export interface RegisterPayload {
  organization_name: string;
  email: string;
  password: string;
}

export interface UserListResponse {
  data: UserResponse[];
  total: number;
}

export interface UserCreatePayload {
  email: string;
  password: string;
  role: string;
}

export interface UserStatusUpdatePayload {
  is_active: boolean;
}

export interface LogoutResponse {
  message: string;
}

export interface ShopifyConfigResponse {
  id: string;
  tenant_id: string;
  provider: string;
  shop_domain: string;
  shopify_location_id: string | null;
  default_location_id: string | null;
  auto_sync_stock: boolean;
  has_webhook_secret: boolean;
  is_active: boolean;
  masked_access_token: string;
  last_sync_at: string | null;
  created_at: string;
}

export interface ShopifyConfigPayload {
  shop_domain: string;
  access_token: string;
  shopify_location_id?: string | null;
  default_location_id?: string | null;
  auto_sync_stock?: boolean;
  webhook_secret?: string | null;
}

export interface ShopifyTestConnectionResponse {
  success: boolean;
  shop_name?: string | null;
  shop_domain?: string | null;
  currency?: string | null;
  message: string;
}

export interface ShopifySyncResponse {
  success: boolean;
  sku_code: string;
  on_hand: number;
  available: number;
  shopify_inventory_item_id: number;
  synced_at: string;
  message: string;
}


const BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";
const TOKEN_STORAGE_KEY = "smart_inventory_auth_token";

export function getAuthToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem(TOKEN_STORAGE_KEY);
}

export function setAuthToken(token: string): void {
  if (typeof window !== "undefined") {
    localStorage.setItem(TOKEN_STORAGE_KEY, token);
  }
}

export function clearAuthToken(): void {
  if (typeof window !== "undefined") {
    localStorage.removeItem(TOKEN_STORAGE_KEY);
  }
}

export async function apiClient<T>(
  endpoint: string,
  options: RequestInit = {}
): Promise<T> {
  const url = `${BASE_URL}${endpoint.startsWith("/") ? endpoint : `/${endpoint}`}`;

  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(options.headers as Record<string, string>),
  };

  const token = getAuthToken();
  if (token && !headers["Authorization"]) {
    headers["Authorization"] = `Bearer ${token}`;
  }

  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), 10000);

  let response: Response;
  try {
    response = await fetch(url, {
      signal: options.signal || controller.signal,
      ...options,
      headers,
    });
  } catch (err: unknown) {
    if (err instanceof Error && err.name === "AbortError") {
      throw new ApiError(408, {
        code: "TIMEOUT",
        message: "Network request timed out. Please verify the backend service is running.",
      });
    }
    throw err;
  } finally {
    clearTimeout(timeoutId);
  }

  if (!response.ok) {
    let errorData: ApiErrorResponse["error"];
    try {
      const json = await response.json();
      errorData = json.error || {
        code: "HTTP_ERROR",
        message: response.statusText || "Request failed",
      };
    } catch {
      errorData = {
        code: "HTTP_ERROR",
        message: `HTTP request failed with status ${response.status}`,
      };
    }

    if (response.status === 401 && typeof window !== "undefined") {
      clearAuthToken();
    }

    throw new ApiError(response.status, errorData);
  }

  return response.json() as Promise<T>;
}

export async function getShopifyConfig(): Promise<ShopifyConfigResponse> {
  return apiClient<ShopifyConfigResponse>("/integrations/shopify/config");
}

export async function saveShopifyConfig(payload: ShopifyConfigPayload): Promise<ShopifyConfigResponse> {
  return apiClient<ShopifyConfigResponse>("/integrations/shopify/config", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function testShopifyConnection(): Promise<ShopifyTestConnectionResponse> {
  return apiClient<ShopifyTestConnectionResponse>("/integrations/shopify/test", {
    method: "POST",
  });
}

// --- Purchasing Types & APIs ---
export interface POItem {
  id: string;
  po_id: string;
  sku_id: string;
  quantity_ordered: number;
  quantity_received: number;
  unit_cost: string | number;
  created_at: string;
  sku_code?: string | null;
  product_name?: string | null;
}

export interface PurchaseOrder {
  id: string;
  tenant_id: string;
  supplier_id: string | null;
  status: "Draft" | "Sent" | "Partially Received" | "Completed" | string;
  expected_date: string | null;
  created_at: string;
  items: POItem[];
}

export interface PaginatedPurchaseOrdersResponse {
  data: PurchaseOrder[];
  meta: {
    total: number;
    page: number;
    limit: number;
    total_pages: number;
  };
}

export interface CreatePurchaseOrderItemPayload {
  sku_id: string;
  quantity_ordered: number;
  unit_cost: number;
}

export interface CreatePurchaseOrderPayload {
  supplier_id?: string | null;
  expected_date?: string | null;
  items: CreatePurchaseOrderItemPayload[];
}

export interface ReceivePOItemPayload {
  po_item_id: string;
  quantity_to_receive: number;
}

export interface ReceivePurchaseOrderPayload {
  location_id: string;
  items: ReceivePOItemPayload[];
}

export interface PurchasingSuggestion {
  sku_id: string;
  sku_code: string;
  product_name?: string | null;
  location_id?: string | null;
  location_name?: string | null;
  current_on_hand: number;
  reorder_point: number;
  lead_time_days: number;
  suggested_reorder_quantity: number;
  unit_cost: string | number;
  supplier_id?: string | null;
  urgency: "High" | "Medium" | "Low";
}

export async function getPurchaseOrders(params?: {
  status?: string;
  page?: number;
  limit?: number;
}): Promise<PaginatedPurchaseOrdersResponse> {
  const query = new URLSearchParams();
  if (params?.status) query.append("status", params.status);
  if (params?.page) query.append("page", String(params.page));
  if (params?.limit) query.append("limit", String(params.limit));
  const qs = query.toString();
  return apiClient<PaginatedPurchaseOrdersResponse>(`/purchasing/orders${qs ? `?${qs}` : ""}`);
}

export async function createPurchaseOrder(
  payload: CreatePurchaseOrderPayload
): Promise<PurchaseOrder> {
  return apiClient<PurchaseOrder>("/purchasing/orders", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function receivePurchaseOrder(
  orderId: string,
  payload: ReceivePurchaseOrderPayload
): Promise<PurchaseOrder> {
  return apiClient<PurchaseOrder>(`/purchasing/orders/${orderId}/receive`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function getPurchasingSuggestions(): Promise<PurchasingSuggestion[]> {
  return apiClient<PurchasingSuggestion[]>("/purchasing/suggestions");
}

// --- Forecasting Types & APIs ---
export interface DemandForecastItem {
  id: string;
  tenant_id: string;
  sku_id: string;
  forecast_date: string;
  predicted_demand: number;
  confidence_lower: number;
  confidence_upper: number;
  generated_at: string;
  sku_code?: string | null;
  product_name?: string | null;
}

export interface PaginatedDemandForecastsResponse {
  data: DemandForecastItem[];
  meta: {
    total: number;
    page: number;
    limit: number;
    total_pages: number;
  };
}

export interface ForecastJobResponse {
  job_id: string;
  status: string;
  total_skus_processed: number;
  generated_forecasts_count: number;
  message: string;
  mape?: number | null;
}

export interface ReorderRecommendationItem {
  sku_id: string;
  sku_code: string;
  product_name?: string | null;
  current_stock: number;
  predicted_daily_demand: number;
  lead_time_days: number;
  suggested_reorder_point: number;
  suggested_order_qty: number;
  days_of_supply: number;
  urgency: string;
}

export async function getDemandForecasts(params?: {
  sku_id?: string;
  start_date?: string;
  end_date?: string;
  page?: number;
  limit?: number;
}): Promise<PaginatedDemandForecastsResponse> {
  const query = new URLSearchParams();
  if (params?.sku_id) query.append("sku_id", params.sku_id);
  if (params?.start_date) query.append("start_date", params.start_date);
  if (params?.end_date) query.append("end_date", params.end_date);
  if (params?.page) query.append("page", String(params.page));
  if (params?.limit) query.append("limit", String(params.limit));
  const qs = query.toString();
  return apiClient<PaginatedDemandForecastsResponse>(`/forecasts${qs ? `?${qs}` : ""}`);
}

export async function triggerForecastRun(horizonDays: number = 30): Promise<ForecastJobResponse> {
  return apiClient<ForecastJobResponse>("/forecasts/jobs", {
    method: "POST",
    body: JSON.stringify({ horizon_days: horizonDays }),
  });
}

export async function getReorderRecommendations(): Promise<ReorderRecommendationItem[]> {
  return apiClient<ReorderRecommendationItem[]>("/forecasts/recommendations");
}

