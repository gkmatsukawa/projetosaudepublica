"""
forecasting.py
--------------
Módulo de previsão de séries temporais para dados de saúde pública.

Modelos disponíveis
-------------------
1. LinearTrendForecaster  – regressão linear simples (baseline rápido)
2. MovingAverageForecaster – média móvel ponderada exponencialmente (EWM)
3. ARIMAForecaster         – ARIMA via statsmodels (mais preciso)

Todos os forecasters seguem a mesma interface:
    .fit(series: pd.Series) -> self
    .predict(steps: int) -> pd.DataFrame  com colunas [data, previsao, lower, upper]
"""

import warnings
import numpy as np
import pandas as pd
from abc import ABC, abstractmethod


# ---------------------------------------------------------------------------
# Interface base
# ---------------------------------------------------------------------------

class BaseForecaster(ABC):
    """Interface comum para todos os forecasters."""

    @abstractmethod
    def fit(self, series: pd.Series) -> "BaseForecaster":
        """Treina o modelo com a série temporal fornecida."""
        ...

    @abstractmethod
    def predict(self, steps: int = 12) -> pd.DataFrame:
        """
        Retorna previsões para os próximos `steps` períodos.
        DataFrame com colunas: data, previsao, lower, upper.
        """
        ...


# ---------------------------------------------------------------------------
# 1. Regressão Linear
# ---------------------------------------------------------------------------

class LinearTrendForecaster(BaseForecaster):
    """
    Ajusta uma regressão linear simples sobre o índice temporal
    e extrapola para os próximos `steps` períodos.
    """

    def __init__(self):
        self._coef = None
        self._intercept = None
        self._residual_std = None
        self._last_index = None
        self._freq = None

    def fit(self, series: pd.Series) -> "LinearTrendForecaster":
        y = series.values.astype(float)
        x = np.arange(len(y))
        self._coef = np.polyfit(x, y, 1)
        fitted = np.polyval(self._coef, x)
        self._residual_std = np.std(y - fitted)
        self._last_index = len(y) - 1
        if isinstance(series.index, pd.DatetimeIndex):
            self._freq = pd.infer_freq(series.index) or "W"
            self._last_date = series.index[-1]
        else:
            self._last_date = None
        return self

    def predict(self, steps: int = 12) -> pd.DataFrame:
        if self._coef is None:
            raise RuntimeError("Chame .fit() antes de .predict()")

        future_idx = np.arange(self._last_index + 1, self._last_index + 1 + steps)
        forecasts = np.polyval(self._coef, future_idx)
        forecasts = np.clip(forecasts, 0, None)

        ci = 1.96 * self._residual_std
        dates = self._make_dates(steps)

        return pd.DataFrame(
            {
                "data": dates,
                "previsao": forecasts.round(1),
                "lower": np.clip(forecasts - ci, 0, None).round(1),
                "upper": (forecasts + ci).round(1),
            }
        )

    def _make_dates(self, steps: int):
        if self._last_date is not None:
            return pd.date_range(self._last_date, periods=steps + 1, freq=self._freq)[1:]
        return list(range(self._last_index + 1, self._last_index + 1 + steps))


# ---------------------------------------------------------------------------
# 2. Exponential Weighted Moving Average
# ---------------------------------------------------------------------------

class EWMAForecaster(BaseForecaster):
    """
    Previsão via média móvel ponderada exponencialmente (EWMA).
    Simples e robusto para séries com tendência suave.
    """

    def __init__(self, span: int = 8):
        self._span = span
        self._last_value = None
        self._residual_std = None
        self._last_date = None
        self._freq = None

    def fit(self, series: pd.Series) -> "EWMAForecaster":
        smoothed = series.ewm(span=self._span, adjust=False).mean()
        self._last_value = float(smoothed.iloc[-1])
        self._residual_std = float((series - smoothed).std())
        if isinstance(series.index, pd.DatetimeIndex):
            self._freq = pd.infer_freq(series.index) or "W"
            self._last_date = series.index[-1]
        return self

    def predict(self, steps: int = 12) -> pd.DataFrame:
        if self._last_value is None:
            raise RuntimeError("Chame .fit() antes de .predict()")

        # EWMA flat projection (nível constante igual ao último valor suavizado)
        forecasts = np.full(steps, self._last_value)
        ci = 1.96 * self._residual_std * np.sqrt(np.arange(1, steps + 1))

        if self._last_date is not None:
            dates = pd.date_range(self._last_date, periods=steps + 1, freq=self._freq)[1:]
        else:
            dates = list(range(steps))

        return pd.DataFrame(
            {
                "data": dates,
                "previsao": np.clip(forecasts, 0, None).round(1),
                "lower": np.clip(forecasts - ci, 0, None).round(1),
                "upper": (forecasts + ci).round(1),
            }
        )


