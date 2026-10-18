# Smart Inventory Management & Demand Forecasting: Database Schema

## Database Technology

**PostgreSQL (version 15+)**. Chosen for its advanced concurrency controls, ACID compliance (critical for atomic inventory operations), JSONB support for flexible integration mappings, and robust indexing capabilities.

## Architecture Philosophy

The inventory design utilizes a **Ledger Pattern**. Direct modifications to inventory totals are prohibited. Instead, all changes are written as append-only records to `inventory_transactions`. The `inventory_levels` table acts as a materialized state representing the current snapshot, maintained via strict database transactions. This guarantees the audit trail and 99.9% accuracy target.

## Tables and Columns

### 1. Multi-Tenancy & Authorization
**`tenants`**
*   `id` (UUID, PK)
*   `name` (VARCHAR)
*   `created_at` (TIMESTAMP)

**`users`**
*   `id` (UUID, PK)
*   `tenant_id` (UUID, FK)
*   `email` (VARCHAR, Unique per tenant)
*   `password_hash` (VARCHAR)
*   `role` (VARCHAR) - *Admin, Inventory Manager, Purchaser, Warehouse Staff, Analyst, Viewer*
*   `is_active` (BOOLEAN)

### 2. Product Master
**`categories`**
*   `id` (UUID, PK)
*   `tenant_id` (UUID, FK)
*   `parent_id` (UUID, FK, Nullable)
*   `name` (VARCHAR)

**`products`**
*   `id` (UUID, PK)
*   `tenant_id` (UUID, FK)
*   `category_id` (UUID, FK)
*   `name` (VARCHAR)
*   `description` (TEXT)
*   `base_unit` (VARCHAR)

**`skus`** (Variants of a product)
*   `id` (UUID, PK)
*   `tenant_id` (UUID, FK)
*   `product_id` (UUID, FK)
*   `sku_code` (VARCHAR, Unique per tenant)
*   `supplier_id` (UUID, FK, Nullable)
*   `unit_cost` (DECIMAL)
*   `sales_price` (DECIMAL)
*   `lead_time_days` (INTEGER)

### 3. Inventory & Locations
**`locations`**
*   `id` (UUID, PK)
*   `tenant_id` (UUID, FK)
*   `name` (VARCHAR)
*   `type` (VARCHAR) - *Warehouse, Store*
*   `address` (TEXT)

**`inventory_levels`** (Current Snapshot)
*   `id` (UUID, PK)
*   `tenant_id` (UUID, FK)
*   `sku_id` (UUID, FK)
*   `location_id` (UUID, FK)
*   `on_hand` (INTEGER) - *Total physical stock*
*   `reserved` (INTEGER) - *Committed to unfulfilled sales orders*
*   `available` (INTEGER) - *Generated column/view: (on_hand - reserved)*
*   `reorder_point` (INTEGER)
*   `reorder_quantity` (INTEGER)
*   `version` (INTEGER) - *Optimistic locking token*

**`inventory_transactions`** (The Ledger / Audit Trail)
*   `id` (UUID, PK)
*   `tenant_id` (UUID, FK)
*   `sku_id` (UUID, FK)
*   `location_id` (UUID, FK)
*   `user_id` (UUID, FK)
*   `transaction_type` (VARCHAR) - *Receive, Ship, Adjust, Transfer*
*   `quantity_change` (INTEGER) - *Positive or negative*
*   `reference_id` (VARCHAR) - *e.g., PO #, Sales Order #*
*   `reason` (VARCHAR)
*   `created_at` (TIMESTAMP)

### 4. Supply Chain & Demand
**`purchase_orders`**
*   `id` (UUID, PK)
*   `tenant_id` (UUID, FK)
*   `supplier_id` (UUID, FK)
*   `status` (VARCHAR) - *Draft, Sent, Partially Received, Completed*
*   `expected_date` (DATE)

**`po_items`**
*   `id` (UUID, PK)
*   `po_id` (UUID, FK)
*   `sku_id` (UUID, FK)
*   `quantity_ordered` (INTEGER)
*   `quantity_received` (INTEGER)
*   `unit_cost` (DECIMAL)

**`sales_history`** (Time-series for ML Forecasting)
*   `id` (UUID, PK)
*   `tenant_id` (UUID, FK)
*   `sku_id` (UUID, FK)
*   `location_id` (UUID, FK)
*   `sales_date` (DATE)
*   `quantity_sold` (INTEGER)
*   `channel` (VARCHAR) - *e.g., Shopify, POS*

