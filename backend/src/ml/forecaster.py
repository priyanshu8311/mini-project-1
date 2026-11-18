import math
from dataclasses import dataclass
from datetime import date, timedelta

# pyrefly: ignore[missing-import]
import numpy as np
from sklearn.linear_model import Ridge


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
    """Time-series demand forecaster trained on historical data using Scikit-Learn."""

    @staticmethod
    def _build_feature_vector(
        history_values: list[float],
        target_date: date,
        time_index: int,
    ) -> list[float]:
        """Extract tabular ML features from historical sequence up to target_date."""
        # 1. Lag features
        lag_1 = history_values[-1] if len(history_values) >= 1 else 0.0
        lag_2 = history_values[-2] if len(history_values) >= 2 else lag_1
        lag_7 = history_values[-7] if len(history_values) >= 7 else lag_1
        lag_14 = history_values[-14] if len(history_values) >= 14 else lag_7

        # 2. Rolling window statistics
        w7 = history_values[-7:] if len(history_values) >= 7 else history_values
        rolling_mean_7 = float(np.mean(w7)) if w7 else lag_1
        rolling_std_7 = float(np.std(w7)) if len(w7) > 1 else 0.5

        # 3. Calendar & Seasonality features
        day_of_week = float(target_date.weekday())  # 0=Monday, 6=Sunday
        is_weekend = 1.0 if target_date.weekday() in (4, 5) else 0.0  # Fri/Sat lift
        day_of_month = float(target_date.day)

        return [
            lag_1,
            lag_2,
            lag_7,
            lag_14,
            rolling_mean_7,
            rolling_std_7,
            day_of_week,
            is_weekend,
            day_of_month,
            float(time_index),
        ]

    @staticmethod
    def forecast_sku_demand(
        daily_sales: dict[date, int],
        start_date: date,
        horizon_days: int = 30,
        alpha: float = 1.0,
    ) -> ForecastResult:
        """Train a Scikit-Learn regressor on daily sales and project future demand."""
        sorted_dates = sorted(daily_sales.keys())
        sales_values = [float(daily_sales[d]) for d in sorted_dates]

        # Cold-start fallback if zero or insufficient data
        if not sales_values or len(sales_values) < 3:
            baseline = 1.0
            points = [
                ForecastPoint(
                    forecast_date=start_date + timedelta(days=i),
                    predicted_demand=int(baseline),
                    confidence_lower=0,
                    confidence_upper=int(baseline * 2),
                )
                for i in range(horizon_days)
            ]
            return ForecastResult(
                points=points,
                daily_velocity=baseline,
                std_dev=0.5,
                mape=None,
            )

        # 1. Build Supervised Training Dataset (X, y)
        X_train_list: list[list[float]] = []
        y_train_list: list[float] = []

        # Start from day index 1 so at least 1 lag exists
        for idx in range(1, len(sales_values)):
            curr_date = sorted_dates[idx]
            sub_history = sales_values[:idx]
            feat = DemandForecaster._build_feature_vector(
                history_values=sub_history,
                target_date=curr_date,
                time_index=idx,
            )
            X_train_list.append(feat)
            y_train_list.append(sales_values[idx])

        X_train = np.array(X_train_list, dtype=np.float64)
        y_train = np.array(y_train_list, dtype=np.float64)

        # 2. Fit Scikit-Learn Model
        model = Ridge(alpha=alpha, positive=False)
        model.fit(X_train, y_train)

        # 3. Model Variance / Residual Error
        train_preds = model.predict(X_train)
        residuals = y_train - train_preds
        variance = float(np.mean(residuals**2)) if len(residuals) > 0 else 1.0
        std_dev = max(0.5, math.sqrt(variance))

        # 4. Out-of-sample MAPE Validation (holdout test set if >= 14 points)
        mape: float | None = None
        if len(sales_values) >= 14:
            split_idx = len(sales_values) - 7
            X_val_train, y_val_train = X_train[:split_idx], y_train[:split_idx]
            X_val_test, y_val_test = X_train[split_idx:], y_train[split_idx:]
            if len(X_val_train) >= 3 and len(X_val_test) > 0:
                val_model = Ridge(alpha=alpha)
                val_model.fit(X_val_train, y_val_train)
                val_preds = val_model.predict(X_val_test)
                errors = [
                    abs(actual - pred) / actual
                    for actual, pred in zip(y_val_test, val_preds, strict=False)
                    if actual > 0
                ]
                if errors:
                    mape = round(float(np.mean(errors)) * 100, 2)

        # 5. Autoregressive Recursive Forecasting into Future
        simulated_history = list(sales_values)
        points: list[ForecastPoint] = []
        predicted_values: list[float] = []

        start_time_idx = len(sales_values)
        for i in range(horizon_days):
            target_date = start_date + timedelta(days=i)
            features = DemandForecaster._build_feature_vector(
                history_values=simulated_history,
                target_date=target_date,
                time_index=start_time_idx + i,
            )
            X_step = np.array([features], dtype=np.float64)
            step_pred = float(model.predict(X_step)[0])
            step_pred = max(0.0, step_pred)  # Demand cannot be negative

            # Uncertainty expands slightly further into the future
            horizon_penalty = math.sqrt(1.0 + (i * 0.05))
            interval = 1.28 * std_dev * horizon_penalty  # 80% confidence interval

            pred_int = int(round(step_pred))
            lower_int = max(0, int(round(step_pred - interval)))
            upper_int = int(round(step_pred + interval))

            points.append(
                ForecastPoint(
                    forecast_date=target_date,
                    predicted_demand=pred_int,
                    confidence_lower=lower_int,
                    confidence_upper=upper_int,
                )
            )

            # Append prediction to history for autoregressive lags in next step
            predicted_values.append(step_pred)
            simulated_history.append(step_pred)

        daily_velocity = (
            float(np.mean(predicted_values))
            if predicted_values
            else float(np.mean(sales_values[-14:]))
        )

        return ForecastResult(
            points=points,
            daily_velocity=round(daily_velocity, 2),
            std_dev=round(std_dev, 2),
            mape=mape,
        )
