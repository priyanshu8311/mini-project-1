from decimal import Decimal

import pytest
from backend.src.domain.inventory.models import LocationType
from backend.src.domain.inventory.schemas import CategoryCreate, SKUCreate
from backend.src.domain.inventory.service import CatalogService
from backend.src.domain.users.models import Tenant
from backend.src.domain.users.service import UserService
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession


@pytest.mark.asyncio
async def test_create_and_list_categories(
    async_client: AsyncClient,
    admin_token: str,
    test_tenant: Tenant,
) -> None:
    """Verify category creation and hierarchical parent-child retrieval."""
    # 1. Create root category
    root_resp = await async_client.post(
        "/api/v1/products/categories",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"name": "Electronics"},
    )
    assert root_resp.status_code == 201
    root_data = root_resp.json()
    assert root_data["name"] == "Electronics"
    root_id = root_data["id"]

    # 2. Create subcategory
    sub_resp = await async_client.post(
        "/api/v1/products/categories",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"name": "Smartphones", "parent_id": root_id},
    )
    assert sub_resp.status_code == 201
    sub_data = sub_resp.json()
    assert sub_data["parent_id"] == root_id

    # 3. List categories
    list_resp = await async_client.get(
        "/api/v1/products/categories",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert list_resp.status_code == 200
    cats = list_resp.json()
    assert len(cats) >= 2


@pytest.mark.asyncio
async def test_create_and_list_locations(
    async_client: AsyncClient,
    admin_token: str,
) -> None:
    """Verify warehouse and retail store creation."""
    wh_resp = await async_client.post(
        "/api/v1/locations",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={
            "name": "Central Distribution Center",
            "type": LocationType.WAREHOUSE.value,
            "address": "100 Logistics Blvd, Dallas, TX",
        },
    )
    assert wh_resp.status_code == 201
    wh_data = wh_resp.json()
    assert wh_data["name"] == "Central Distribution Center"
    assert wh_data["type"] == "Warehouse"

    # List locations
    list_resp = await async_client.get(
        "/api/v1/locations",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert list_resp.status_code == 200
    locations = list_resp.json()
    assert len(locations) >= 1


@pytest.mark.asyncio
async def test_create_sku_with_inline_product(
    async_client: AsyncClient,
    admin_token: str,
    db_session: AsyncSession,
    test_tenant: Tenant,
) -> None:
    """Verify creating a SKU with inline product name and category."""
    category = await CatalogService.create_category(
        db_session,
        test_tenant.id,
        CategoryCreate(name="Hardware"),
    )
    await db_session.commit()

    resp = await async_client.post(
        "/api/v1/products/skus",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={
            "sku_code": "HDW-BOLT-001",
            "product_name": "Titanium Bolt M8",
            "category_id": str(category.id),
            "unit_cost": 2.50,
            "sales_price": 5.99,
            "lead_time_days": 14,
        },
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["sku_code"] == "HDW-BOLT-001"
    assert data["product_name"] == "Titanium Bolt M8"
    assert data["category_name"] == "Hardware"
    assert float(data["unit_cost"]) == 2.50
    assert float(data["sales_price"]) == 5.99


@pytest.mark.asyncio
async def test_create_sku_duplicate_code_conflict(
    async_client: AsyncClient,
    admin_token: str,
    db_session: AsyncSession,
    test_tenant: Tenant,
) -> None:
    """Verify duplicate SKU code in same tenant raises 409 Conflict."""
    category = await CatalogService.create_category(
        db_session,
        test_tenant.id,
        CategoryCreate(name="Tools"),
    )
    await db_session.commit()

    sku_payload = {
        "sku_code": "TOOL-WRENCH-01",
        "product_name": "Adjustable Wrench",
        "category_id": str(category.id),
        "unit_cost": 10.00,
        "sales_price": 19.99,
    }

    resp1 = await async_client.post(
        "/api/v1/products/skus",
        headers={"Authorization": f"Bearer {admin_token}"},
        json=sku_payload,
    )
    assert resp1.status_code == 201

    # Duplicate SKU code
    resp2 = await async_client.post(
        "/api/v1/products/skus",
        headers={"Authorization": f"Bearer {admin_token}"},
        json=sku_payload,
    )
    assert resp2.status_code == 409
    error_data = resp2.json()
    assert error_data["error"]["code"] == "CONFLICT"


@pytest.mark.asyncio
async def test_list_skus_pagination_and_search(
    async_client: AsyncClient,
    admin_token: str,
    db_session: AsyncSession,
    test_tenant: Tenant,
) -> None:
    """Verify pagination envelope and search filtering by SKU code or name."""
    cat = await CatalogService.create_category(
        db_session,
        test_tenant.id,
        CategoryCreate(name="Office Supplies"),
    )
    await db_session.commit()

    # Seed 3 SKUs
    for i in range(1, 4):
        await CatalogService.create_sku(
            db_session,
            test_tenant.id,
            SKUCreate(
                sku_code=f"OFF-PEN-00{i}",
                product_name=f"Gel Pen Pack {i}",
                category_id=cat.id,
                unit_cost=Decimal("1.20"),
                sales_price=Decimal("2.99"),
            ),
        )
    await db_session.commit()

    # Paginated retrieval
    resp = await async_client.get(
        "/api/v1/products/skus?page=1&limit=2",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 200
    res_json = resp.json()
    assert "data" in res_json
    assert "meta" in res_json
    assert len(res_json["data"]) == 2
    assert res_json["meta"]["total"] >= 3
    assert res_json["meta"]["page"] == 1
    assert res_json["meta"]["limit"] == 2

    # Search filter
    search_resp = await async_client.get(
        "/api/v1/products/skus?search=002",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert search_resp.status_code == 200
    search_json = search_resp.json()
    assert len(search_json["data"]) == 1
    assert search_json["data"][0]["sku_code"] == "OFF-PEN-002"


@pytest.mark.asyncio
async def test_sku_update_success(
    async_client: AsyncClient,
    admin_token: str,
    db_session: AsyncSession,
    test_tenant: Tenant,
) -> None:
    """Verify updating unit cost, sales price, and lead time on a SKU."""
    cat = await CatalogService.create_category(
        db_session,
        test_tenant.id,
        CategoryCreate(name="Apparel"),
    )
    sku_item = await CatalogService.create_sku(
        db_session,
        test_tenant.id,
        SKUCreate(
            sku_code=f"APP-TSHIRT-{test_tenant.id.hex[:4]}",
            product_name="Cotton T-Shirt",
            category_id=cat.id,
            unit_cost=Decimal("5.00"),
            sales_price=Decimal("15.00"),
            lead_time_days=5,
        ),
    )
    await db_session.commit()

    update_resp = await async_client.put(
        f"/api/v1/products/skus/{sku_item.id}",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"sales_price": 18.50, "lead_time_days": 9},
    )
    assert update_resp.status_code == 200
    updated_data = update_resp.json()
    assert float(updated_data["sales_price"]) == 18.50
    assert updated_data["lead_time_days"] == 9


@pytest.mark.asyncio
async def test_tenant_isolation_skus(
    async_client: AsyncClient,
    admin_token: str,
    db_session: AsyncSession,
) -> None:
    """Verify Tenant A cannot access or see Tenant B's SKUs."""
    # Tenant B
    tenant_b = await UserService.create_tenant(db_session, name="Tenant B Corp")
    cat_b = await CatalogService.create_category(
        db_session,
        tenant_b.id,
        CategoryCreate(name="Tenant B Category"),
    )
    sku_b = await CatalogService.create_sku(
        db_session,
        tenant_b.id,
        SKUCreate(
            sku_code="SECRET-SKU-99",
            product_name="Confidential Item",
            category_id=cat_b.id,
            unit_cost=Decimal("100.00"),
            sales_price=Decimal("250.00"),
        ),
    )
    await db_session.commit()

    # User in Tenant A queries single SKU from Tenant B
    get_resp = await async_client.get(
        f"/api/v1/products/skus/{sku_b.id}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert get_resp.status_code == 404  # Not found for Tenant A

    # User in Tenant A queries list
    list_resp = await async_client.get(
        "/api/v1/products/skus?search=SECRET-SKU-99",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert list_resp.status_code == 200
    assert len(list_resp.json()["data"]) == 0


@pytest.mark.asyncio
async def test_rbac_sku_write_permissions(
    async_client: AsyncClient,
    viewer_token: str,
    db_session: AsyncSession,
    test_tenant: Tenant,
) -> None:
    """Verify Viewer role receives 403 Forbidden on SKU creation."""
    cat = await CatalogService.create_category(
        db_session,
        test_tenant.id,
        CategoryCreate(name="Raw Materials"),
    )
    await db_session.commit()

    resp = await async_client.post(
        "/api/v1/products/skus",
        headers={"Authorization": f"Bearer {viewer_token}"},
        json={
            "sku_code": "RAW-STEEL-01",
            "product_name": "Steel Sheet 2mm",
            "category_id": str(cat.id),
        },
    )
    assert resp.status_code == 403
    error_data = resp.json()
    assert error_data["error"]["code"] == "FORBIDDEN"
