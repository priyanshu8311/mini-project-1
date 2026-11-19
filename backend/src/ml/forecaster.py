import math
from dataclasses import dataclass
from datetime import date, timedelta


@dataclass
class ForecastPoint:
    """A single daily forecast projection."""

    forecast_date: date
    predicted_demand: int
    confidence_lower: int
    confidence_upper: int


@dataclass
class ForecastResult:
    """Complete forecast output for a SKU."""

    points: list[ForecastPoint]
    daily_velocity: float
    std_dev: float
    mape: float | None = None


class DemandForecaster:
    """Time-series demand forecaster employing exponential smoothing, velocity estimation, and uncertainty intervals."""

    @staticmethod
    def forecast_sku_demand(
        daily_sales: dict[date, int],
        start_date: date,
        horizon_days: int = 30,
        alpha: float = 0.3,
    ) -> ForecastResult:
        """Generate time-series demand predictions from historical sales.

        Args:
            daily_sales: Mapping of historical date -> units sold.
            start_date: First date of the forecasting horizon.
            horizon_days: Number of days forward to project.
            alpha: Exponential smoothing weight (0 < alpha <= 1).
        """
        sorted_dates = sorted(daily_sales.keys())
        sales_values = [daily_sales[d] for d in sorted_dates]

        if not sales_values:
            # Cold-start baseline: 0 velocity
            baseline = 1
            points = [
                ForecastPoint(
                    forecast_date=start_date + timedelta(days=i),
                    predicted_demand=baseline,
                    confidence_lower=0,
                    confidence_upper=baseline * 2,
                )
                for i in range(horizon_days)
            ]
            return ForecastResult(points=points, daily_velocity=float(baseline), std_dev=0.5, mape=None)

        # 1. Simple Exponential Smoothing (Holt-Winters single smoothing)
        smoothed = float(sales_values[0])
        for val in sales_values[1:]:
            smoothed = alpha * val + (1 - alpha) * smoothed

        # 2. Moving Average Velocity (last 14 or 30 days)
        recent_window = sales_values[-30:] if len(sales_values) >= 30 else sales_values
        avg_velocity = sum(recent_window) / len(recent_window)
        # Combine smoothed estimate with average velocity
        blended_velocity = max(0.1, (smoothed * 0.6) + (avg_velocity * 0.4))

        # 3. Variance and Standard Deviation
        variance = sum((x - avg_velocity) ** 2 for x in recent_window) / len(recent_window)
        std_dev = math.sqrt(variance) if variance > 0 else max(0.5, blended_velocity * 0.25)

        # 4. Out-of-sample MAPE calculation if enough points exist
        mape: float | None = None
        if len(sales_values) >= 14:
            train = sales_values[:-7]
            test = sales_values[-7:]
            if train:
                train_smoothed = float(train[0])
                for v in train[1:]:
                    train_smoothed = alpha * v + (1 - alpha) * train_smoothed
                errors = []
                for actual in test:
                    if actual > 0:
                        errors.append(abs(actual - train_smoothed) / actual)
                if errors:
                    mape = round((sum(errors) / len(errors)) * 100, 2)

        # 5. Project future horizon
        # 80% confidence interval: z ≈ 1.28
        # Standard error grows slightly with sqrt(time)
        points: list[ForecastPoint] = []
        for i in range(horizon_days):
            target_date = start_date + timedelta(days=i)
            # Factor in weekday / weekend seasonality pattern if available
            day_of_week = target_date.weekday()
            seasonality_multiplier = 1.15 if day_of_week in (4, 5) else 0.95  # Fri/Sat lift

            daily_pred = max(0.0, blended_velocity * seasonality_multiplier)
            horizon_factor = math.sqrt(1 + (i * 0.05))
            interval = 1.28 * std_dev * horizon_factor

            pred_int = int(round(daily_pred))
            lower_int = max(0, int(round(daily_pred - interval)))
            upper_int = int(round(daily_pred + interval))

            points.append(
                ForecastPoint(
                    forecast_date=target_date,
                    predicted_demand=pred_int,
                    confidence_lower=lower_int,
                    confidence_upper=upper_int,
                )
            )

        return ForecastResult(
            points=points,
            daily_velocity=round(blended_velocity, 2),
            std_dev=round(std_dev, 2),
            mape=mape,
        )
