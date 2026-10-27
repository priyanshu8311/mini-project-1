from datetime import date
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.src.api.dependencies import get_current_user, require_roles
from backend.src.core.database import get_db_session
from backend.src.domain.forecasting.schemas import (
    ForecastJobResponse,
    ForecastRunRequest,
    PaginatedDemandForecastsResponse,
    ReorderRecommendation,
    SalesHistoryRecordCreate,
    SalesHistoryRecordResponse,
)
from backend.src.domain.forecasting.service import ForecastingService
from backend.src.domain.users.models import User, UserRole

forecasting_router = APIRouter(prefix="/forecasts", tags=["Demand Forecasting"])


@forecasting_router.get(
    "",
    response_model=PaginatedDemandForecastsResponse,
    summary="Get generated ML demand predictions",
)
async def get_forecasts(
    sku_id: UUID | None = Query(default=None, description="Filter predictions by SKU UUID"),
    start_date: date | None = Query(default=None, description="Start date of forecast window"),
    end_date: date | None = Query(default=None, description="End date of forecast window"),
    page: int = Query(default=1, ge=1, description="Page number"),
    limit: int = Query(default=50, ge=1, le=100, description="Page size"),
    db: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> PaginatedDemandForecastsResponse:
    """Retrieve generated time-series demand predictions with optional date and SKU filters."""
    data, meta = await ForecastingService.get_forecasts(
        db=db,
        tenant_id=current_user.tenant_id,
        sku_id=sku_id,
        start_date=start_date,
        end_date=end_date,
        page=page,
        limit=limit,
    )
    return PaginatedDemandForecastsResponse(data=data, meta=meta)


@forecasting_router.post(
    "/jobs",
    response_model=ForecastJobResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Trigger an ML forecast generation batch job",
)
async def trigger_forecast_job(
    payload: ForecastRunRequest = ForecastRunRequest(),
    db: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(
        require_roles([
            UserRole.ADMIN.value,
            UserRole.ANALYST.value,
            UserRole.INVENTORY_MANAGER.value,
        ])
    ),
) -> ForecastJobResponse:
    """Trigger time-series ML forecast calculation for tenant catalog SKUs."""
    return await ForecastingService.generate_forecasts(
        db=db,
        tenant_id=current_user.tenant_id,
        payload=payload,
    )


@forecasting_router.get(
    "/recommendations",
    response_model=list[ReorderRecommendation],
    summary="Get ML-driven replenishment and reorder recommendations",
)
async def get_reorder_recommendations(
    db: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> list[ReorderRecommendation]:
    """Retrieve reorder recommendations synthesized from demand velocity, lead times, and current stock."""
    return await ForecastingService.get_reorder_recommendations(
        db=db,
        tenant_id=current_user.tenant_id,
    )


@forecasting_router.post(
    "/sales",
    response_model=list[SalesHistoryRecordResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Ingest sales history records for ML model training",
)
async def record_sales_history(
    records: list[SalesHistoryRecordCreate],
    db: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(
        require_roles([
            UserRole.ADMIN.value,
            UserRole.INVENTORY_MANAGER.value,
            UserRole.ANALYST.value,
        ])
    ),
) -> list[SalesHistoryRecordResponse]:
    """Ingest daily sales records into the time-series training repository."""
    return await ForecastingService.record_sales(
        db=db,
        tenant_id=current_user.tenant_id,
        records=records,
    )
