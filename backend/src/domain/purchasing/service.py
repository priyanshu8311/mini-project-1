import math
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.src.core.errors import NotFoundException, ValidationException
from backend.src.domain.inventory.models import (
    SKU,
    InventoryLevel,
    Location,
    TransactionType,
)
from backend.src.domain.inventory.schemas import (
    InventoryTransactionCreate,
    PaginationMeta,
)
from backend.src.domain.inventory.service import InventoryService
from backend.src.domain.purchasing.models import OrderStatus, POItem, PurchaseOrder
from backend.src.domain.purchasing.schemas import (
    POItemResponse,
    POReceiveRequest,
    PurchaseOrderCreate,
    PurchaseOrderResponse,
    PurchaseOrderUpdate,
    PurchasingSuggestionItem,
    UrgencyLevel,
)


class PurchasingService:
    """Business logic for vendor purchase orders, receipt restocking, and replenishment suggestions."""

    @staticmethod
    def _to_po_response(po: PurchaseOrder) -> PurchaseOrderResponse:
        """Convert a PurchaseOrder ORM model to a typed response schema."""
        item_responses: list[POItemResponse] = []
        for item in po.items:
            sku_code = item.sku.sku_code if item.sku else None
            prod_name = (
                item.sku.product.name
                if item.sku and getattr(item.sku, "product", None)
                else None
            )
            item_responses.append(
                POItemResponse(
                    id=item.id,
                    po_id=item.po_id,
                    sku_id=item.sku_id,
                    quantity_ordered=item.quantity_ordered,
                    quantity_received=item.quantity_received,
                    unit_cost=item.unit_cost,
                    created_at=item.created_at,
                    sku_code=sku_code,
                    product_name=prod_name,
                )
            )

        return PurchaseOrderResponse(
            id=po.id,
            tenant_id=po.tenant_id,
            supplier_id=po.supplier_id,
            status=po.status,
            expected_date=po.expected_date,
            created_at=po.created_at,
            items=item_responses,
        )

    @staticmethod
    async def create_purchase_order(
        db: AsyncSession,
        tenant_id: UUID,
        payload: PurchaseOrderCreate,
    ) -> PurchaseOrderResponse:
        """Create a new purchase order with validated line items."""
        # 1. Verify all requested SKUs exist and belong to this tenant
        sku_ids = [item.sku_id for item in payload.items]
        sku_res = await db.execute(
            select(SKU).where(
                SKU.tenant_id == tenant_id,
                SKU.id.in_(sku_ids),
            )
        )
        found_skus = {s.id: s for s in sku_res.scalars().all()}
        for sku_id in sku_ids:
            if sku_id not in found_skus:
                raise NotFoundException("SKU", sku_id)

        # 2. Instantiate Purchase Order
        po = PurchaseOrder(
            tenant_id=tenant_id,
            supplier_id=payload.supplier_id,
            status=OrderStatus.DRAFT.value,
            expected_date=payload.expected_date,
        )
        db.add(po)
        await db.flush()

        # 3. Add Line Items
        for item_data in payload.items:
            po_item = POItem(
                po_id=po.id,
                sku_id=item_data.sku_id,
                quantity_ordered=item_data.quantity_ordered,
                quantity_received=0,
                unit_cost=item_data.unit_cost,
            )
            db.add(po_item)

        await db.flush()
        await db.commit()

        # Reload with relationships
        return await PurchasingService.get_purchase_order(db, tenant_id, po.id)

    @staticmethod
    async def list_purchase_orders(
        db: AsyncSession,
        tenant_id: UUID,
        status: str | None = None,
        page: int = 1,
        limit: int = 50,
    ) -> tuple[list[PurchaseOrderResponse], PaginationMeta]:
        """List paginated purchase orders with optional status filtering."""
        query = (
            select(PurchaseOrder)
            .where(PurchaseOrder.tenant_id == tenant_id)
            .options(
                selectinload(PurchaseOrder.items)
                .selectinload(POItem.sku)
                .selectinload(SKU.product)
            )
        )

        if status:
            query = query.where(PurchaseOrder.status == status)

        # Count total
        count_q = (
            select(func.count(PurchaseOrder.id))
            .where(PurchaseOrder.tenant_id == tenant_id)
        )
        if status:
            count_q = count_q.where(PurchaseOrder.status == status)
        total_res = await db.execute(count_q)
        total = total_res.scalar_one()

        query = query.order_by(PurchaseOrder.created_at.desc())
        query = query.offset((page - 1) * limit).limit(limit)

        result = await db.execute(query)
        pos = result.scalars().all()

        responses = [PurchasingService._to_po_response(po) for po in pos]
        total_pages = math.ceil(total / limit) if total > 0 else 1
        meta = PaginationMeta(
            total=total,
            page=page,
            limit=limit,
            total_pages=total_pages,
        )
        return responses, meta

    @staticmethod
    async def get_purchase_order(
        db: AsyncSession,
        tenant_id: UUID,
        po_id: UUID,
    ) -> PurchaseOrderResponse:
        """Fetch a single purchase order by ID."""
        result = await db.execute(
            select(PurchaseOrder)
            .where(
                PurchaseOrder.id == po_id,
                PurchaseOrder.tenant_id == tenant_id,
            )
            .options(
                selectinload(PurchaseOrder.items)
                .selectinload(POItem.sku)
                .selectinload(SKU.product)
            )
        )
        po = result.scalar_one_or_none()
        if not po:
            raise NotFoundException("Purchase Order", po_id)

        return PurchasingService._to_po_response(po)

    @staticmethod
    async def update_purchase_order(
        db: AsyncSession,
        tenant_id: UUID,
        po_id: UUID,
        payload: PurchaseOrderUpdate,
    ) -> PurchaseOrderResponse:
        """Update mutable metadata on a purchase order."""
        result = await db.execute(
            select(PurchaseOrder)
            .where(
                PurchaseOrder.id == po_id,
                PurchaseOrder.tenant_id == tenant_id,
            )
            .options(
                selectinload(PurchaseOrder.items)
                .selectinload(POItem.sku)
                .selectinload(SKU.product)
            )
        )
        po = result.scalar_one_or_none()
        if not po:
            raise NotFoundException("Purchase Order", po_id)

        if payload.supplier_id is not None:
            po.supplier_id = payload.supplier_id
        if payload.expected_date is not None:
            po.expected_date = payload.expected_date
        if payload.status is not None:
            po.status = payload.status.value

        await db.flush()
        await db.commit()
        return PurchasingService._to_po_response(po)

    @staticmethod
    async def receive_purchase_order(
        db: AsyncSession,
        tenant_id: UUID,
        user_id: UUID,
        po_id: UUID,
        payload: POReceiveRequest,
    ) -> PurchaseOrderResponse:
        """Process incoming shipment: atomically adjust stock ledger and advance PO status."""
        # 1. Verify target location
        loc_res = await db.execute(
            select(Location).where(
                Location.id == payload.location_id,
                Location.tenant_id == tenant_id,
            )
        )
        if not loc_res.scalar_one_or_none():
            raise NotFoundException("Location", payload.location_id)

        # 2. Fetch purchase order
        result = await db.execute(
            select(PurchaseOrder)
            .where(
                PurchaseOrder.id == po_id,
                PurchaseOrder.tenant_id == tenant_id,
            )
            .options(
                selectinload(PurchaseOrder.items)
                .selectinload(POItem.sku)
                .selectinload(SKU.product)
            )
        )
        po = result.scalar_one_or_none()
        if not po:
            raise NotFoundException("Purchase Order", po_id)

        if po.status == OrderStatus.COMPLETED.value:
            raise ValidationException("Purchase order is already completely received and closed.")

        items_by_id: dict[UUID, POItem] = {item.id: item for item in po.items}

        # 3. Process each received line item
        for rec in payload.items:
            po_item = items_by_id.get(rec.po_item_id)
            if not po_item:
                raise NotFoundException("Purchase Order Item", rec.po_item_id)

            remaining_allowed = po_item.quantity_ordered - po_item.quantity_received
            if rec.quantity_to_receive > remaining_allowed:
                raise ValidationException(
                    f"Received quantity {rec.quantity_to_receive} exceeds outstanding balance of "
                    f"{remaining_allowed} for SKU item {po_item.id}."
                )

            # Update item received count
            po_item.quantity_received += rec.quantity_to_receive

            # Record stock receipt in the ledger (append-only ledger transaction)
            # which updates inventory_levels atomically with row locking.
            await InventoryService.record_transaction(
                db=db,
                tenant_id=tenant_id,
                user_id=user_id,
                payload=InventoryTransactionCreate(
                    transaction_type=TransactionType.RECEIVE,
                    sku_id=po_item.sku_id,
                    location_id=payload.location_id,
                    quantity_change=rec.quantity_to_receive,
                    reference_id=f"PO-{str(po.id)[:8].upper()}",
                    reason=f"Restock from Purchase Order {po.id}",
                ),
            )

        # 4. Check if all items are fully received
        all_completed = all(
            item.quantity_received >= item.quantity_ordered for item in po.items
        )
        if all_completed:
            po.status = OrderStatus.COMPLETED.value
        else:
            po.status = OrderStatus.PARTIALLY_RECEIVED.value

        await db.flush()
        await db.commit()

        return PurchasingService._to_po_response(po)

    @staticmethod
    async def get_replenishment_suggestions(
        db: AsyncSession,
        tenant_id: UUID,
    ) -> list[PurchasingSuggestionItem]:
        """Generate purchase recommendations based on safety stock thresholds and lead times."""
        # Query inventory levels with stock below or at reorder point
        levels_res = await db.execute(
            select(InventoryLevel)
            .where(
                InventoryLevel.tenant_id == tenant_id,
                InventoryLevel.on_hand <= InventoryLevel.reorder_point,
            )
            .options(
                selectinload(InventoryLevel.sku).selectinload(SKU.product),
                selectinload(InventoryLevel.location),
            )
            .order_by(InventoryLevel.on_hand.asc())
        )
        levels = levels_res.scalars().all()

        suggestions: list[PurchasingSuggestionItem] = []
        for lvl in levels:
            sku = lvl.sku
            if not sku:
                continue

            # Determine suggested order quantity
            if lvl.reorder_quantity > 0:
                suggested_qty = lvl.reorder_quantity
            else:
                # Target safety cushion: 2x reorder point minus on_hand
                suggested_qty = max(10, (lvl.reorder_point * 2) - lvl.on_hand)

            # Determine urgency
            if lvl.on_hand <= 0:
                urgency = UrgencyLevel.HIGH
            elif lvl.on_hand <= lvl.reorder_point // 2:
                urgency = UrgencyLevel.HIGH
            else:
                urgency = UrgencyLevel.MEDIUM

            suggestions.append(
                PurchasingSuggestionItem(
                    sku_id=sku.id,
                    sku_code=sku.sku_code,
                    product_name=sku.product.name if sku.product else None,
                    location_id=lvl.location_id,
                    location_name=lvl.location.name if lvl.location else None,
                    current_on_hand=lvl.on_hand,
                    reorder_point=lvl.reorder_point,
                    lead_time_days=sku.lead_time_days,
                    suggested_reorder_quantity=suggested_qty,
                    unit_cost=sku.unit_cost,
                    supplier_id=sku.supplier_id,
                    urgency=urgency,
                )
            )

        return suggestions
