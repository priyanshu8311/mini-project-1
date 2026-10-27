from datetime import date, timedelta
from decimal import Decimal

import pytest
from backend.src.domain.inventory.models import Location, LocationType
from backend.src.domain.inventory.schemas import (
    LocationCreate,
    SKUCreate,
)
from backend.src.domain.inventory.service import CatalogService, InventoryService
from backend.src.domain.purchasing.models import OrderStatus
from backend.src.domain.purchasing.schemas import (
    POItemCreate,
    POReceiveItem,
    POReceiveRequest,
    PurchaseOrderCreate,
)
from backend.src.domain.purchasing.service import PurchasingService
from backend.src.domain.users.models import Tenant, User
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession


@pytest.fixture
async def sample_catalog(
    db_session: AsyncSession,
    test_tenant: Tenant,
) -> tuple[Location, list]:
    """Create a sample warehouse location and SKUs."""
    loc = await CatalogService.create_location(
        db=db_session,
        tenant_id=test_tenant.id,
        payload=LocationCreate(
            name="Main DC",
            type=LocationType.WAREHOUSE,
            address="100 Distribution Way",
        ),
    )

    sku1 = await CatalogService.create_sku(
        db=db_session,
        tenant_id=test_tenant.id,
        payload=SKUCreate(
            sku_code="SKU-WIDGET-01",
            product_name="Standard Widget",
            unit_cost=Decimal("15.50"),
            sales_price=Decimal("29.99"),
            lead_time_days=5,
        ),
    )

    sku2 = await CatalogService.create_sku(
        db=db_session,
        tenant_id=test_tenant.id,
        payload=SKUCreate(
            sku_code="SKU-GADGET-02",
            product_name="Super Gadget",
            unit_cost=Decimal("45.00"),
            sales_price=Decimal("89.99"),
            lead_time_days=10,
        ),
    )

    await db_session.commit()
    return loc, [sku1, sku2]


@pytest.mark.asyncio
async def test_create_and_receive_purchase_order(
    db_session: AsyncSession,
    test_tenant: Tenant,
    test_admin_user: User,
    sample_catalog: tuple[Location, list],
) -> None:
    """Test full purchase order lifecycle: Draft -> Receive -> Ledger Restock."""
    loc, skus = sample_catalog
    sku1, sku2 = skus

    # 1. Create Purchase Order
    po_res = await PurchasingService.create_purchase_order(
        db=db_session,
        tenant_id=test_tenant.id,
        payload=PurchaseOrderCreate(
            expected_date=date.today() + timedelta(days=7),
            items=[
                POItemCreate(sku_id=sku1.id, quantity_ordered=50, unit_cost=Decimal("15.50")),
                POItemCreate(sku_id=sku2.id, quantity_ordered=20, unit_cost=Decimal("45.00")),
            ],
        ),
    )
    assert po_res.status == OrderStatus.DRAFT.value
    assert len(po_res.items) == 2

    # 2. Receive Partial Shipment (all of sku1, half of sku2)
    po_item1 = po_res.items[0]
    po_item2 = po_res.items[1]

    receive_payload = POReceiveRequest(
        location_id=loc.id,
        items=[
            POReceiveItem(po_item_id=po_item1.id, quantity_to_receive=50),
            POReceiveItem(po_item_id=po_item2.id, quantity_to_receive=10),
        ],
    )
    updated_po = await PurchasingService.receive_purchase_order(
        db=db_session,
        tenant_id=test_tenant.id,
        user_id=test_admin_user.id,
        po_id=po_res.id,
        payload=receive_payload,
    )
    assert updated_po.status == OrderStatus.PARTIALLY_RECEIVED.value

    # 3. Verify Inventory Ledger and On-Hand Levels
    levels, _ = await InventoryService.list_inventory_levels(
        db=db_session,
        tenant_id=test_tenant.id,
        location_id=loc.id,
    )
    levels_map = {lvl.sku_id: lvl for lvl in levels}
    assert levels_map[sku1.id].on_hand == 50
    assert levels_map[sku2.id].on_hand == 10

    # 4. Receive remaining items for sku2 -> Completes PO
    complete_payload = POReceiveRequest(
        location_id=loc.id,
        items=[
            POReceiveItem(po_item_id=po_item2.id, quantity_to_receive=10),
        ],
    )
    final_po = await PurchasingService.receive_purchase_order(
        db=db_session,
        tenant_id=test_tenant.id,
        user_id=test_admin_user.id,
        po_id=po_res.id,
        payload=complete_payload,
    )
    assert final_po.status == OrderStatus.COMPLETED.value


