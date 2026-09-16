"""
data_loader.py
--------------
Carrega dados de saúde pública a partir de arquivos Excel (.xlsx/.xls) ou CSV.
Também gera dados sintéticos de exemplo para demonstração.
"""

import pandas as pd
import numpy as np
from pathlib import Path
from datetime import date, timedelta


# ---------------------------------------------------------------------------
# Colunas esperadas no arquivo de entrada
# ---------------------------------------------------------------------------
REQUIRED_COLUMNS = {"data", "municipio", "casos", "obitos", "recuperados"}


def load_excel(path: str | Path) -> pd.DataFrame:
    """Lê um arquivo Excel e retorna um DataFrame normalizado."""
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Arquivo não encontrado: {path}")

    df = pd.read_excel(path, parse_dates=["data"])
    df.columns = [c.strip().lower().replace(" ", "_") for c in df.columns]

    missing = REQUIRED_COLUMNS - set(df.columns)
    if missing:
        raise ValueError(f"Colunas obrigatórias ausentes: {missing}")

    df = df.sort_values("data").reset_index(drop=True)
    return df


def load_csv(path: str | Path) -> pd.DataFrame:
    """Lê um arquivo CSV e retorna um DataFrame normalizado."""
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Arquivo não encontrado: {path}")

    df = pd.read_csv(path, parse_dates=["data"])
    df.columns = [c.strip().lower().replace(" ", "_") for c in df.columns]

    missing = REQUIRED_COLUMNS - set(df.columns)
    if missing:
        raise ValueError(f"Colunas obrigatórias ausentes: {missing}")

    df = df.sort_values("data").reset_index(drop=True)
    return df


def generate_sample_data(
    municipios: list[str] | None = None,
    start: str = "2022-01-01",
    periods: int = 104,  # ~2 anos semanais
    seed: int = 42,
) -> pd.DataFrame:
    """
    Gera dados sintéticos de saúde pública para demonstração.

    Parâmetros
    ----------
    municipios : lista de nomes de municípios (padrão: 5 cidades fictícias)
    start      : data de início (YYYY-MM-DD)
    periods    : número de semanas
    seed       : semente aleatória
    """
    rng = np.random.default_rng(seed)
    if municipios is None:
        municipios = ["São Paulo", "Rio de Janeiro", "Belo Horizonte", "Salvador", "Curitiba"]

    datas = pd.date_range(start=start, periods=periods, freq="W")
    records = []

    for municipio in municipios:
        # Tendência base por município
        base = rng.integers(50, 300)
        trend = np.linspace(0, rng.integers(-30, 80), periods)
        sazonalidade = 20 * np.sin(2 * np.pi * np.arange(periods) / 52)
        ruido = rng.normal(0, 10, periods)

        casos_raw = base + trend + sazonalidade + ruido
        casos = np.clip(casos_raw, 0, None).astype(int)
        obitos = np.clip((casos * rng.uniform(0.01, 0.05, periods)).astype(int), 0, None)
        recuperados = np.clip(casos - obitos - rng.integers(0, 10, periods), 0, None)

        for i, dt in enumerate(datas):
            records.append(
                {
                    "data": dt,
                    "municipio": municipio,
                    "casos": int(casos[i]),
                    "obitos": int(obitos[i]),
                    "recuperados": int(recuperados[i]),
                    "ativos": max(0, int(casos[i]) - int(obitos[i]) - int(recuperados[i])),
                }
            )

    df = pd.DataFrame(records).sort_values(["municipio", "data"]).reset_index(drop=True)
    return df


def save_sample_excel(output_path: str | Path) -> Path:
    """Gera o Excel de dados de exemplo e salva no caminho indicado."""
    output_path = Path(output_path)
    df = generate_sample_data()
    df.to_excel(output_path, index=False)
    print(f"[data_loader] Dados de exemplo salvos em: {output_path}")
    return output_path
