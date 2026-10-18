import math
from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.src.core.errors import ConflictException, NotFoundException, ValidationException
from backend.src.domain.inventory.models import SKU, Category, Location, Product
from backend.src.domain.inventory.schemas import (
    CategoryCreate,
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
        elif payload.product_name and payload.category_id:
            product = await CatalogService.create_product(
                db,
                tenant_id,
                ProductCreate(
                    name=payload.product_name,
                    category_id=payload.category_id,
                ),
            )
        else:
            raise ValidationException(
                "Either 'product_id' or both 'product_name' and 'category_id' must be provided."
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
            search_pattern = f"%{search.strip().lower()}%"
            query = query.where(
                or_(
                    func.lower(SKU.sku_code).like(search_pattern),
                    func.lower(Product.name).like(search_pattern),
                )
            )

        # Total count query
        count_query = (
            select(func.count(SKU.id))
            .join(Product, SKU.product_id == Product.id)
            .where(SKU.tenant_id == tenant_id)
        )
        if category_id:
            count_query = count_query.where(Product.category_id == category_id)
        if search:
            search_pattern = f"%{search.strip().lower()}%"
            count_query = count_query.where(
                or_(
                    func.lower(SKU.sku_code).like(search_pattern),
                    func.lower(Product.name).like(search_pattern),
                )
            )

        total_res = await db.execute(count_query)
        total = total_res.scalar_one()

        # Sorting
        sort_column = getattr(SKU, sort_by, SKU.created_at)
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