@pytest.mark.asyncio
async def test_purchasing_api_endpoints(
    async_client: AsyncClient,
    admin_token: str,
    viewer_token: str,
    sample_catalog: tuple[Location, list],
) -> None:
    """Test purchasing API routes with RBAC enforcement."""
    loc, skus = sample_catalog
    sku1, _ = skus

    # 1. Create PO via API as Admin
    create_resp = await async_client.post(
        "/api/v1/purchasing/orders",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={
            "expected_date": str(date.today() + timedelta(days=5)),
            "items": [
                {"sku_id": str(sku1.id), "quantity_ordered": 100, "unit_cost": "15.00"}
            ],
        },
    )
    assert create_resp.status_code == 201
    po_data = create_resp.json()
    po_id = po_data["id"]
    po_item_id = po_data["items"][0]["id"]

    # 2. Viewer cannot create PO (RBAC check)
    forbidden_resp = await async_client.post(
        "/api/v1/purchasing/orders",
        headers={"Authorization": f"Bearer {viewer_token}"},
        json={"items": [{"sku_id": str(sku1.id), "quantity_ordered": 10}]},
    )
    assert forbidden_resp.status_code == 403

    # 3. List POs
    list_resp = await async_client.get(
        "/api/v1/purchasing/orders",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert list_resp.status_code == 200
    assert list_resp.json()["meta"]["total"] >= 1

    # 4. Receive shipment via API
    receive_resp = await async_client.post(
        f"/api/v1/purchasing/orders/{po_id}/receive",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={
            "location_id": str(loc.id),
            "items": [{"po_item_id": po_item_id, "quantity_to_receive": 100}],
        },
    )
    assert receive_resp.status_code == 200
    assert receive_resp.json()["status"] == "Completed"

    # 5. Fetch replenishment suggestions
    sugg_resp = await async_client.get(
        "/api/v1/purchasing/suggestions",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert sugg_resp.status_code == 200
    assert isinstance(sugg_resp.json(), list)


@pytest.mark.asyncio
async def test_forecasting_lifecycle(
    async_client: AsyncClient,
    admin_token: str,
    test_tenant: Tenant,
    test_admin_user: User,
    sample_catalog: tuple[Location, list],
    db_session: AsyncSession,
) -> None:
    """Test sales ingestion, ML batch forecasting, and recommendation generation."""
    loc, skus = sample_catalog
    sku1, _ = skus

    # 1. Ingest historical sales records
    sales_payload = [
        {
            "sku_id": str(sku1.id),
            "location_id": str(loc.id),
            "sales_date": str(date.today() - timedelta(days=i)),
            "quantity_sold": 10 + (i % 5),
            "channel": "Shopify",
        }
        for i in range(1, 15)
    ]
    sales_resp = await async_client.post(
        "/api/v1/forecasts/sales",
        headers={"Authorization": f"Bearer {admin_token}"},
        json=sales_payload,
    )
    assert sales_resp.status_code == 201
    assert len(sales_resp.json()) == 14

    # 2. Trigger Batch Forecast Run
    job_resp = await async_client.post(
        "/api/v1/forecasts/jobs",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"horizon_days": 14},
    )
    assert job_resp.status_code == 202
    job_data = job_resp.json()
    assert job_data["status"] == "COMPLETED"
    assert job_data["generated_forecasts_count"] > 0

    # 3. Query generated forecasts
    get_fc_resp = await async_client.get(
        f"/api/v1/forecasts?sku_id={sku1.id}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert get_fc_resp.status_code == 200
    fc_data = get_fc_resp.json()
    assert fc_data["meta"]["total"] >= 14
    first_pt = fc_data["data"][0]
    assert first_pt["predicted_demand"] >= 0
    assert first_pt["confidence_upper"] >= first_pt["predicted_demand"]

    # 4. Query Reorder Recommendations
    rec_resp = await async_client.get(
        "/api/v1/forecasts/recommendations",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert rec_resp.status_code == 200
    recs = rec_resp.json()
    assert len(recs) >= 2


@pytest.mark.asyncio
async def test_sku_inline_product_creation(
    db_session: AsyncSession,
    test_tenant: Tenant,
) -> None:
    """Refactored test verifying inline product creation with SKU (formerly in verify_sku.py)."""
    payload = SKUCreate(
        sku_code="TEST-BULB-001",
        product_name="LED Bulb Test",
        category_id=None,
        unit_cost=Decimal("9.98"),
        sales_price=Decimal("11.98"),
        lead_time_days=5,
    )
    sku = await CatalogService.create_sku(db_session, test_tenant.id, payload)
    await db_session.commit()
    assert sku.sku_code == "TEST-BULB-001"
    assert sku.product_id is not None
    assert sku.product_name == "LED Bulb Test"
