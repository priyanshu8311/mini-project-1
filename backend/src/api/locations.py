from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.src.api.dependencies import get_current_tenant_id, require_roles
from backend.src.core.database import get_db_session
from backend.src.domain.inventory.schemas import LocationCreate, LocationResponse
from backend.src.domain.inventory.service import CatalogService
from backend.src.domain.users.models import UserRole

locations_router = APIRouter(prefix="/locations", tags=["Locations"])

LOCATION_WRITE_ROLES = [UserRole.ADMIN.value, UserRole.INVENTORY_MANAGER.value]


@locations_router.get(
    "",
    response_model=list[LocationResponse],
    status_code=status.HTTP_200_OK,
    summary="List all physical locations",
)
async def list_locations(
    tenant_id: UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db_session),
) -> list[LocationResponse]:
    """Retrieve all physical locations (warehouses, stores) for the tenant."""
    locations = await CatalogService.list_locations(db=db, tenant_id=tenant_id)
    return [LocationResponse.model_validate(loc) for loc in locations]


@locations_router.post(
    "",
    response_model=LocationResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_roles(LOCATION_WRITE_ROLES))],
    summary="Create a new physical location",
)
async def create_location(
    payload: LocationCreate,
    tenant_id: UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db_session),
) -> LocationResponse:
    """Create a new location under the tenant organization."""
    location = await CatalogService.create_location(
        db=db,
        tenant_id=tenant_id,
        payload=payload,
    )
    return LocationResponse.model_validate(location)


@locations_router.get(
    "/{id}",
    response_model=LocationResponse,
    status_code=status.HTTP_200_OK,
    summary="Get single location details",
)
async def get_location(
    id: UUID,
    tenant_id: UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db_session),
) -> LocationResponse:
    """Retrieve location details by primary key."""
    location = await CatalogService.get_location_by_id(
        db=db,
        tenant_id=tenant_id,
        location_id=id,
    )
    return LocationResponse.model_validate(location)
