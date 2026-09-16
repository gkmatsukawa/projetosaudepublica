"""
main.py
-------
Pipeline principal de analise e previsao de dados de saude publica.

Uso rapido (modo demo com dados sinteticos):
    python main.py

Uso com arquivo real:
    python main.py --input data/raw/meus_dados.xlsx --model arima --steps 12

Argumentos:
    --input   : Caminho para arquivo Excel ou CSV de entrada
                (se omitido, gera dados sinteticos de demonstracao)
    --model   : Modelo de previsao: linear | ewma | arima  (padrao: arima)
    --steps   : Numero de semanas a prever              (padrao: 12)
    --no-excel: Nao gera relatorio Excel
    --no-pbi  : Nao gera exportacao Power BI
"""

import argparse
import sys
from pathlib import Path

# Adiciona o diretorio src ao path para importacoes relativas
sys.path.insert(0, str(Path(__file__).parent / "src"))

from data_loader import load_excel, load_csv, generate_sample_data, save_sample_excel
from analysis import generate_report_dict
from forecasting import forecast_all_municipios
from excel_exporter import export_to_excel
from powerbi_exporter import export_to_powerbi


# ---------------------------------------------------------------------------
# Configuracao de diretorios
# ---------------------------------------------------------------------------
BASE_DIR     = Path(__file__).parent
DATA_RAW     = BASE_DIR / "data" / "raw"
DATA_PROC    = BASE_DIR / "data" / "processed"
EXPORTS_DIR  = BASE_DIR / "data" / "exports"
POWERBI_DIR  = BASE_DIR / "powerbi"
REPORTS_DIR  = BASE_DIR / "reports"

for d in [DATA_RAW, DATA_PROC, EXPORTS_DIR, POWERBI_DIR, REPORTS_DIR]:
    d.mkdir(parents=True, exist_ok=True)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def parse_args():
    parser = argparse.ArgumentParser(
        description="Analise e Previsao de Dados de Saude Publica",
        formatter_class=argparse.RawTextHelpFormatter,
    )
    parser.add_argument(
        "--input", type=str, default=None,
        help="Caminho para arquivo Excel (.xlsx) ou CSV (.csv) de entrada.\n"
             "Se omitido, dados sinteticos de demonstracao serao gerados.",
    )
    parser.add_argument(
        "--model", type=str, default="arima",
        choices=["linear", "ewma", "arima"],
        help="Modelo de previsao: linear | ewma | arima  (padrao: arima)",
    )
    parser.add_argument(
        "--steps", type=int, default=12,
        help="Numero de semanas futuras a prever  (padrao: 12)",
    )
    parser.add_argument(
        "--no-excel", action="store_true",
        help="Pula a geracao do relatorio Excel",
    )
    parser.add_argument(
        "--no-pbi", action="store_true",
        help="Pula a exportacao para Power BI",
    )
    return parser.parse_args()


# ---------------------------------------------------------------------------
# Pipeline
# ---------------------------------------------------------------------------
def run(args=None):
    if args is None:
        args = parse_args()

    print("=" * 60)
    print("  SAUDE PUBLICA - Analise & Previsao")
    print("=" * 60)

    # ------------------------------------------------------------------
    # 1. Carregamento de dados
    # ------------------------------------------------------------------
    print("\n[1/5] Carregando dados...")
    if args.input is None:
        print("  -> Nenhum arquivo fornecido - usando dados sinteticos de demonstracao.")
        df = generate_sample_data()
        sample_path = DATA_RAW / "dados_exemplo.xlsx"
        save_sample_excel(sample_path)
    else:
        input_path = Path(args.input)
        suffix = input_path.suffix.lower()
        if suffix in (".xlsx", ".xls"):
            df = load_excel(input_path)
        elif suffix == ".csv":
            df = load_csv(input_path)
        else:
            print(f"  ERRO: Formato nao suportado: {suffix}. Use .xlsx ou .csv")
            sys.exit(1)
        print(f"  OK Arquivo carregado: {input_path} ({len(df):,} linhas)")

    print(f"  OK Municipios: {sorted(df['municipio'].unique())}")
    print(f"  OK Periodo: {df['data'].min().date()} a {df['data'].max().date()}")
    print(f"  OK Total de registros: {len(df):,}")

    # ------------------------------------------------------------------
    # 2. Analise
    # ------------------------------------------------------------------
    print("\n[2/5] Executando analise estatistica...")
    report = generate_report_dict(df)

    summary = report["summary"]
    print(f"  OK Municipios analisados: {len(summary)}")
    print(f"  OK Total de casos: {summary['total_casos'].sum():,}")
    print(f"  OK Total de obitos: {summary['total_obitos'].sum():,}")
    print(f"  OK Anomalias detectadas: {len(report['anomalies'])}")

    # ------------------------------------------------------------------
    # 3. Previsao
    # ------------------------------------------------------------------
    print(f"\n[3/5] Gerando previsoes ({args.model.upper()}, {args.steps} semanas)...")
    forecast_df = forecast_all_municipios(df, metric="casos", steps=args.steps, model=args.model)
    if forecast_df.empty:
        print("  AVISO: Nenhuma previsao gerada - verifique os dados de entrada.")
    else:
        n_mun = len(df['municipio'].unique())
        print(f"  OK Previsoes geradas: {len(forecast_df)} linhas ({n_mun} municipios x {args.steps} semanas)")

    # Salva dados processados
    processed_path = DATA_PROC / "dados_processados.csv"
    df.to_csv(processed_path, index=False, encoding="utf-8-sig")
    print(f"  OK Dados processados salvos: {processed_path}")

    # ------------------------------------------------------------------
    # 4. Export Excel
    # ------------------------------------------------------------------
    if not args.no_excel:
        print("\n[4/5] Exportando relatorio Excel...")
        excel_path = REPORTS_DIR / "relatorio_saude_publica.xlsx"
        export_to_excel(df, report, forecast_df, excel_path)
    else:
        print("\n[4/5] Export Excel pulado (--no-excel).")

    # ------------------------------------------------------------------
    # 5. Export Power BI
    # ------------------------------------------------------------------
    if not args.no_pbi:
        print("\n[5/5] Exportando arquivos para Power BI...")
        export_to_powerbi(df, report, forecast_df, POWERBI_DIR)
    else:
        print("\n[5/5] Export Power BI pulado (--no-pbi).")

    # ------------------------------------------------------------------
    # Resumo final
    # ------------------------------------------------------------------
    print("\n" + "=" * 60)
    print("  PIPELINE CONCLUIDO COM SUCESSO")
    print("=" * 60)
    print(f"\n  Dados brutos       : {DATA_RAW}")
    print(f"  Dados processados  : {DATA_PROC}")
    if not args.no_excel:
        print(f"  Relatorio Excel    : {REPORTS_DIR / 'relatorio_saude_publica.xlsx'}")
    if not args.no_pbi:
        print(f"  Arquivos Power BI  : {POWERBI_DIR}")
    print()


if __name__ == "__main__":
    run()
