# Smart Inventory Management & Demand Forecasting: API Specification

## 1. Overview and Conventions

This document defines the application programming interface (API) for the Smart Inventory Management system. The API follows RESTful principles, utilizing standard HTTP methods and JSON payloads. It serves as the single source of truth for the frontend application (React/Next.js) and third-party integrations.

*   **Base URL:** `https://api.yourdomain.com/api/v1`
*   **Content-Type:** `application/json` for all request and response bodies.
*   **Versioning:** URI-based versioning (`/api/v1/`).

## 2. Authentication and Authorization

*   **Authentication:** Stateless JSON Web Tokens (JWT). Clients must include the token in the `Authorization` header: `Authorization: Bearer <token>`.
*   **Authorization:** Role-Based Access Control (RBAC) is enforced server-side. The JWT payload includes the user's `tenant_id` and `role`. Middleware intercepts every request, validates the JWT signature, and checks role permissions against the requested endpoint before processing.
*   **Tenant Isolation:** The `tenant_id` extracted from the JWT is automatically injected into all database queries to guarantee data privacy.

## 3. Request and Response Formats

### Pagination and Filtering
For endpoints returning lists (e.g., inventory levels, transactions), cursor-based or offset/limit pagination is required to handle large catalogs.
*   **Query Parameters:** `?page=1&limit=50&sort_by=created_at&sort_order=desc`
*   **Filtering:** Additional query parameters apply filters: `?location_id=<uuid>&stock_status=low`.
*   **Response Wrapper:**
    ```json
    {
      "data": [ ... ],
      "meta": {
        "total": 1250,
        "page": 1,
        "limit": 50,
        "total_pages": 25
      }
    }
    ```

### Validation and Error Conventions
Input validation occurs immediately upon receiving a request. If validation fails, or an error occurs, the API returns a standardized JSON structure:
*   **Error Response Format:**
    ```json
    {
      "error": {
        "code": "VALIDATION_ERROR",
        "message": "Invalid quantity provided.",
        "details": [
          { "field": "quantity_change", "issue": "Must be greater than 0" }
        ]
      }
    }
    ```
*   **Standard HTTP Codes:**
    *   `200 OK` / `201 Created`: Success.
    *   `400 Bad Request`: Malformed payload or business logic violation (e.g., insufficient stock).
    *   `401 Unauthorized`: Missing or invalid JWT.
    *   `403 Forbidden`: Insufficient role permissions.
    *   `404 Not Found`: Resource does not exist.
    *   `422 Unprocessable Entity`: Schema validation failure.
    *   `500 Internal Server Error`: Unhandled backend exception.

## 4. Core API Endpoints

### Auth & Users
*   `POST /auth/login`: Authenticates user credentials and returns a JWT.
*   `GET /users/me`: Retrieves current user profile and permissions.

### Product & SKU Management
*   `GET /products/skus`: Lists all SKUs with optional filtering.
*   `POST /products/skus`: Creates a new SKU.
*   `PUT /products/skus/{id}`: Updates SKU details (e.g., reorder point, supplier).

### Inventory Operations
*   `GET /inventory/levels`: Retrieves current on-hand, reserved, and available stock per SKU per location.
*   `POST /inventory/transactions`: Records atomic stock operations (Receive, Ship, Adjust, Transfer). Requires `transaction_type`, `sku_id`, `location_id` (and `target_location_id` for transfers), `quantity_change`, and `reason`.

### Demand Forecasting
*   `GET /forecasts`: Retrieves generated ML demand predictions by SKU and date range.
*   `POST /forecasts/jobs`: Triggers an asynchronous batch forecast generation (Admin/Analyst only).

### Replenishment
*   `GET /purchasing/suggestions`: Retrieves automated PO recommendations based on forecasts and safety stock.
*   `POST /purchasing/orders`: Converts a suggestion into a formal Purchase Order.

## 5. External APIs and Integrations

The system performs two-way synchronization with sales channels (Shopify, POS) and ERPs.

*   **Outgoing Synchronization:** Worker processes (Celery) poll or react to internal events (e.g., stock update). They construct external API payloads and dispatch them using encrypted credentials stored in the `integration_configs` database table. Secrets are decrypted in memory only at the time of execution.
*   **Connector Modules:** Dedicated internal modules map our system's `inventory_levels` schema to the specific API schemas of Shopify, Square, etc.

## 6. Webhooks and Verification

To maintain real-time sync with sales channels, the API exposes webhook receiver endpoints.

*   **Endpoint:** `POST /webhooks/{provider}` (e.g., `/webhooks/shopify/orders/create`)
*   **Verification:** Webhook authenticity is strictly validated using HMAC-SHA256 signatures provided in the request headers (e.g., `X-Shopify-Hmac-Sha256`). Requests failing signature verification are rejected with a `401 Unauthorized` before processing.
*   **Processing:** Valid webhooks are immediately acknowledged (`200 OK`) and placed onto a Redis message queue for asynchronous processing to ensure channel sync latency remains under the 30-second target.

## 7. Rate Limiting

To prevent abuse and ensure high availability:
*   **Authenticated API Clients:** Limited to 300 requests per minute per `tenant_id`.
*   **Unauthenticated Endpoints (Login):** Strictly limited to 5 requests per minute per IP to mitigate brute-force attacks.
*   **Webhook Receivers:** Limited based on provider documentation and load-balancer capacity.
*   **Response:** Exceeding limits returns `429 Too Many Requests` with a `Retry-After` header.

## 8. Failure Handling and Resilience

*   **External API Failures:** Outbound requests to external integrations utilize an exponential backoff and retry strategy via the background task queue. 
*   **Dead Letter Queue (DLQ):** Tasks that fail consistently (e.g., invalid Shopify API key) are moved to a DLQ and trigger an in-app alert for the system Admin.
*   **Database Transactions:** Internal inventory operations are strictly wrapped in database transactions. If an operation fails (e.g., deadlocks or validation failure), the transaction is rolled back entirely, ensuring no partial stock updates occur.

## 9. Required Environment Variables

The application relies on the following environment variables (never hardcoded):

*   `DATABASE_URL`: Connection string for PostgreSQL.
*   `REDIS_URL`: Connection string for the task queue and caching layer.
*   `JWT_SECRET_KEY`: High-entropy string for signing Auth tokens.
*   `ENCRYPTION_KEY`: Symmetric key used to encrypt/decrypt external provider API keys stored in the database.
*   `SHOPIFY_WEBHOOK_SECRET` / `SQUARE_WEBHOOK_SECRET`: Global secrets used to verify incoming webhook payloads.
*   `ALLOWED_ORIGINS`: CORS configuration for the frontend web application.