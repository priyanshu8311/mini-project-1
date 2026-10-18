# Smart Inventory Management & Demand Forecasting: System Architecture

## Recommended Tech Stack and Reasoning

To adhere to the principle of the simplest reliable architecture while meeting the high-concurrency, ML-forecasting, and scalable SaaS requirements from the PRD, we will utilize a **Modular Monolith** built on Python. 

*   **Backend Framework:** **Python (FastAPI)**. FastAPI provides high-performance, async, RESTful API capabilities while keeping the ecosystem natively aligned with the ML forecasting tools (XGBoost, Prophet) required by the MVP. This eliminates the need for a separate ML microservice.
*   **Database:** **PostgreSQL**. A robust, ACID-compliant relational database is non-negotiable for atomic inventory transactions, concurrent locking, and strict data consistency.
*   **Frontend:** **React (Next.js) with Tailwind CSS**. Next.js provides optimized loading for web applications, while Tailwind CSS maps perfectly to the 8-point grid, semantic color tokens, and utility-driven UI components defined in the visual design principles.
*   **Background Processing / Queue:** **Redis & Celery**. Essential for decoupling long-running jobs (ML forecast generation, batch CSV imports) and handling the polling/webhooks for multi-channel syncs (Shopify, Square) without blocking the main API thread.

## Frontend and Backend Architecture

**Frontend (Client-Side Application):**
*   **Pattern:** Single Page Application (SPA) with Server-Side Rendering (SSR) for initial load performance.
*   **State Management:** React Query for server-state caching and synchronization (ideal for real-time dashboards and inventory lists), and lightweight Context API for global UI state (auth, theme).
*   **UI System:** Component-driven architecture mapping directly to the DESIGN.md specifications (Cards, Data Tables with inline editing, Modals, Toasts).

**Backend (API & Processing):**
*   **Pattern:** Domain-Driven Modular Monolith. The codebase is unified but logically separated by domains (Inventory, Integrations, Forecasting, Auth) to allow easy extraction into microservices if future scalability demands it.
*   **Concurrency Model:** Asynchronous I/O via FastAPI combined with SQLAlchemy async sessions to handle the 10,000+ daily transactions target with low latency.

## Data Flow

1.  **Web Request (e.g., Stock Transfer):** Client issues a REST request. FastAPI validates the payload and checks RBAC permissions.
2.  **Transaction Execution:** Database transaction begins. The system applies row-level locking (`SELECT ... FOR UPDATE`) to the relevant SKU/Location rows, calculates the new balances, writes to the `inventory_transactions` ledger, and updates the `inventory_levels` table atomically.
3.  **Background Sync:** Upon successful commit, an event is emitted to the Celery task queue to sync the updated stock level to connected integrations (e.g., Shopify, Square).
4.  **Forecasting Pipeline:** A scheduled Celery cron job fetches the last week's sales data from PostgreSQL, passes it through the Python-based XGBoost/Prophet model, and writes the output back to the `demand_forecasts` table for UI consumption.

## Folder Structure

```text
/backend
  /src
    /api          # FastAPI routers, endpoints, and dependency injection (Auth)
    /core         # Configuration, logging, security, error handlers
    /domain       # Domain modules (inventory, users, forecasting, integrations)
      /inventory
        models.py # SQLAlchemy ORM models
        schemas.py# Pydantic validation schemas
        service.py# Business logic
    /tasks        # Celery background workers (sync, ml_pipeline, imports)
    /ml           # Prophet/XGBoost training and inference scripts
/frontend
  /src
    /app          # Next.js App Router (Pages: Dashboard, Inventory, Settings)
    /components   # Reusable UI (Buttons, Tables, Modals) matching DESIGN.md
    /hooks        # React Query hooks and custom business logic
    /lib          # API clients, utility functions, styling tokens
```

## Database Interaction

*   **ORM:** SQLAlchemy 2.0 (Async mode) with Alembic for schema migrations.
*   **Concurrency Handling:** Optimistic locking (version numbers on rows) is used for standard updates. Pessimistic locking is strictly applied during inventory balance adjustments to guarantee atomic decrement/increment operations across locations.
*   **Query Optimization:** Read-heavy dashboard queries utilize indexed views, while write-heavy operations interact strictly with the append-only transaction ledger.

