"""
analysis.py
-----------
Módulo de análise estatística e de tendências de dados de saúde pública.
"""

import pandas as pd
import numpy as np
from typing import Any


def summary_statistics(df: pd.DataFrame) -> pd.DataFrame:
    """
    Retorna estatísticas descritivas por município:
    total de casos, óbitos, recuperados, taxa de letalidade e taxa de recuperação.
    """
    grp = df.groupby("municipio").agg(
        total_casos=("casos", "sum"),
        total_obitos=("obitos", "sum"),
        total_recuperados=("recuperados", "sum"),
        media_semanal_casos=("casos", "mean"),
        max_casos_semana=("casos", "max"),
        min_casos_semana=("casos", "min"),
    )

    grp["taxa_letalidade_pct"] = (grp["total_obitos"] / grp["total_casos"].replace(0, np.nan) * 100).round(2)
    grp["taxa_recuperacao_pct"] = (
        grp["total_recuperados"] / grp["total_casos"].replace(0, np.nan) * 100
    ).round(2)

    return grp.reset_index()


def weekly_totals(df: pd.DataFrame) -> pd.DataFrame:
    """Agrega os dados por semana (soma de todos os municípios)."""
    grp = (
        df.groupby("data")
        .agg(
            casos=("casos", "sum"),
            obitos=("obitos", "sum"),
            recuperados=("recuperados", "sum"),
            ativos=("ativos", "sum"),
        )
        .reset_index()
    )
    grp["media_movel_7"] = grp["casos"].rolling(window=7, min_periods=1).mean().round(1)
    return grp


def municipio_trend(df: pd.DataFrame, municipio: str) -> pd.DataFrame:
    """Extrai e enriquece a série temporal de um município específico."""
    sub = df[df["municipio"] == municipio].copy().sort_values("data").reset_index(drop=True)
    sub["media_movel_4sem"] = sub["casos"].rolling(window=4, min_periods=1).mean().round(1)
    sub["variacao_pct"] = sub["casos"].pct_change().mul(100).round(2)
    return sub


def detect_anomalies(df: pd.DataFrame, z_threshold: float = 2.5) -> pd.DataFrame:
    """
    Detecta semanas com número de casos anormalmente alto ou baixo
    usando Z-score por município.
    """
    results = []
    for mun, grp in df.groupby("municipio"):
        grp = grp.copy()
        mu = grp["casos"].mean()
        sigma = grp["casos"].std()
        if sigma == 0:
            continue
        grp["z_score"] = (grp["casos"] - mu) / sigma
        anomalies = grp[grp["z_score"].abs() > z_threshold].copy()
        anomalies["municipio"] = mun
        results.append(anomalies[["data", "municipio", "casos", "z_score"]])

    if not results:
        return pd.DataFrame(columns=["data", "municipio", "casos", "z_score"])
    return pd.concat(results).sort_values("z_score", ascending=False).reset_index(drop=True)


def correlation_matrix(df: pd.DataFrame) -> pd.DataFrame:
    """Retorna a matriz de correlação entre casos, óbitos e recuperados."""
    cols = ["casos", "obitos", "recuperados"]
    available = [c for c in cols if c in df.columns]
    return df[available].corr().round(4)


def rank_municipios(df: pd.DataFrame, by: str = "total_casos", ascending: bool = False) -> pd.DataFrame:
    """Classifica municípios por um indicador calculado pelo summary_statistics."""
    stats = summary_statistics(df)
    if by not in stats.columns:
        raise ValueError(f"Coluna '{by}' não disponível. Opções: {list(stats.columns)}")
    return stats.sort_values(by, ascending=ascending).reset_index(drop=True)


def generate_report_dict(df: pd.DataFrame) -> dict[str, Any]:
    """Consolida todas as análises num dicionário para uso interno ou exportação."""
    return {
        "summary": summary_statistics(df),
        "weekly_totals": weekly_totals(df),
        "anomalies": detect_anomalies(df),
        "correlations": correlation_matrix(df),
        "ranking_casos": rank_municipios(df, by="total_casos"),
        "ranking_letalidade": rank_municipios(df, by="taxa_letalidade_pct"),
    }
