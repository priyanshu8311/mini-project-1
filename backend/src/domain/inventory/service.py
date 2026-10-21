import math
from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.src.core.errors import ConflictException, NotFoundException, ValidationException
from backend.src.domain.inventory.models import (
    SKU,
    Category,
    InventoryLevel,
    InventoryTransaction,
    Location,
    Product,
    TransactionType,
)
from backend.src.domain.inventory.schemas import (
    CategoryCreate,
    InventoryLevelResponse,
    InventoryTransactionCreate,
    InventoryTransactionResponse,
    LocationCreate,
    PaginationMeta,
    ProductCreate,
    SKUCreate,
    SKUResponse,
    SKUUpdate,
)


class CatalogService:
    """Service handling master data operations for Categories, Products, SKUs, and Locations."""

    # --- Categories ---
    @staticmethod
    async def create_category(
        db: AsyncSession,
        tenant_id: UUID,
        payload: CategoryCreate,
    ) -> Category:
        """Create a new product category."""
        if payload.parent_id:
            parent = await CatalogService.get_category_by_id(db, tenant_id, payload.parent_id)
            if not parent:
                raise NotFoundException("Parent Category", payload.parent_id)

        category = Category(
            tenant_id=tenant_id,
            parent_id=payload.parent_id,
            name=payload.name.strip(),
        )
        db.add(category)
        await db.flush()
        await db.refresh(category)
        return category

    @staticmethod
    async def list_categories(
        db: AsyncSession,
        tenant_id: UUID,
    ) -> list[Category]:
        """List all categories for a tenant."""
        result = await db.execute(
            select(Category)
            .where(Category.tenant_id == tenant_id)
            .order_by(Category.name.asc())
        )
        return list(result.scalars().all())

    @staticmethod
    async def get_category_by_id(
        db: AsyncSession,
        tenant_id: UUID,
        category_id: UUID,
    ) -> Category:
        """Fetch category by ID with tenant isolation."""
        result = await db.execute(
            select(Category).where(
                Category.id == category_id,
                Category.tenant_id == tenant_id,
            )
        )
        category = result.scalar_one_or_none()
        if not category:
            raise NotFoundException("Category", category_id)
        return category

    # --- Products ---
    @staticmethod
    async def create_product(
        db: AsyncSession,
        tenant_id: UUID,
        payload: ProductCreate,
    ) -> Product:
        """Create a new product."""
        await CatalogService.get_category_by_id(db, tenant_id, payload.category_id)

        product = Product(
            tenant_id=tenant_id,
            category_id=payload.category_id,
            name=payload.name.strip(),
            description=payload.description.strip() if payload.description else None,
            base_unit=payload.base_unit.strip(),
        )
        db.add(product)
        await db.flush()
        await db.refresh(product)
        return product

    @staticmethod
    async def get_product_by_id(
        db: AsyncSession,
        tenant_id: UUID,
        product_id: UUID,
    ) -> Product:
        """Fetch product by ID with tenant isolation."""
        result = await db.execute(
            select(Product).where(
                Product.id == product_id,
                Product.tenant_id == tenant_id,
            )
        )
        product = result.scalar_one_or_none()
        if not product:
            raise NotFoundException("Product", product_id)
        return product

    # --- Locations ---
    @staticmethod
    async def create_location(
        db: AsyncSession,
        tenant_id: UUID,
        payload: LocationCreate,
    ) -> Location:
        """Create an inventory physical location."""
        location = Location(
            tenant_id=tenant_id,
            name=payload.name.strip(),
            type=payload.type.value if hasattr(payload.type, "value") else str(payload.type),
            address=payload.address.strip() if payload.address else None,
        )
        db.add(location)
        await db.flush()
        await db.refresh(location)
        return location

    @staticmethod
    async def list_locations(
        db: AsyncSession,
        tenant_id: UUID,
    ) -> list[Location]:
        """List all physical locations for a tenant."""
        result = await db.execute(
            select(Location)
            .where(Location.tenant_id == tenant_id)
            .order_by(Location.name.asc())
        )
        return list(result.scalars().all())

    @staticmethod
    async def get_location_by_id(
        db: AsyncSession,
        tenant_id: UUID,
        location_id: UUID,
    ) -> Location:
        """Fetch location by ID with tenant isolation."""
        result = await db.execute(
            select(Location).where(
                Location.id == location_id,
                Location.tenant_id == tenant_id,
            )
        )
        location = result.scalar_one_or_none()
        if not location:
            raise NotFoundException("Location", location_id)
        return location

    # --- SKUs ---
    @staticmethod
    async def create_sku(
        db: AsyncSession,
        tenant_id: UUID,
        payload: SKUCreate,
    ) -> SKUResponse:
        """Create a new SKU variant, validating tenant uniqueness."""
        clean_code = payload.sku_code.strip().upper()

        # Check unique constraint on (tenant_id, sku_code)
        existing = await db.execute(
            select(SKU).where(
                SKU.tenant_id == tenant_id,
                SKU.sku_code == clean_code,
            )
        )
        if existing.scalar_one_or_none():
            raise ConflictException(f"SKU with code '{clean_code}' already exists for this tenant.")

        # Determine product association
        if payload.product_id:
            product = await CatalogService.get_product_by_id(db, tenant_id, payload.product_id)
        elif payload.product_name:
            target_cat_id = payload.category_id
            if not target_cat_id:
                # Find or create a default 'General' category for this tenant
                cat_result = await db.execute(
                    select(Category).where(
                        Category.tenant_id == tenant_id,
                        Category.name == "General",
                    )
                )
                default_cat = cat_result.scalar_one_or_none()
                if not default_cat:
                    default_cat = Category(
                        tenant_id=tenant_id,
                        name="General",
                    )
                    db.add(default_cat)
                    await db.flush()
                target_cat_id = default_cat.id

            product = await CatalogService.create_product(
                db,
                tenant_id,
                ProductCreate(
                    name=payload.product_name,
                    category_id=target_cat_id,
                ),
            )
        else:
            raise ValidationException(
                "Either 'product_id' or 'product_name' must be provided."
            )

        sku = SKU(
            tenant_id=tenant_id,
            product_id=product.id,
            sku_code=clean_code,
            supplier_id=payload.supplier_id,
            unit_cost=payload.unit_cost,
            sales_price=payload.sales_price,
            lead_time_days=payload.lead_time_days,
        )
        db.add(sku)
        await db.flush()
        await db.refresh(sku)

        # Retrieve category for display name
        category = await CatalogService.get_category_by_id(db, tenant_id, product.category_id)

        return SKUResponse(
            id=sku.id,
            tenant_id=sku.tenant_id,
            product_id=sku.product_id,
            sku_code=sku.sku_code,
            supplier_id=sku.supplier_id,
            unit_cost=sku.unit_cost,
            sales_price=sku.sales_price,
            lead_time_days=sku.lead_time_days,
            created_at=sku.created_at,
            product_name=product.name,
            category_name=category.name,
        )

    @staticmethod
    def _to_sku_response(sku: SKU) -> SKUResponse:
        cat_name = (
            sku.product.category.name
            if sku.product and sku.product.category
            else None
        )
        return SKUResponse(
            id=sku.id,
            tenant_id=sku.tenant_id,
            product_id=sku.product_id,
            sku_code=sku.sku_code,
            supplier_id=sku.supplier_id,
            unit_cost=sku.unit_cost,
            sales_price=sku.sales_price,
            lead_time_days=sku.lead_time_days,
            created_at=sku.created_at,
            product_name=sku.product.name if sku.product else None,
            category_name=cat_name,
        )

    @staticmethod
    async def list_skus(
        db: AsyncSession,
        tenant_id: UUID,
        page: int = 1,
        limit: int = 50,
        search: str | None = None,
        category_id: UUID | None = None,
        sort_by: str = "created_at",
        sort_order: str = "desc",
    ) -> tuple[list[SKUResponse], PaginationMeta]:
        """List and search SKUs with pagination envelope."""
        page = max(1, page)
        limit = max(1, min(limit, 100))

        # Base query with product & category joined
        query = (
            select(SKU)
            .join(Product, SKU.product_id == Product.id)
            .join(Category, Product.category_id == Category.id)
            .where(SKU.tenant_id == tenant_id)
            .options(selectinload(SKU.product).selectinload(Product.category))
        )

        if category_id:
            query = query.where(Product.category_id == category_id)

        if search:
            clean_search = search.strip().lower()
            escaped_search = (
                clean_search.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
            )
            search_pattern = f"%{escaped_search}%"
            search_cond = or_(
                func.lower(SKU.sku_code).like(search_pattern, escape="\\"),
                func.lower(Product.name).like(search_pattern, escape="\\"),
            )
            query = query.where(search_cond)

        # Total count query
        count_query = (
            select(func.count(SKU.id))
            .join(Product, SKU.product_id == Product.id)
            .where(SKU.tenant_id == tenant_id)
        )
        if category_id:
            count_query = count_query.where(Product.category_id == category_id)
        if search:
            count_query = count_query.where(search_cond)

        total_res = await db.execute(count_query)
        total = total_res.scalar_one()

        # Sorting with safe column allowlist
        allowed_sort_columns = {
            "created_at": SKU.created_at,
            "sku_code": SKU.sku_code,
            "unit_cost": SKU.unit_cost,
            "sales_price": SKU.sales_price,
            "lead_time_days": SKU.lead_time_days,
        }
        sort_column = allowed_sort_columns.get(sort_by, SKU.created_at)
        if sort_order.lower() == "asc":
            query = query.order_by(sort_column.asc())
        else:
            query = query.order_by(sort_column.desc())

        # Pagination
        query = query.offset((page - 1) * limit).limit(limit)
        results = await db.execute(query)
        skus = results.scalars().all()

        sku_responses = [CatalogService._to_sku_response(item) for item in skus]

        total_pages = math.ceil(total / limit) if total > 0 else 1
        meta = PaginationMeta(
            total=total,
            page=page,
            limit=limit,
            total_pages=total_pages,
        )

        return sku_responses, meta

    @staticmethod
    async def get_sku_by_id(
        db: AsyncSession,
        tenant_id: UUID,
        sku_id: UUID,
    ) -> SKUResponse:
        """Fetch single SKU with product and category names."""
        result = await db.execute(
            select(SKU)
            .where(SKU.id == sku_id, SKU.tenant_id == tenant_id)
            .options(selectinload(SKU.product).selectinload(Product.category))
        )
        sku = result.scalar_one_or_none()
        if not sku:
            raise NotFoundException("SKU", sku_id)

        return CatalogService._to_sku_response(sku)

    @staticmethod
    async def update_sku(
        db: AsyncSession,
        tenant_id: UUID,
        sku_id: UUID,
        payload: SKUUpdate,
    ) -> SKUResponse:
        """Update mutable attributes on a SKU."""
        result = await db.execute(
            select(SKU)
            .where(SKU.id == sku_id, SKU.tenant_id == tenant_id)
            .options(selectinload(SKU.product).selectinload(Product.category))
        )
        sku = result.scalar_one_or_none()
        if not sku:
            raise NotFoundException("SKU", sku_id)

        if payload.sku_code:
            clean_code = payload.sku_code.strip().upper()
            if clean_code != sku.sku_code:
                # Check conflict
                existing = await db.execute(
                    select(SKU).where(
                        SKU.tenant_id == tenant_id,
                        SKU.sku_code == clean_code,
                        SKU.id != sku_id,
                    )
                )
                if existing.scalar_one_or_none():
                    raise ConflictException(f"SKU code '{clean_code}' is already in use.")
                sku.sku_code = clean_code

        if payload.supplier_id is not None:
            sku.supplier_id = payload.supplier_id
        if payload.unit_cost is not None:
            sku.unit_cost = payload.unit_cost
        if payload.sales_price is not None:
            sku.sales_price = payload.sales_price
        if payload.lead_time_days is not None:
            sku.lead_time_days = payload.lead_time_days

        await db.flush()
        await db.refresh(sku)

        return CatalogService._to_sku_response(sku)