## Authentication and Authorization

*   **Authentication:** JSON Web Tokens (JWT) for stateless session management.
*   **Authorization (RBAC):** Middleware injects the user context into every request. Endpoints are decorated with role-based dependencies (e.g., `require_roles(['Admin', 'Inventory Manager'])`). 
*   **Security:** Passwords hashed via bcrypt. Multi-Factor Authentication (MFA) supported via TOTP (Time-based One-Time Password) for Admin roles.

## API Architecture

*   **Style:** REST API over HTTPS. 
*   **Payloads:** JSON structured. Validated strictly by Pydantic models.
*   **Versioning:** URI versioning (e.g., `/api/v1/inventory`).
*   **Pagination & Filtering:** Standardized offset/limit or cursor-based pagination for inventory lists. Robust query string filtering (location, SKU, status) to support advanced search functionality.

## External Services & Integrations

*   **E-commerce & POS APIs:** Two-way synchronization via dedicated connector modules (Shopify API, Square API). 
*   **Webhooks:** An exposed `/api/v1/webhooks/{provider}` endpoint securely receives incoming events (e.g., new order placed on Shopify) and queues them in Redis for immediate processing.
*   **Resiliency:** Integrations use exponential backoff and retry mechanisms for network failures to ensure the "single live view" remains accurate.

## AI Architecture

*   **Model:** Standard Prophet or XGBoost time-series model (MVP configuration).
*   **Data Pipeline:** Pulls from `sales_history` and `inventory_transactions`. 
*   **Execution:** Runs offline in batch windows (e.g., overnight) to prevent locking main database resources.
*   **Output:** Generates predicted daily/weekly demand per SKU per location, mapping results into the `demand_forecasts` table along with confidence intervals to drive the "Reorder Points" logic.

## Environment Configuration

*   **Methodology:** 12-Factor App methodology. All configuration is injected via environment variables (`.env`).
*   **Separation:** Distinct environments for Development, Staging, and Production. 
*   **Secrets:** API keys for external services, database credentials, and JWT salts are stored in a secure secret manager (e.g., AWS Secrets Manager or HashiCorp Vault) and loaded at runtime.

## Error Handling

*   **Backend:** Global exception handlers map domain exceptions to standard HTTP status codes (400 Bad Request, 401 Unauthorized, 403 Forbidden, 404 Not Found, 409 Conflict). Responses include clear, standardized error codes.
*   **Frontend:** React Error Boundaries capture UI crashes. API failures trigger error toasts or modal feedback per the DESIGN.md specifications. Form inputs utilize inline validation hints.
*   **Logging:** All application errors are routed to structured logs (JSON format) and centralized (e.g., Datadog, ELK stack, or Sentry) to monitor integration health and system stability.

## Security Boundaries

*   **Network:** The database and Redis cache are placed in private subnets, completely isolated from the public internet. Only the FastAPI application servers reside in the public/load-balanced subnet.
*   **Data Validation:** Strict input validation and sanitization via Pydantic to prevent SQL injection and XSS.
*   **Tenant Isolation:** As a SaaS product, all database queries explicitly filter by `tenant_id` via middleware to prevent cross-tenant data leakage.

## Testing and Deployment Approach

*   **Testing:**
    *   *Unit Tests:* Pytest for backend business logic (specifically inventory locking and math) and Jest for frontend UI components.
    *   *Integration Tests:* End-to-end tests for core workflows (Order to Stock-out) against a spun-up PostgreSQL test container.
    *   *ML Testing:* Validation of MAPE (Mean Absolute Percentage Error) thresholds against a holdout validation set.
*   **Deployment:** Docker containerization. CI/CD pipeline (GitHub Actions) runs tests, builds images, and pushes to a container registry. Managed deployment via AWS ECS (Fargate) or standard Kubernetes to ensure scalability, coupled with a Managed PostgreSQL instance (AWS RDS) for high availability and automated backups.