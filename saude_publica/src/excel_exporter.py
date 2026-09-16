"""
excel_exporter.py
-----------------
Exporta resultados de análise e previsão para um arquivo Excel formatado
com múltiplas abas, tabelas, cabeçalhos coloridos e gráficos embutidos.

Requer: pip install openpyxl
"""

from pathlib import Path
import pandas as pd
import openpyxl
from openpyxl import Workbook
from openpyxl.styles import (
    PatternFill, Font, Alignment, Border, Side, numbers
)
from openpyxl.chart import LineChart, BarChart, Reference
from openpyxl.chart.series import DataPoint
from openpyxl.utils.dataframe import dataframe_to_rows
from openpyxl.utils import get_column_letter
from datetime import datetime


# ---------------------------------------------------------------------------
# Paleta de cores
# ---------------------------------------------------------------------------
COLOR_HEADER_BG = "1F497D"   # azul escuro
COLOR_HEADER_FG = "FFFFFF"   # branco
COLOR_ALT_ROW   = "DCE6F1"   # azul claro alternado
COLOR_ACCENT    = "E26B0A"   # laranja (avisos, anomalias)
COLOR_GOOD      = "375623"   # verde escuro
COLOR_GOOD_BG   = "EBFBEE"   # verde claro


def _apply_header(ws, row: int, n_cols: int, bg: str = COLOR_HEADER_BG, fg: str = COLOR_HEADER_FG):
    fill = PatternFill("solid", fgColor=bg)
    font = Font(bold=True, color=fg, size=11)
    for col in range(1, n_cols + 1):
        cell = ws.cell(row=row, column=col)
        cell.fill = fill
        cell.font = font
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)


def _write_df(ws, df: pd.DataFrame, start_row: int = 1, title: str | None = None) -> int:
    """
    Escreve um DataFrame na planilha com cabeçalho formatado.
    Retorna a próxima linha disponível após os dados.
    """
    row = start_row

    if title:
        ws.cell(row=row, column=1, value=title).font = Font(bold=True, size=13, color=COLOR_HEADER_BG)
        row += 1

    # Cabeçalhos
    for col_idx, col_name in enumerate(df.columns, start=1):
        ws.cell(row=row, column=col_idx, value=str(col_name).replace("_", " ").title())
    _apply_header(ws, row, len(df.columns))
    row += 1

    # Dados
    alt_fill = PatternFill("solid", fgColor=COLOR_ALT_ROW)
    for r_idx, row_data in enumerate(df.itertuples(index=False), start=0):
        for col_idx, value in enumerate(row_data, start=1):
            cell = ws.cell(row=row, column=col_idx, value=value)
            if r_idx % 2 == 1:
                cell.fill = alt_fill
            cell.alignment = Alignment(horizontal="center")
        row += 1

    # Ajusta largura das colunas
    for col_idx, col_name in enumerate(df.columns, start=1):
        max_len = max(len(str(col_name)), df[col_name].astype(str).map(len).max() if len(df) > 0 else 10)
        ws.column_dimensions[get_column_letter(col_idx)].width = min(max_len + 4, 40)

    return row + 1


def _add_line_chart(ws, data_ws_title: str, title: str,
                    min_row: int, max_row: int,
                    date_col: int, value_cols: list[int],
                    anchor_cell: str = "A1"):
    """Adiciona um gráfico de linha referenciando outra planilha."""
    chart = LineChart()
    chart.title = title
    chart.style = 10
    chart.y_axis.title = "Casos"
    chart.x_axis.title = "Semana"
    chart.width = 22
    chart.height = 12

    for col in value_cols:
        data_ref = Reference(ws.parent[data_ws_title], min_col=col, min_row=min_row, max_row=max_row)
        chart.add_data(data_ref, titles_from_data=True)

    cats = Reference(ws.parent[data_ws_title], min_col=date_col, min_row=min_row + 1, max_row=max_row)
    chart.set_categories(cats)
    ws.add_chart(chart, anchor_cell)


