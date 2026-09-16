"""
powerbi_exporter.py
-------------------
Exporta dados de análise e previsão em formatos prontos para consumo no Power BI:
  - CSV por tabela (cada aba = um CSV)
  - JSON consolidado (para data flow ou REST API)
  - Arquivo de metadados com descrição das tabelas

O Power BI importa CSVs e JSONs nativamente via "Obter Dados".
"""

import json
from pathlib import Path
import pandas as pd
from datetime import datetime


DATE_FORMAT = "%Y-%m-%d"   # ISO 8601 – padrão Power BI


def _df_to_csv(df: pd.DataFrame, path: Path, date_col: str = "data") -> None:
    """Salva DataFrame como CSV com datas no formato ISO."""
    out = df.copy()
    if date_col in out.columns and pd.api.types.is_datetime64_any_dtype(out[date_col]):
        out[date_col] = out[date_col].dt.strftime(DATE_FORMAT)
    out.to_csv(path, index=False, encoding="utf-8-sig")


def export_to_powerbi(
    df_raw: pd.DataFrame,
    report: dict,
    forecast_df: pd.DataFrame,
    output_dir: str | Path,
) -> dict[str, Path]:
    """
    Exporta todas as tabelas para a pasta `output_dir` como:
      - CSV individuais (um por tabela)
      - JSON consolidado (saude_publica_full.json)
      - Metadados (metadata.json)

    Retorna um dict com os caminhos gerados.
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    paths: dict[str, Path] = {}

    # ------------------------------------------------------------------
    # 1. Dados brutos
    # ------------------------------------------------------------------
    p = output_dir / "dados_brutos.csv"
    _df_to_csv(df_raw, p)
    paths["dados_brutos"] = p

    # ------------------------------------------------------------------
    # 2. Resumo estatístico
    # ------------------------------------------------------------------
    p = output_dir / "resumo_estatistico.csv"
    report["summary"].to_csv(p, index=False, encoding="utf-8-sig")
    paths["resumo_estatistico"] = p

    # ------------------------------------------------------------------
    # 3. Totais semanais
    # ------------------------------------------------------------------
    p = output_dir / "totais_semanais.csv"
    _df_to_csv(report["weekly_totals"], p)
    paths["totais_semanais"] = p

    # ------------------------------------------------------------------
    # 4. Previsões
    # ------------------------------------------------------------------
    p = output_dir / "previsoes.csv"
    _df_to_csv(forecast_df, p)
    paths["previsoes"] = p

    # ------------------------------------------------------------------
    # 5. Anomalias
    # ------------------------------------------------------------------
    p = output_dir / "anomalias.csv"
    _df_to_csv(report["anomalies"], p)
    paths["anomalias"] = p

    # ------------------------------------------------------------------
    # 6. Ranking
    # ------------------------------------------------------------------
    p = output_dir / "ranking_municipios.csv"
    report["ranking_casos"].to_csv(p, index=False, encoding="utf-8-sig")
    paths["ranking_municipios"] = p

    # ------------------------------------------------------------------
    # 7. Correlações
    # ------------------------------------------------------------------
    p = output_dir / "correlacoes.csv"
    corr = report["correlations"].reset_index()
    corr.rename(columns={"index": "variavel"}, inplace=True)
    corr.to_csv(p, index=False, encoding="utf-8-sig")
    paths["correlacoes"] = p

    # ------------------------------------------------------------------
    # 8. JSON consolidado
    # ------------------------------------------------------------------
    def df_to_records(df: pd.DataFrame) -> list:
        out = df.copy()
        for col in out.select_dtypes(include=["datetime64[ns]", "datetime64[ns, UTC]"]).columns:
            out[col] = out[col].dt.strftime(DATE_FORMAT)
        return out.to_dict(orient="records")

    full_json = {
        "gerado_em": datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
        "dados_brutos": df_to_records(df_raw),
        "resumo_estatistico": df_to_records(report["summary"]),
        "totais_semanais": df_to_records(report["weekly_totals"]),
        "previsoes": df_to_records(forecast_df),
        "anomalias": df_to_records(report["anomalies"]),
        "ranking_municipios": df_to_records(report["ranking_casos"]),
    }
    p_json = output_dir / "saude_publica_full.json"
    with open(p_json, "w", encoding="utf-8") as f:
        json.dump(full_json, f, ensure_ascii=False, indent=2, default=str)
    paths["json_full"] = p_json

    # ------------------------------------------------------------------
    # 9. Metadados para documentação do Power BI
    # ------------------------------------------------------------------
    metadata = {
        "projeto": "Análise e Previsão de Dados de Saúde Pública",
        "gerado_em": datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
        "tabelas": {
            "dados_brutos": {
                "descricao": "Série temporal semanal de casos, óbitos e recuperados por município.",
                "colunas": list(df_raw.columns),
                "linhas": len(df_raw),
            },
            "totais_semanais": {
                "descricao": "Somatório semanal de todos os municípios com média móvel.",
                "colunas": list(report["weekly_totals"].columns),
            },
            "previsoes": {
                "descricao": "Projeção futura de casos com intervalos de confiança 95%.",
                "colunas": list(forecast_df.columns),
            },
            "resumo_estatistico": {
                "descricao": "Indicadores agregados por município (totais, taxas, médias).",
            },
            "anomalias": {
                "descricao": "Semanas com desvio padrão > 2.5 (Z-score) — picos atípicos.",
            },
            "ranking_municipios": {
                "descricao": "Municípios ordenados por total de casos e taxa de letalidade.",
            },
        },
        "relacionamentos_sugeridos": [
            "dados_brutos[municipio] → resumo_estatistico[municipio]",
            "dados_brutos[municipio] → previsoes[municipio]",
            "dados_brutos[data]     → totais_semanais[data]",
        ],
        "medidas_dax_sugeridas": [
            "Total Casos = SUM(dados_brutos[casos])",
            "Total Óbitos = SUM(dados_brutos[obitos])",
            "Taxa Letalidade % = DIVIDE([Total Óbitos], [Total Casos]) * 100",
            "Variação Semanal % = DIVIDE([Total Casos] - CALCULATE([Total Casos], DATEADD(dados_brutos[data], -7, DAY)), CALCULATE([Total Casos], DATEADD(dados_brutos[data], -7, DAY))) * 100",
        ],
    }
    p_meta = output_dir / "metadata.json"
    with open(p_meta, "w", encoding="utf-8") as f:
        json.dump(metadata, f, ensure_ascii=False, indent=2)
    paths["metadata"] = p_meta

    print(f"[powerbi_exporter] {len(paths)} arquivos exportados para: {output_dir}")
    for name, path in paths.items():
        print(f"  OK {name:25s} -> {path.name}")

    return paths