class InventoryService:
    """Core inventory engine with row-locking, append-only ledger, and stock tracking."""

    @staticmethod
    async def _get_or_create_level_for_update(
        db: AsyncSession,
        tenant_id: UUID,
        sku_id: UUID,
        location_id: UUID,
    ) -> InventoryLevel:
        """Lock or initialize an inventory_level row using pessimistic concurrency."""
        # 1. Verify SKU and Location existence
        sku_res = await db.execute(
            select(SKU).where(SKU.id == sku_id, SKU.tenant_id == tenant_id)
        )
        if not sku_res.scalar_one_or_none():
            raise NotFoundException("SKU", sku_id)

        loc_res = await db.execute(
            select(Location).where(Location.id == location_id, Location.tenant_id == tenant_id)
        )
        if not loc_res.scalar_one_or_none():
            raise NotFoundException("Location", location_id)

        # 2. Select with pessimistic row lock
        query = (
            select(InventoryLevel)
            .where(
                InventoryLevel.tenant_id == tenant_id,
                InventoryLevel.sku_id == sku_id,
                InventoryLevel.location_id == location_id,
            )
            .with_for_update()
        )
        result = await db.execute(query)
        level = result.scalar_one_or_none()

        if not level:
            level = InventoryLevel(
                tenant_id=tenant_id,
                sku_id=sku_id,
                location_id=location_id,
                on_hand=0,
                reserved=0,
                version=1,
            )
            db.add(level)
            await db.flush()
            await db.refresh(level)

        return level

    @staticmethod
    def _to_level_response(item: InventoryLevel) -> InventoryLevelResponse:
        sku_code = item.sku.sku_code if item.sku else None
        prod_name = (
            item.sku.product.name
            if item.sku and item.sku.product
            else None
        )
        loc_name = item.location.name if item.location else None
        loc_type = item.location.type if item.location else None
        return InventoryLevelResponse(
            id=item.id,
            tenant_id=item.tenant_id,
            sku_id=item.sku_id,
            location_id=item.location_id,
            on_hand=item.on_hand,
            reserved=item.reserved,
            available=max(0, item.on_hand - item.reserved),
            reorder_point=item.reorder_point,
            reorder_quantity=item.reorder_quantity,
            version=item.version,
            created_at=item.created_at,
            sku_code=sku_code,
            product_name=prod_name,
            location_name=loc_name,
            location_type=loc_type,
        )

    @staticmethod
    def _to_tx_response(tx: InventoryTransaction) -> InventoryTransactionResponse:
        sku_code = tx.sku.sku_code if tx.sku else None
        prod_name = (
            tx.sku.product.name
            if tx.sku and tx.sku.product
            else None
        )
        loc_name = tx.location.name if tx.location else None
        user_email = tx.user.email if tx.user else None
        return InventoryTransactionResponse(
            id=tx.id,
            tenant_id=tx.tenant_id,
            sku_id=tx.sku_id,
            location_id=tx.location_id,
            user_id=tx.user_id,
            transaction_type=tx.transaction_type,
            quantity_change=tx.quantity_change,
            reference_id=tx.reference_id,
            reason=tx.reason,
            created_at=tx.created_at,
            sku_code=sku_code,
            product_name=prod_name,
            location_name=loc_name,
            user_email=user_email,
        )

    @staticmethod
    async def record_transaction(
        db: AsyncSession,
        tenant_id: UUID,
        user_id: UUID,
        payload: InventoryTransactionCreate,
    ) -> InventoryTransactionResponse:
        """Atomically record a stock operation in the ledger and update inventory levels."""
        if payload.quantity_change == 0:
            raise ValidationException(
                "Quantity change cannot be zero.",
                details=[{"field": "quantity_change", "issue": "Must be non-zero"}],
            )

        if payload.transaction_type == TransactionType.TRANSFER:
            if not payload.target_location_id:
                raise ValidationException(
                    "target_location_id is required for stock transfers.",
                    details=[{"field": "target_location_id", "issue": "Required for transfer"}],
                )
            if payload.location_id == payload.target_location_id:
                raise ValidationException(
                    "Source and destination locations must be distinct.",
                    details=[
                        {
                            "field": "target_location_id",
                            "issue": "Cannot transfer to same location",
                        }
                    ],
                )

            qty = abs(payload.quantity_change)

            # Deterministic lock ordering to prevent cross-transaction deadlocks
            first_loc, second_loc = (
                (payload.location_id, payload.target_location_id)
                if str(payload.location_id) < str(payload.target_location_id)
                else (payload.target_location_id, payload.location_id)
            )

            lvl_a = await InventoryService._get_or_create_level_for_update(
                db, tenant_id, payload.sku_id, first_loc
            )
            lvl_b = await InventoryService._get_or_create_level_for_update(
                db, tenant_id, payload.sku_id, second_loc
            )

            source_level = lvl_a if first_loc == payload.location_id else lvl_b
            target_level = lvl_b if first_loc == payload.location_id else lvl_a

            available_stock = source_level.on_hand - source_level.reserved
            if available_stock < qty:
                err_msg = (
                    f"Insufficient stock ({available_stock}) at source to transfer {qty} units."
                )
                raise ValidationException(
                    err_msg,
                    details=[{"field": "quantity_change", "issue": "Insufficient available stock"}],
                )

            # Update balances atomically
            source_level.on_hand -= qty
            source_level.version += 1
            target_level.on_hand += qty
            target_level.version += 1

            # Ledger entries: Outbound from source, Inbound to destination
            tx_out = InventoryTransaction(
                tenant_id=tenant_id,
                sku_id=payload.sku_id,
                location_id=payload.location_id,
                user_id=user_id,
                transaction_type=TransactionType.TRANSFER.value,
                quantity_change=-qty,
                reference_id=payload.reference_id,
                reason=payload.reason or f"Transfer out to location {payload.target_location_id}",
            )
            tx_in = InventoryTransaction(
                tenant_id=tenant_id,
                sku_id=payload.sku_id,
                location_id=payload.target_location_id,
                user_id=user_id,
                transaction_type=TransactionType.TRANSFER.value,
                quantity_change=qty,
                reference_id=payload.reference_id,
                reason=payload.reason or f"Transfer in from location {payload.location_id}",
            )
            db.add_all([tx_out, tx_in])
            await db.flush()

            # Eager load relationships for response
            res = await db.execute(
                select(InventoryTransaction)
                .where(InventoryTransaction.id == tx_out.id)
                .options(
                    selectinload(InventoryTransaction.sku).selectinload(SKU.product),
                    selectinload(InventoryTransaction.location),
                    selectinload(InventoryTransaction.user),
                )
            )
            return InventoryService._to_tx_response(res.scalar_one())

        elif payload.transaction_type == TransactionType.RECEIVE:
            qty = abs(payload.quantity_change)
            level = await InventoryService._get_or_create_level_for_update(
                db, tenant_id, payload.sku_id, payload.location_id
            )
            level.on_hand += qty
            level.version += 1

            tx = InventoryTransaction(
                tenant_id=tenant_id,
                sku_id=payload.sku_id,
                location_id=payload.location_id,
                user_id=user_id,
                transaction_type=TransactionType.RECEIVE.value,
                quantity_change=qty,
                reference_id=payload.reference_id,
                reason=payload.reason,
            )
            db.add(tx)
            await db.flush()

            res = await db.execute(
                select(InventoryTransaction)
                .where(InventoryTransaction.id == tx.id)
                .options(
                    selectinload(InventoryTransaction.sku).selectinload(SKU.product),
                    selectinload(InventoryTransaction.location),
                    selectinload(InventoryTransaction.user),
                )
            )
            return InventoryService._to_tx_response(res.scalar_one())

        elif payload.transaction_type == TransactionType.SHIP:
            qty = abs(payload.quantity_change)
            level = await InventoryService._get_or_create_level_for_update(
                db, tenant_id, payload.sku_id, payload.location_id
            )
            if level.on_hand < qty:
                raise ValidationException(
                    f"Insufficient on-hand stock ({level.on_hand}) to ship {qty} units.",
                    details=[{"field": "quantity_change", "issue": "Insufficient on-hand stock"}],
                )
            level.on_hand -= qty
            level.version += 1

            tx = InventoryTransaction(
                tenant_id=tenant_id,
                sku_id=payload.sku_id,
                location_id=payload.location_id,
                user_id=user_id,
                transaction_type=TransactionType.SHIP.value,
                quantity_change=-qty,
                reference_id=payload.reference_id,
                reason=payload.reason,
            )
            db.add(tx)
            await db.flush()

            res = await db.execute(
                select(InventoryTransaction)
                .where(InventoryTransaction.id == tx.id)
                .options(
                    selectinload(InventoryTransaction.sku).selectinload(SKU.product),
                    selectinload(InventoryTransaction.location),
                    selectinload(InventoryTransaction.user),
                )
            )
            return InventoryService._to_tx_response(res.scalar_one())

        elif payload.transaction_type == TransactionType.ADJUST:
            level = await InventoryService._get_or_create_level_for_update(
                db, tenant_id, payload.sku_id, payload.location_id
            )
            if payload.quantity_change < 0 and level.on_hand + payload.quantity_change < 0:
                raise ValidationException(
                    f"Stock adjustment would reduce on-hand below zero (current: {level.on_hand}).",
                    details=[
                        {"field": "quantity_change", "issue": "Resulting stock cannot be negative"}
                    ],
                )
            level.on_hand += payload.quantity_change
            level.version += 1

            tx = InventoryTransaction(
                tenant_id=tenant_id,
                sku_id=payload.sku_id,
                location_id=payload.location_id,
                user_id=user_id,
                transaction_type=TransactionType.ADJUST.value,
                quantity_change=payload.quantity_change,
                reference_id=payload.reference_id,
                reason=payload.reason,
            )
            db.add(tx)
            await db.flush()

            res = await db.execute(
                select(InventoryTransaction)
                .where(InventoryTransaction.id == tx.id)
                .options(
                    selectinload(InventoryTransaction.sku).selectinload(SKU.product),
                    selectinload(InventoryTransaction.location),
                    selectinload(InventoryTransaction.user),
                )
            )
            return InventoryService._to_tx_response(res.scalar_one())

        else:
            raise ValidationException(f"Unsupported transaction type '{payload.transaction_type}'.")

    @staticmethod
    async def list_inventory_levels(
        db: AsyncSession,
        tenant_id: UUID,
        page: int = 1,
        limit: int = 50,
        sku_id: UUID | None = None,
        location_id: UUID | None = None,
        stock_status: str | None = None,
        search: str | None = None,
    ) -> tuple[list[InventoryLevelResponse], PaginationMeta]:
        """List and filter current inventory level snapshots."""
        page = max(1, page)
        limit = max(1, min(limit, 100))

        query = (
            select(InventoryLevel)
            .join(InventoryLevel.sku)
            .join(SKU.product)
            .join(InventoryLevel.location)
            .where(InventoryLevel.tenant_id == tenant_id)
            .options(
                selectinload(InventoryLevel.sku).selectinload(SKU.product),
                selectinload(InventoryLevel.location),
            )
        )
        count_query = (
            select(func.count(InventoryLevel.id))
            .join(InventoryLevel.sku)
            .join(SKU.product)
            .join(InventoryLevel.location)
            .where(InventoryLevel.tenant_id == tenant_id)
        )

        if sku_id:
            query = query.where(InventoryLevel.sku_id == sku_id)
            count_query = count_query.where(InventoryLevel.sku_id == sku_id)

        if location_id:
            query = query.where(InventoryLevel.location_id == location_id)
            count_query = count_query.where(InventoryLevel.location_id == location_id)

        if stock_status == "low":
            query = query.where(InventoryLevel.on_hand <= InventoryLevel.reorder_point)
            count_query = count_query.where(InventoryLevel.on_hand <= InventoryLevel.reorder_point)
        elif stock_status == "out_of_stock":
            query = query.where(InventoryLevel.on_hand == 0)
            count_query = count_query.where(InventoryLevel.on_hand == 0)
        elif stock_status == "in_stock":
            query = query.where(InventoryLevel.on_hand > 0)
            count_query = count_query.where(InventoryLevel.on_hand > 0)

        if search:
            clean = search.strip()
            # Escape LIKE wildcards to prevent wildcard injection attacks
            escaped = clean.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
            pattern = f"%{escaped}%"
            search_cond = or_(
                SKU.sku_code.ilike(pattern, escape="\\"),
                Product.name.ilike(pattern, escape="\\"),
                Location.name.ilike(pattern, escape="\\"),
            )
            query = query.where(search_cond)
            count_query = count_query.where(search_cond)

        total_res = await db.execute(count_query)
        total = total_res.scalar_one()

        query = query.order_by(InventoryLevel.created_at.desc())
        query = query.offset((page - 1) * limit).limit(limit)
        results = await db.execute(query)
        items = results.scalars().all()

        responses = [InventoryService._to_level_response(item) for item in items]
        total_pages = math.ceil(total / limit) if total > 0 else 1

        meta = PaginationMeta(
            total=total,
            page=page,
            limit=limit,
            total_pages=total_pages,
        )
        return responses, meta

    @staticmethod
    async def list_transactions(
        db: AsyncSession,
        tenant_id: UUID,
        page: int = 1,
        limit: int = 50,
        sku_id: UUID | None = None,
        location_id: UUID | None = None,
        transaction_type: str | None = None,
    ) -> tuple[list[InventoryTransactionResponse], PaginationMeta]:
        """Retrieve paginated ledger audit trail records."""
        page = max(1, page)
        limit = max(1, min(limit, 100))

        query = (
            select(InventoryTransaction)
            .where(InventoryTransaction.tenant_id == tenant_id)
            .options(
                selectinload(InventoryTransaction.sku).selectinload(SKU.product),
                selectinload(InventoryTransaction.location),
                selectinload(InventoryTransaction.user),
            )
        )
        count_query = select(func.count(InventoryTransaction.id)).where(
            InventoryTransaction.tenant_id == tenant_id
        )

        if sku_id:
            query = query.where(InventoryTransaction.sku_id == sku_id)
            count_query = count_query.where(InventoryTransaction.sku_id == sku_id)

        if location_id:
            query = query.where(InventoryTransaction.location_id == location_id)
            count_query = count_query.where(InventoryTransaction.location_id == location_id)

        if transaction_type:
            query = query.where(InventoryTransaction.transaction_type == transaction_type)
            count_query = count_query.where(
                InventoryTransaction.transaction_type == transaction_type
            )

        total_res = await db.execute(count_query)
        total = total_res.scalar_one()

        query = query.order_by(InventoryTransaction.created_at.desc())
        query = query.offset((page - 1) * limit).limit(limit)
        results = await db.execute(query)
        items = results.scalars().all()

        responses = [InventoryService._to_tx_response(tx) for tx in items]
        total_pages = math.ceil(total / limit) if total > 0 else 1

        meta = PaginationMeta(
            total=total,
            page=page,
            limit=limit,
            total_pages=total_pages,
        )
        return responses, meta
