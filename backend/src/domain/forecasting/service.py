import math
import uuid
from collections import defaultdict
from datetime import UTC, date, datetime, timedelta
from uuid import UUID

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.src.core.database import utcnow
from backend.src.domain.forecasting.models import DemandForecast, SalesHistory
from backend.src.domain.forecasting.schemas import (
    DemandForecastResponse,
    ForecastJobResponse,
    ForecastRunRequest,
    PaginationMeta,
    ReorderRecommendation,
    SalesHistoryRecordCreate,
    SalesHistoryRecordResponse,
)
from backend.src.domain.inventory.models import (
    SKU,
    InventoryLevel,
    InventoryTransaction,
    TransactionType,
)
from backend.src.ml.forecaster import DemandForecaster


class ForecastingService:
    """Service handling sales history ingestion, ML demand forecasting, and replenishment optimization."""

    @staticmethod
    def _to_forecast_response(df: DemandForecast) -> DemandForecastResponse:
        sku_code = df.sku.sku_code if df.sku else None
        prod_name = (
            df.sku.product.name
            if df.sku and getattr(df.sku, "product", None)
            else None
        )
        return DemandForecastResponse(
            id=df.id,
            tenant_id=df.tenant_id,
            sku_id=df.sku_id,
            forecast_date=df.forecast_date,
            predicted_demand=df.predicted_demand,
            confidence_lower=df.confidence_lower,
            confidence_upper=df.confidence_upper,
            generated_at=df.generated_at,
            sku_code=sku_code,
            product_name=prod_name,
        )

    @staticmethod
    async def get_forecasts(
        db: AsyncSession,
        tenant_id: UUID,
        sku_id: UUID | None = None,
        start_date: date | None = None,
        end_date: date | None = None,
        page: int = 1,
        limit: int = 50,
    ) -> tuple[list[DemandForecastResponse], PaginationMeta]:
        """Fetch generated demand forecasts with SKU filtering and date range constraints."""
        query = (
            select(DemandForecast)
            .where(DemandForecast.tenant_id == tenant_id)
            .options(
                selectinload(DemandForecast.sku).selectinload(SKU.product)
            )
        )

        if sku_id:
            query = query.where(DemandForecast.sku_id == sku_id)
        if start_date:
            query = query.where(DemandForecast.forecast_date >= start_date)
        if end_date:
            query = query.where(DemandForecast.forecast_date <= end_date)

        # Count total
        count_q = (
            select(func.count(DemandForecast.id))
            .where(DemandForecast.tenant_id == tenant_id)
        )
        if sku_id:
            count_q = count_q.where(DemandForecast.sku_id == sku_id)
        if start_date:
            count_q = count_q.where(DemandForecast.forecast_date >= start_date)
        if end_date:
            count_q = count_q.where(DemandForecast.forecast_date <= end_date)

        total_res = await db.execute(count_q)
        total = total_res.scalar_one()

        query = query.order_by(
            DemandForecast.forecast_date.asc(),
            DemandForecast.sku_id.asc(),
        )
        query = query.offset((page - 1) * limit).limit(limit)

        results = await db.execute(query)
        items = results.scalars().all()

        responses = [ForecastingService._to_forecast_response(item) for item in items]
        total_pages = math.ceil(total / limit) if total > 0 else 1
        meta = PaginationMeta(
            total=total,
            page=page,
            limit=limit,
            total_pages=total_pages,
        )
        return responses, meta

    @staticmethod
    async def record_sales(
        db: AsyncSession,
        tenant_id: UUID,
        records: list[SalesHistoryRecordCreate],
    ) -> list[SalesHistoryRecordResponse]:
        """Record sales history records for model training."""
        responses: list[SalesHistoryRecordResponse] = []
        for rec in records:
            history = SalesHistory(
                tenant_id=tenant_id,
                sku_id=rec.sku_id,
                location_id=rec.location_id,
                sales_date=rec.sales_date,
                quantity_sold=rec.quantity_sold,
                channel=rec.channel,
            )
            db.add(history)
            await db.flush()
            responses.append(
                SalesHistoryRecordResponse(
                    id=history.id,
                    tenant_id=history.tenant_id,
                    sku_id=history.sku_id,
                    location_id=history.location_id,
                    sales_date=history.sales_date,
                    quantity_sold=history.quantity_sold,
                    channel=history.channel,
                    created_at=history.created_at,
                )
            )

        await db.commit()
        return responses

    @staticmethod
    async def generate_forecasts(
        db: AsyncSession,
        tenant_id: UUID,
        payload: ForecastRunRequest,
    ) -> ForecastJobResponse:
        """Run ML demand forecasting models across SKUs and update forecast table."""
        # 1. Fetch SKUs
        sku_q = select(SKU).where(SKU.tenant_id == tenant_id)
        if payload.sku_ids:
            sku_q = sku_q.where(SKU.id.in_(payload.sku_ids))
        sku_res = await db.execute(sku_q)
        skus = sku_res.scalars().all()

        if not skus:
            return ForecastJobResponse(
                job_id=str(uuid.uuid4()),
                status="COMPLETED",
                total_skus_processed=0,
                generated_forecasts_count=0,
                message="No matching SKUs found to forecast.",
                mape=None,
            )

        today = datetime.now(UTC).date()
        job_id = str(uuid.uuid4())
        total_forecasts = 0
        total_mape = 0.0
        mape_count = 0

        for sku in skus:
            # 2. Pull sales history for this SKU
            sales_res = await db.execute(
                select(SalesHistory).where(
                    SalesHistory.tenant_id == tenant_id,
                    SalesHistory.sku_id == sku.id,
                )
            )
            sales = sales_res.scalars().all()
            daily_sales: dict[date, int] = defaultdict(int)
            for s in sales:
                daily_sales[s.sales_date] += s.quantity_sold

            # If sales_history is sparse, check ledger Ship transactions
            if not daily_sales:
                tx_res = await db.execute(
                    select(InventoryTransaction).where(
                        InventoryTransaction.tenant_id == tenant_id,
                        InventoryTransaction.sku_id == sku.id,
                        InventoryTransaction.transaction_type == TransactionType.SHIP,
                    )
                )
                txs = tx_res.scalars().all()
                for tx in txs:
                    tx_date = tx.created_at.date()
                    daily_sales[tx_date] += abs(tx.quantity_change)

            # 3. Execute ML Forecaster
            forecast_result = DemandForecaster.forecast_sku_demand(
                daily_sales=daily_sales,
                start_date=today,
                horizon_days=payload.horizon_days,
            )

            if forecast_result.mape is not None:
                total_mape += forecast_result.mape
                mape_count += 1

            # 4. Remove previous active forecasts from today forward for this SKU
            await db.execute(
                delete(DemandForecast).where(
                    DemandForecast.tenant_id == tenant_id,
                    DemandForecast.sku_id == sku.id,
                    DemandForecast.forecast_date >= today,
                )
            )

            # 5. Insert new predictions
            gen_time = utcnow()
            for pt in forecast_result.points:
                df = DemandForecast(
                    tenant_id=tenant_id,
                    sku_id=sku.id,
                    forecast_date=pt.forecast_date,
                    predicted_demand=pt.predicted_demand,
                    confidence_lower=pt.confidence_lower,
                    confidence_upper=pt.confidence_upper,
                    generated_at=gen_time,
                )
                db.add(df)
                total_forecasts += 1

            # 6. Dynamically calculate recommended reorder point on inventory levels
            # Reorder Point = (Lead Time Days * Daily Demand) + Safety Stock (1.65 * std_dev * sqrt(lead_time))
            lead_time = sku.lead_time_days or 7
            safety_stock = int(math.ceil(1.65 * forecast_result.std_dev * math.sqrt(lead_time)))
            computed_rop = int(math.ceil((lead_time * forecast_result.daily_velocity) + safety_stock))
            reorder_qty = max(10, int(math.ceil(lead_time * forecast_result.daily_velocity * 2)))

            # Update inventory level reorder points
            levels_res = await db.execute(
                select(InventoryLevel).where(
                    InventoryLevel.tenant_id == tenant_id,
                    InventoryLevel.sku_id == sku.id,
                )
            )
            levels = levels_res.scalars().all()
            for lvl in levels:
                if lvl.reorder_point == 0:
                    lvl.reorder_point = max(5, computed_rop)
                if lvl.reorder_quantity == 0:
                    lvl.reorder_quantity = reorder_qty

        await db.commit()

        avg_mape = round(total_mape / mape_count, 2) if mape_count > 0 else None
        return ForecastJobResponse(
            job_id=job_id,
            status="COMPLETED",
            total_skus_processed=len(skus),
            generated_forecasts_count=total_forecasts,
            message=f"Successfully generated {total_forecasts} forecast data points across {len(skus)} SKUs.",
            mape=avg_mape,
        )

    @staticmethod
    async def get_reorder_recommendations(
        db: AsyncSession,
        tenant_id: UUID,
    ) -> list[ReorderRecommendation]:
        """Combine ML demand velocity and inventory levels to generate replenishment recommendations."""
        # 1. Fetch SKUs with products
        skus_res = await db.execute(
            select(SKU)
            .where(SKU.tenant_id == tenant_id)
            .options(selectinload(SKU.product))
        )
        skus = skus_res.scalars().all()

        today = datetime.now(UTC).date()
        horizon_end = today + timedelta(days=30)

        recommendations: list[ReorderRecommendation] = []
        for sku in skus:
            # Get current on_hand sum across locations
            levels_res = await db.execute(
                select(func.coalesce(func.sum(InventoryLevel.on_hand), 0)).where(
                    InventoryLevel.tenant_id == tenant_id,
                    InventoryLevel.sku_id == sku.id,
                )
            )
            current_stock = int(levels_res.scalar_one())

            # Get predicted demand over the next 30 days
            fc_res = await db.execute(
                select(func.coalesce(func.sum(DemandForecast.predicted_demand), 0)).where(
                    DemandForecast.tenant_id == tenant_id,
                    DemandForecast.sku_id == sku.id,
                    DemandForecast.forecast_date >= today,
                    DemandForecast.forecast_date <= horizon_end,
                )
            )
            total_predicted_demand = int(fc_res.scalar_one())
            daily_velocity = round(total_predicted_demand / 30.0, 2) if total_predicted_demand > 0 else 1.0

            lead_time = sku.lead_time_days or 7
            suggested_rop = int(math.ceil(daily_velocity * lead_time * 1.5))
            suggested_order_qty = max(10, int(math.ceil(daily_velocity * 30)))
            days_of_supply = round(current_stock / daily_velocity, 1) if daily_velocity > 0 else 999.0

            # Urgency
            if current_stock <= 0:
                urgency = "Critical"
            elif days_of_supply <= lead_time:
                urgency = "High"
            elif days_of_supply <= lead_time * 2:
                urgency = "Medium"
            else:
                urgency = "Low"

            recommendations.append(
                ReorderRecommendation(
                    sku_id=sku.id,
                    sku_code=sku.sku_code,
                    product_name=sku.product.name if sku.product else None,
                    current_stock=current_stock,
                    predicted_daily_demand=daily_velocity,
                    lead_time_days=lead_time,
                    suggested_reorder_point=suggested_rop,
                    suggested_order_qty=suggested_order_qty,
                    days_of_supply=days_of_supply,
                    urgency=urgency,
                )
            )

        # Sort recommendations by urgency / days of supply
        recommendations.sort(key=lambda r: r.days_of_supply)
        return recommendations