def export_to_excel(
    df_raw: pd.DataFrame,
    report: dict,
    forecast_df: pd.DataFrame,
    output_path: str | Path,
) -> Path:
    """
    Gera um arquivo Excel com as seguintes abas:
      1. Dados Brutos
      2. Resumo Estatístico
      3. Totais Semanais (+ gráfico)
      4. Previsões (+ gráfico)
      5. Anomalias
      6. Ranking de Municípios
      7. Correlações
    """
    output_path = Path(output_path)
    wb = Workbook()

    # ------------------------------------------------------------------
    # Aba 1 – Dados Brutos
    # ------------------------------------------------------------------
    ws_raw = wb.active
    ws_raw.title = "Dados Brutos"
    # Formata datas como string antes de escrever
    df_raw_out = df_raw.copy()
    if pd.api.types.is_datetime64_any_dtype(df_raw_out["data"]):
        df_raw_out["data"] = df_raw_out["data"].dt.strftime("%d/%m/%Y")
    _write_df(ws_raw, df_raw_out, start_row=1, title="📋 Dados Brutos – Saúde Pública")

    # ------------------------------------------------------------------
    # Aba 2 – Resumo Estatístico
    # ------------------------------------------------------------------
    ws_summary = wb.create_sheet("Resumo Estatístico")
    _write_df(ws_summary, report["summary"], title="📊 Resumo Estatístico por Município")

    # ------------------------------------------------------------------
    # Aba 3 – Totais Semanais
    # ------------------------------------------------------------------
    ws_weekly = wb.create_sheet("Totais Semanais")
    weekly = report["weekly_totals"].copy()
    if pd.api.types.is_datetime64_any_dtype(weekly["data"]):
        weekly["data"] = weekly["data"].dt.strftime("%d/%m/%Y")
    next_row = _write_df(ws_weekly, weekly, title="📅 Totais Semanais (todos os municípios)")

    # ------------------------------------------------------------------
    # Aba 4 – Previsões
    # ------------------------------------------------------------------
    ws_fc = wb.create_sheet("Previsões")
    fc_out = forecast_df.copy()
    if "data" in fc_out.columns and pd.api.types.is_datetime64_any_dtype(fc_out["data"]):
        fc_out["data"] = fc_out["data"].dt.strftime("%d/%m/%Y")
    next_fc = _write_df(ws_fc, fc_out, title="🔮 Previsões de Casos (próximas semanas)")

    # ------------------------------------------------------------------
    # Aba 5 – Anomalias
    # ------------------------------------------------------------------
    ws_anom = wb.create_sheet("Anomalias")
    anom = report["anomalies"].copy()
    if len(anom) > 0 and pd.api.types.is_datetime64_any_dtype(anom["data"]):
        anom["data"] = anom["data"].dt.strftime("%d/%m/%Y")
    _write_df(ws_anom, anom, title="⚠️ Anomalias Detectadas (Z-score > 2.5)")

    # Destaca anomalias positivas em laranja
    orange_fill = PatternFill("solid", fgColor=COLOR_ACCENT)
    for row in ws_anom.iter_rows(min_row=3, max_row=ws_anom.max_row):
        try:
            z_val = float(row[3].value) if row[3].value is not None else 0
            if z_val > 0:
                for cell in row:
                    cell.fill = orange_fill
        except (ValueError, TypeError):
            pass

    # ------------------------------------------------------------------
    # Aba 6 – Ranking
    # ------------------------------------------------------------------
    ws_rank = wb.create_sheet("Ranking")
    _write_df(ws_rank, report["ranking_casos"], title="🏆 Ranking por Total de Casos")

    # ------------------------------------------------------------------
    # Aba 7 – Correlações
    # ------------------------------------------------------------------
    ws_corr = wb.create_sheet("Correlações")
    corr_df = report["correlations"].reset_index()
    corr_df.rename(columns={"index": "variavel"}, inplace=True)
    _write_df(ws_corr, corr_df, title="🔗 Matriz de Correlação")

    # ------------------------------------------------------------------
    # Rodapé informativo em todas as abas
    # ------------------------------------------------------------------
    generated_at = datetime.now().strftime("%d/%m/%Y %H:%M")
    for ws in wb.worksheets:
        last = ws.max_row + 2
        ws.cell(row=last, column=1, value=f"Gerado em: {generated_at}").font = Font(italic=True, size=9, color="888888")

    wb.save(output_path)
    print(f"[excel_exporter] Relatório Excel salvo em: {output_path}")
    return output_path