# ---------------------------------------------------------------------------
# 3. ARIMA
# ---------------------------------------------------------------------------

class ARIMAForecaster(BaseForecaster):
    """
    Previsão com ARIMA (statsmodels).
    Requer: pip install statsmodels
    """

    def __init__(self, order: tuple[int, int, int] = (2, 1, 2)):
        self._order = order
        self._model_fit = None
        self._last_date = None
        self._freq = None

    def fit(self, series: pd.Series) -> "ARIMAForecaster":
        try:
            from statsmodels.tsa.arima.model import ARIMA
        except ImportError:
            raise ImportError("Instale statsmodels: pip install statsmodels")

        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            model = ARIMA(series.values.astype(float), order=self._order)
            self._model_fit = model.fit()

        if isinstance(series.index, pd.DatetimeIndex):
            self._freq = pd.infer_freq(series.index) or "W"
            self._last_date = series.index[-1]

        return self

    def predict(self, steps: int = 12) -> pd.DataFrame:
        if self._model_fit is None:
            raise RuntimeError("Chame .fit() antes de .predict()")

        forecast_res = self._model_fit.get_forecast(steps=steps)
        mean_forecast = forecast_res.predicted_mean
        ci = forecast_res.conf_int(alpha=0.05)

        if self._last_date is not None:
            dates = pd.date_range(self._last_date, periods=steps + 1, freq=self._freq)[1:]
        else:
            dates = list(range(steps))

        return pd.DataFrame(
            {
                "data": dates,
                "previsao": np.clip(mean_forecast, 0, None).round(1),
                "lower": np.clip(ci[:, 0], 0, None).round(1),
                "upper": np.clip(ci[:, 1], 0, None).round(1),
            }
        )


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------

FORECASTERS = {
    "linear": LinearTrendForecaster,
    "ewma": EWMAForecaster,
    "arima": ARIMAForecaster,
}


def get_forecaster(name: str, **kwargs) -> BaseForecaster:
    """
    Retorna uma instância do forecaster pelo nome.

    Opções: 'linear', 'ewma', 'arima'
    """
    name = name.lower()
    if name not in FORECASTERS:
        raise ValueError(f"Forecaster desconhecido: '{name}'. Opções: {list(FORECASTERS.keys())}")
    return FORECASTERS[name](**kwargs)


def forecast_municipio(
    df: pd.DataFrame,
    municipio: str,
    metric: str = "casos",
    steps: int = 12,
    model: str = "arima",
) -> pd.DataFrame:
    """
    Atalho: prevê `metric` para um município usando o modelo escolhido.

    Retorna DataFrame com colunas: data, previsao, lower, upper, municipio, metrica, modelo
    """
    sub = df[df["municipio"] == municipio].sort_values("data").set_index("data")[metric]
    forecaster = get_forecaster(model)
    forecaster.fit(sub)
    result = forecaster.predict(steps=steps)
    result["municipio"] = municipio
    result["metrica"] = metric
    result["modelo"] = model
    return result


def forecast_all_municipios(
    df: pd.DataFrame,
    metric: str = "casos",
    steps: int = 12,
    model: str = "arima",
) -> pd.DataFrame:
    """Prevê `metric` para todos os municípios no DataFrame."""
    parts = []
    for municipio in df["municipio"].unique():
        try:
            fc = forecast_municipio(df, municipio, metric=metric, steps=steps, model=model)
            parts.append(fc)
        except Exception as exc:
            print(f"[forecasting] Erro em {municipio}: {exc}")
    if not parts:
        return pd.DataFrame()
    return pd.concat(parts, ignore_index=True)
