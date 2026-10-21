# Smart Inventory Management & Demand Forecasting System

A production-grade, multi-tenant inventory management and AI-driven demand forecasting platform. Built with an append-only transaction ledger, optimistic and pessimistic concurrency control, real-time multi-location tracking, automated replenishment calculations, and machine learning time-series forecasting.

---

## Table of Contents

1. [Executive Summary & Business Value](#1-executive-summary--business-value)
2. [System Architecture](#2-system-architecture)
3. [Technology Stack](#3-technology-stack)
4. [Project Directory Structure](#4-project-directory-structure)
5. [Core Features & Functional Modules](#5-core-features--functional-modules)
6. [Database Schema & Ledger Architecture](#6-database-schema--ledger-architecture)
7. [API Specification & Protocols](#7-api-specification--protocols)
8. [Frontend & Design System](#8-frontend--design-system)
9. [Role-Based Access Control (RBAC)](#9-role-based-access-control-rbac)
10. [Environment Configuration & Variables](#10-environment-configuration--variables)
11. [Installation & Getting Started](#11-installation--getting-started)
12. [Database Inspection & Helpful Commands](#12-database-inspection--helpful-commands)
13. [Testing, Quality & Developer Guidelines](#13-testing-quality--developer-guidelines)

---

## 1. Executive Summary & Business Value

*Source of Truth: `PRD.md`*

In retail and distribution supply chains, poor inventory visibility and manual demand planning lead to inventory distortion—causing severe stockouts on high-velocity items and costly excess holding capital on slow-moving inventory.

*   **Problem:** Stockouts cost retailers billions annually in missed revenue, while excess inventory ties up working capital and warehouse space.
*   **Value Proposition:** Real-time multi-location tracking paired with automated AI/ML demand forecasting minimizes distortion, reduces stockouts by up to 35%, and cuts holding costs by 10–20%.
*   **Target Users:** Inventory Planners, Supply Chain Managers, Warehouse Clerks, Procurement Buyers, and Retail/E-commerce Operators.

---

## 2. System Architecture

*Source of Truth: `ARCHITECTURE.md`*

The platform follows a **Domain-Driven Modular Monolith** architecture:

```
+-----------------------------------------------------------------------------------+
|                                 Next.js 16 Web Client                             |
|        (App Router, React 19, React Query, Tailwind CSS v4, Lucide Icons)        |
+-----------------------------------------------------------------------------------+
                                          |
                                   HTTPS / REST API
                                          v
+-----------------------------------------------------------------------------------+
|                              FastAPI Application Server                           |
|  +-------------------+  +--------------------+  +-------------------------------+  |
|  | Auth & Users      |  | Inventory & SKUs   |  | Purchasing & POs              |  |
|  +-------------------+  +--------------------+  +-------------------------------+  |
|  | ML Forecasting    |  | Channel Sync/Hooks |  | Ledger Engine (Atomic Locks)  |  |
|  +-------------------+  +--------------------+  +-------------------------------+  |
+-----------------------------------------------------------------------------------+
                 |                                                 |
         Async SQL (asyncpg)                               Background Tasks
                 v                                                 v
+------------------------------------+             +--------------------------------+
|       PostgreSQL 15 Database       |             |          Redis 7 Queue         |
|  * Append-only Transaction Ledger  |             |  * Background sync worker      |
|  * Row-level locking (FOR UPDATE)  |             |  * Webhook queue & rate limits |
|  * Materialized stock snapshots    |             |  * ML batch forecast jobs      |
+------------------------------------+             +--------------------------------+
```

### Key Architectural Tenets
1. **The Ledger Pattern:** Direct mutations on inventory stock totals are prohibited. All stock alterations are recorded as immutable, append-only entries in `inventory_transactions`.
2. **Atomic Concurrency Control:** Multi-location inventory adjustments and transfers execute inside strict database transactions using pessimistic row-level locking (`SELECT ... FOR UPDATE`) to prevent race conditions.
3. **Decoupled Background Tasks:** Heavy operations (e.g. ML time-series predictions, CSV bulk imports, e-commerce webhook ingestion) are queued into Redis and processed asynchronously.
4. **Tenant Isolation:** Every table and query enforces multi-tenancy via `tenant_id` validation at the API middleware and database layer.

---

## 3. Technology Stack

### Backend
*   **Language & Runtime:** Python 3.11+
*   **Web Framework:** [FastAPI](https://fastapi.tiangolo.com/) (Asynchronous ASGI)
*   **Database ORM:** [SQLAlchemy 2.0](https://www.sqlalchemy.org/) (Async Engine with `asyncpg`)
*   **Schema Migrations:** [Alembic](https://alembic.sqlalchemy.org/)
*   **Data Validation & Settings:** [Pydantic v2](https://docs.pydantic.dev/) & `pydantic-settings`
*   **Security:** Passwords hashed with `bcrypt`, stateless sessions via `PyJWT` (HS256)
*   **ML Engine:** `Prophet`, `XGBoost`, `scikit-learn` for demand forecasting

### Database & Caching
*   **Primary Database:** [PostgreSQL 15](https://www.postgresql.org/) (ACID-compliant relational store)
*   **In-Memory Broker & Cache:** [Redis 7](https://redis.io/)

### Frontend
*   **Framework:** [Next.js 16](https://nextjs.org/) (React 19, App Router)
*   **Styling:** [Tailwind CSS v4](https://tailwindcss.com/)
*   **Server State & Caching:** [@tanstack/react-query v5](https://tanstack.com/query)
*   **Icons:** [lucide-react](https://lucide.dev/)
*   **Language:** TypeScript 5 (Strict Mode)

### Infrastructure & Reverse Proxy
*   **Containerization:** Docker & Docker Compose
*   **Proxy:** Nginx (Reverse proxy, rate limiting, and SSL termination)

---

## 4. Project Directory Structure

```text
mini project-1/
├── AGENTS.md                  # Strict AI coding agent guidelines & conventions
├── API.md                     # REST API endpoint definitions, schemas, & error formats
├── ARCHITECTURE.md            # Modular monolith architectural design & data flow
├── DATABASE.md                # Relational database schema, ledger pattern, & indexes
├── DESIGN.md                  # UI design principles, 8-point grid, & color tokens
├── PRD.md                     # Product Requirements Document & functional specs
├── README.md                  # Master project documentation
├── package.json               # Root scripts to orchestrate frontend & backend
├── docker-compose.yml         # Development multi-container orchestration
├── docker-compose.prod.yml    # Production container definitions
├── docker-compose.local.yml   # Local port overrides
│
├── backend/                   # FastAPI Backend Application
│   ├── alembic/               # Database migration scripts
│   ├── src/
│   │   ├── api/               # API routers & dependency injection (Auth, RBAC)
│   │   │   ├── auth.py        # Login, registration, token refresh
│   │   │   ├── dependencies.py# Session and user authorization middleware
│   │   │   ├── inventory.py   # Stock transactions, adjustments, transfers
│   │   │   ├── locations.py   # Warehouse and retail store locations
│   │   │   ├── products.py    # Products, SKUs, and categories
│   │   │   ├── users.py       # User management and roles
│   │   │   └── webhooks.py    # Shopify / Square external event ingestion
│   │   ├── core/              # Global app configuration, database engine, security
│   │   ├── domain/            # Domain-driven business logic modules
│   │   │   ├── forecasting/   # Time-series demand forecasting logic
│   │   │   ├── integrations/  # E-commerce connector adapters (Shopify, Square)
│   │   │   ├── inventory/     # Inventory ledger models, schemas, and services
│   │   │   ├── purchasing/    # Purchase order generation and replenishment
│   │   │   └── users/         # Tenant and User SQLAlchemy models
│   │   ├── ml/                # Forecast training and batch inference pipelines
│   │   ├── tasks/             # Celery / Redis asynchronous task definitions
│   │   └── main.py            # FastAPI entry point & CORS configuration
│   ├── tests/                 # Pytest test suite
│   ├── requirements.txt       # Python dependencies
│   └── pyproject.toml         # Python tool configurations (Ruff, Pytest)
│
├── frontend/                  # Next.js 16 Client Application
│   ├── src/
│   │   ├── app/               # App Router pages & layouts
│   │   │   ├── page.tsx       # Main Executive KPI Dashboard
│   │   │   ├── inventory/     # Inventory Catalog & SKU master list
│   │   │   ├── forecasting/   # Demand forecast charts & risk alerts
│   │   │   ├── purchasing/    # Suggested POs & vendor order approval
│   │   │   ├── settings/      # Tenant settings, channel integrations, users
│   │   │   ├── login/         # Authentication screen
│   │   │   └── signup/        # Organization registration screen
│   │   ├── components/        # Reusable UI component library (DESIGN.md)
│   │   │   ├── inventory/     # CreateSkuModal, StockAdjustModal
│   │   │   ├── layout/        # Sidebar, Header, Navigation
│   │   │   ├── providers/     # React Query client provider
│   │   │   └── ui/            # DataTable, Button, Card, Badge, Skeleton
│   │   ├── hooks/             # Custom React Query fetching and mutation hooks
│   │   └── lib/               # API clients, auth token storage, utility helpers
│   ├── package.json           # Frontend dependencies & scripts
│   └── tsconfig.json          # TypeScript compiler configuration
│
└── nginx/                     # Reverse proxy configurations
    ├── default.conf           # Production Nginx reverse proxy
    └── default.local.conf     # Local development Nginx overrides
```

---

## 5. Core Features & Functional Modules

### 1. Catalog & SKU Management
*   **Hierarchical Categories:** Nested category trees for structured taxonomy.
*   **Product Variants (SKUs):** Each product can contain multiple SKUs with custom SKU codes, unit purchase costs, sales prices, supplier IDs, and lead times in days.
*   **Search & Multi-Filter:** Real-time instant filtering by category and full-text search across SKU codes and product names.

### 2. Multi-Location Inventory & The Ledger
*   **Unlimited Locations:** Support for distinct warehouses, distribution hubs, and retail stores.
*   **The Ledger Engine:** Every stock movement is an immutable row in `inventory_transactions`:
    *   `Receive`: Inbound stock arrival against purchase orders or supplier shipments.
    *   `Ship`: Outbound stock depletion from customer sales or channel fulfillment.
    *   `Adjust`: Manual inventory balance corrections with required reason codes.
    *   `Transfer`: Two-legged atomic stock movements between warehouses.
*   **Current Stock Snapshot:** The `inventory_levels` table stores `on_hand`, `reserved`, and computed `available` (`on_hand - reserved`) stock.

### 3. Automated Replenishment & Low-Stock Alerts
*   **Dynamic Reorder Points:** Calculated per SKU:
    $$\text{Reorder Point} = (\text{Daily Demand} \times \text{Lead Time Days}) + \text{Safety Stock}$$
*   **Suggested Purchase Orders:** When available inventory drops below the reorder point, the system automatically drafts suggested purchase orders grouped by vendor with recommended replenishment quantities.

### 4. AI/ML Demand Forecasting
*   **Time-Series Analysis:** Evaluates historical sales timelines, weekly seasonality, promotional events, and trends.
*   **Forecast Models:** Integrates Prophet and XGBoost to generate 30-day, 60-day, and 90-day demand curves per SKU per location.
*   **Risk Categorization:** Flags high-risk stockout items and overstocked items directly on the dashboard.

### 5. Multi-Channel Synchronization & Webhooks
*   **Live Channel Sync:** Connectors for Shopify and Square.
*   **Incoming Webhooks:** Dedicated `/api/v1/webhooks/{provider}` endpoints ingest external order events and decrement warehouse stock in near real-time.

---

## 6. Database Schema & Ledger Architecture

*Source of Truth: `DATABASE.md`*

### Database Tables Breakdown

| Domain | Table | Purpose |
| :--- | :--- | :--- |
| **Tenancy & Auth** | `tenants` | Multi-tenant tenant accounts |
| | `users` | User credentials, bcrypt password hashes, and assigned RBAC roles |
| **Catalog** | `categories` | Hierarchical product classification |
| | `products` | Base product master records |
| | `skus` | Distinct variants, costs, prices, and lead times |
| **Inventory** | `locations` | Warehouses and retail storefronts |
| | `inventory_levels` | Current materialized stock snapshot (`on_hand`, `reserved`, `available`) |
| | `inventory_transactions` | **Append-only ledger audit trail** (`Receive`, `Ship`, `Adjust`, `Transfer`) |
| **Purchasing** | `purchase_orders` | Vendor purchase orders (`Draft`, `Sent`, `Partially Received`, `Completed`) |
| | `po_items` | Individual line items on purchase orders |
| **Forecasting** | `sales_history` | Cleaned historical sales time-series for ML training |
| | `demand_forecasts` | Model output predictions with confidence intervals |
| **Integrations** | `channel_integrations` | E-commerce credentials and API sync configurations |
| | `integration_sync_logs` | Audit log of outbound syncs and inbound webhook payloads |

---

## 7. API Specification & Protocols

*Source of Truth: `API.md`*

*   **Base URL:** `http://localhost:8000/api/v1`
*   **Interactive Docs (Swagger UI):** `http://localhost:8000/docs`
*   **Authentication:** `Authorization: Bearer <JWT_ACCESS_TOKEN>`

### Primary API Routes

```
Authentication & Users
  POST   /api/v1/auth/register          # Register tenant and admin user
  POST   /api/v1/auth/login             # Authenticate and receive JWT token
  GET    /api/v1/users/me               # Retrieve current user context and permissions

Catalog & Products
  GET    /api/v1/inventory/categories   # List product categories
  POST   /api/v1/inventory/categories   # Create a category
  GET    /api/v1/inventory/products     # List all products
  POST   /api/v1/inventory/products     # Create a new product
  GET    /api/v1/inventory/skus         # Paginated catalog SKUs with prices & costs
  POST   /api/v1/inventory/skus         # Create a new SKU variant

Inventory Operations (Ledger Engine)
  GET    /api/v1/inventory/levels       # Real-time stock counts by SKU and location
  POST   /api/v1/inventory/adjust       # Record stock count adjustment
  POST   /api/v1/inventory/transfer     # Atomic inter-location stock transfer
  GET    /api/v1/inventory/transactions # Historical audit trail of ledger operations

Demand Forecasting & Purchasing
  GET    /api/v1/forecasting/predictions# View predicted demand curves and stockout risk
  POST   /api/v1/forecasting/generate   # Trigger on-demand forecast job
  GET    /api/v1/purchasing/orders      # List purchase orders
  POST   /api/v1/purchasing/orders      # Create or approve a replenishment order

Integrations & Webhooks
  POST   /api/v1/integrations/connect   # Connect Shopify / Square store
  POST   /api/v1/webhooks/{provider}    # Public webhook listener for channel order events
```

---

## 8. Frontend & Design System

*Source of Truth: `DESIGN.md`*

*   **Grid System:** Strict 8-point spacing grid (`4px`, `8px`, `16px`, `24px`, `32px`, `48px`).
*   **Color Ratio:** 60-30-10 Rule:
    *   `60%`: Clean neutral light/slate backgrounds.
    *   `30%`: Structural panels, cards, and primary text typography.
    *   `10%`: Focused accents (Primary Brand Blue, Success Green, Danger Red).
*   **Accessibility:** WCAG 2.2 AA compliant contrast ratio (minimum 4.5:1 for standard text).
*   **Component Architecture:** Reusable, type-safe React components located in `frontend/src/components/`:
    *   `DataTable.tsx`: Sortable, filterable, paginated data table.
    *   `CreateSkuModal.tsx`: Accessible modal dialog for catalog creation.
    *   `Badge.tsx`: Semantic colored badges for statuses (`Active`, `Low Stock`, `Out of Stock`).
    *   `Card.tsx`: Metric and chart containers with uniform padding and borders.

---

## 9. Role-Based Access Control (RBAC)

| Role | Permissions & Boundaries |
| :--- | :--- |
| **Admin** | Full system control, billing, user creation, role assignment, integrations. |
| **Inventory Manager** | Catalog CRUD, stock adjustments, inter-location transfers, forecast reviews. |
| **Purchaser** | View forecasts, create and edit purchase orders, approve supplier POs. |
| **Warehouse Staff** | Perform receiving and shipping scans; strictly cannot view costs or financials. |
| **Analyst** | Read-only access to inventory, export reports, run on-demand forecast models. |
| **Viewer** | Read-only access to basic dashboards and inventory counts. |

---

## 10. Environment Configuration & Variables

Configuration is loaded from root `.env` (or `.env.production` in production).

| Variable | Description | Default / Example |
| :--- | :--- | :--- |
| `ENVIRONMENT` | Runtime environment (`development`, `production`) | `development` |
| `LOG_LEVEL` | Logging verbosity (`DEBUG`, `INFO`, `WARNING`, `ERROR`) | `INFO` |
| `DATABASE_URL` | Async PostgreSQL connection string | `postgresql+asyncpg://...` |
| `REDIS_URL` | Redis connection URL | `redis://localhost:6379/0` |
| `JWT_SECRET_KEY` | 64-character secret for signing JWT access tokens | High-entropy secret |
| `JWT_ALGORITHM` | Token encryption algorithm | `HS256` |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Access token lifespan | `60` |
| `ENCRYPTION_KEY` | Base64 32-byte key for AES-256-GCM symmetric encryption | Base64 key |
| `ALLOWED_ORIGINS` | Permitted CORS origins for the API | `http://localhost:3000` |
| `NEXT_PUBLIC_API_URL` | API Base URL exposed to frontend client | `http://localhost:8000/api/v1` |

---

## 11. Installation & Getting Started

### Prerequisites
*   [Node.js](https://nodejs.org/) (v20+ recommended)
*   [Python](https://www.python.org/) (v3.11+ recommended)
*   [Docker Desktop](https://www.docker.com/) (for PostgreSQL and Redis)

---

### Step 1: Clone & Configure Environment
```bash
git clone <repository_url>
cd "mini project-1"

# Copy environment variables
cp .env.example .env
```

---

### Step 2: Start PostgreSQL & Redis via Docker
To run the production-grade PostgreSQL 15 and Redis containers:
```bash
docker compose -f docker-compose.prod.yml up -d postgres redis
```
*(Verify both containers are running with `docker ps`)*

---

### Step 3: Run Database Migrations
Activate your Python virtual environment and run Alembic migrations:
```powershell
# Windows PowerShell
.\backend\.venv\Scripts\Activate.ps1
alembic upgrade head
```

---

### Step 4: Start the Development Servers

Open two separate terminal windows from the project root:

**Terminal 1 — Frontend (Next.js):**
```powershell
npm run dev:frontend
```
*Frontend runs at: [http://localhost:3000](http://localhost:3000)*

**Terminal 2 — Backend API (FastAPI):**
```powershell
npm run dev:backend
```
*Backend runs at: [http://localhost:8000](http://localhost:8000)*  
*API Documentation (Swagger): [http://localhost:8000/docs](http://localhost:8000/docs)*

---

## 12. Database Inspection & Helpful Commands

### Direct SQL Inspection via Docker
To run queries directly against your PostgreSQL database:

```powershell
# 1. Inspect all SKUs and linked Products
docker exec -it smart_inventory_prod_db psql -U smart_inv_admin -d smart_inventory_prod -c "SELECT s.sku_code, p.name AS product_name, c.name AS category_name, s.unit_cost, s.sales_price, s.lead_time_days FROM skus s JOIN products p ON s.product_id = p.id LEFT JOIN categories c ON p.category_id = c.id;"

# 2. Open an interactive psql session
docker exec -it smart_inventory_prod_db psql -U smart_inv_admin -d smart_inventory_prod
```

### Useful psql Shortcuts
*   `\dt` : List all database tables
*   `\d <table_name>` : View schema and constraints for a specific table
*   `\q` : Exit the psql prompt

---

## 13. Testing, Quality & Developer Guidelines

*Source of Truth: `AGENTS.md`*

### Backend Unit & Integration Tests
Pytest is configured for business logic, ledger balance math, and atomic locking validation:
```powershell
npm run test:backend
```

### Code Formatting and Linting
```powershell
# Check Python code style with Ruff
npm run lint:backend

# Automatically format Python code
npm run format:backend

# Check TypeScript and Next.js frontend code
npm run lint:frontend
```

### Developer Discipline & Best Practices
1. **Never perform direct updates on stock totals:** Always execute operations through `inventory_transactions` and update `inventory_levels` using `SELECT ... FOR UPDATE`.
2. **Type Safety:** Strict Python type hints and Pydantic validation on the backend; TypeScript interfaces with zero `any` on the frontend.
3. **No Unnecessary Dependencies:** Leverage FastAPI, SQLAlchemy, Next.js, and React Query before considering new packages.
4. **Secret Protection:** Never commit `.env` or hardcode sensitive tokens or passwords into source code.
