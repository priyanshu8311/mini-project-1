import asyncio
import logging
from uuid import UUID

from sqlalchemy import select

from backend.src.core.database import AsyncSessionLocal
from backend.src.domain.forecasting.schemas import ForecastRunRequest
from backend.src.domain.forecasting.service import ForecastingService
from backend.src.domain.users.models import Tenant

logger = logging.getLogger(__name__)


async def run_batch_forecast_for_tenant(
    tenant_id: UUID,
    horizon_days: int = 30,
) -> dict:
    """Execute demand forecasting for all SKUs in a specific tenant."""
    logger.info("Starting background batch forecast for tenant %s", tenant_id)
    async with AsyncSessionLocal() as session:
        try:
            result = await ForecastingService.generate_forecasts(
                db=session,
                tenant_id=tenant_id,
                payload=ForecastRunRequest(horizon_days=horizon_days),
            )
            logger.info(
                "Completed forecast for tenant %s: %s points generated",
                tenant_id,
                result.generated_forecasts_count,
            )
            return {
                "tenant_id": str(tenant_id),
                "job_id": result.job_id,
                "status": result.status,
                "generated_forecasts_count": result.generated_forecasts_count,
            }
        except Exception as e:
            logger.error("Forecast batch failed for tenant %s: %s", tenant_id, e)
            return {
                "tenant_id": str(tenant_id),
                "status": "FAILED",
                "error": str(e),
            }


async def run_batch_forecast_all_tenants(horizon_days: int = 30) -> list[dict]:
    """Execute scheduled batch forecasting across all active tenants."""
    logger.info("Executing global nightly batch forecast run across all tenants")
    async with AsyncSessionLocal() as session:
        res = await session.execute(select(Tenant.id))
        tenant_ids = res.scalars().all()

    results = []
    for tid in tenant_ids:
        res = await run_batch_forecast_for_tenant(tid, horizon_days=horizon_days)
        results.append(res)
    return results


def run_forecast_job_sync(tenant_id: UUID, horizon_days: int = 30) -> dict:
    """Synchronous entry point for task runners and cron jobs."""
    return asyncio.run(run_batch_forecast_for_tenant(tenant_id, horizon_days=horizon_days))