**`demand_forecasts`** (ML Outputs)
*   `id` (UUID, PK)
*   `tenant_id` (UUID, FK)
*   `sku_id` (UUID, FK)
*   `forecast_date` (DATE)
*   `predicted_demand` (INTEGER)
*   `confidence_lower` (INTEGER)
*   `confidence_upper` (INTEGER)
*   `generated_at` (TIMESTAMP)

### 5. Integrations Configuration
**`integration_configs`**
*   `id` (UUID, PK)
*   `tenant_id` (UUID, FK)
*   `provider` (VARCHAR) - *Shopify, Square*
*   `api_key_encrypted` (TEXT)
*   `settings` (JSONB)
*   `last_sync_at` (TIMESTAMP)

## Primary & Foreign Keys / Relationships
*   **SKUs** belong to **Products** (One-to-Many).
*   **Inventory Levels** map exactly one **SKU** to one **Location** (Many-to-Many bridging).
*   **Inventory Transactions** link to a **SKU**, **Location**, and the **User** who authorized the change.
*   **Sales History** and **Demand Forecasts** belong to **SKUs**.
*   **All tables** possess a `tenant_id` Foreign Key linking to `tenants` to ensure strict SaaS data isolation.

## Constraints and Validation
*   **Unique Constraints:** 
    *   `(tenant_id, sku_code)` in `skus` (Ensures SKUs are unique per business).
    *   `(tenant_id, sku_id, location_id)` in `inventory_levels` (Prevents duplicate tracking rows).
*   **Check Constraints:**
    *   `inventory_levels.on_hand >= 0` (Unless specifically configured for backorders, physical stock cannot drop below zero).
    *   `po_items.quantity_received <= po_items.quantity_ordered` (Prevents receiving more than requested without an override).
    *   `inventory_transactions.quantity_change != 0` (Prevents zero-impact ledger bloat).

## Indexes Based on Real Queries
*   **Dashboard / Alerts:** `CREATE INDEX idx_inv_levels_reorder ON inventory_levels (tenant_id, sku_id) WHERE on_hand <= reorder_point;` (Speeds up low-stock alerts).
*   **Transactions List:** `CREATE INDEX idx_inv_tx_created ON inventory_transactions (tenant_id, sku_id, created_at DESC);` (Fast retrieval of SKU history/audit trails).
*   **Sales History for ML:** `CREATE INDEX idx_sales_history_ml ON sales_history (tenant_id, sku_id, sales_date);` (Optimizes batch pulls for the XGBoost/Prophet pipeline).
*   **SKU Search:** `CREATE INDEX idx_sku_code ON skus (tenant_id, sku_code);`

## Ownership and Authorization
*   Database roles are kept simple (e.g., `app_user`, `migrations_user`, `ml_worker`). Application-level Role-Based Access Control (RBAC) defined in the PRD handles specific module access. 
*   `user_id` is stamped on every `inventory_transactions` row, strictly adhering to the audit requirement.

## Row-Level Security (RLS)
*   RLS will be enabled on all core tables keyed to `tenant_id`.
*   A default policy will be applied: `CREATE POLICY tenant_isolation_policy ON skus USING (tenant_id = current_setting('app.current_tenant')::uuid);`. This guarantees that a bug in the application code cannot accidentally leak one client's inventory data to another.

## Sensitive-Data Handling
*   `users.password_hash` utilizes bcrypt.
*   `integration_configs.api_key_encrypted` is encrypted at the application level using symmetric encryption (e.g., AES-256-GCM) before being persisted to the database. The decryption key resides in the environment configuration, securely injected at runtime.
*   Data at rest is encrypted via the cloud provider's disk encryption (e.g., AWS KMS on RDS).

## Migration and Seed Strategy
*   **Migrations:** Handled via Alembic (Python). Migrations are version-controlled, automated, and strictly forward-only in production environments.
*   **Seeding:** Scripts are provided to seed a `System Admin` account and default `Roles`. For new tenants, bulk CSV import modules map raw legacy data directly into the `skus`, `locations`, and creates initial `inventory_transactions` entries representing starting balances.

## Backup and Recovery Considerations
*   **Automated Backups:** Daily full snapshots with continuous Write-Ahead Log (WAL) archiving via managed PostgreSQL, achieving Point-in-Time Recovery (PITR) up to the last 5 minutes.
*   **Retention:** Historical sales and transaction data retained for 3-5 years (partitioned by year for performance).
*   **High Availability:** Multi-AZ (Availability Zone) active-standby deployment to ensure the 99.9% uptime target.