# Saúde Pública – Análise e Previsão de Dados

Sistema completo de análise estatística e previsão de séries temporais para dados de saúde pública, com exportação automática para **Excel** e **Power BI**.

---

## 📁 Estrutura do Projeto

```
saude_publica/
├── main.py                   # Pipeline principal (ponto de entrada)
├── requirements.txt          # Dependências Python
├── src/
│   ├── data_loader.py        # Carregamento de dados (Excel / CSV / sintético)
│   ├── analysis.py           # Análise estatística e detecção de anomalias
│   ├── forecasting.py        # Modelos de previsão (Linear, EWMA, ARIMA)
│   ├── excel_exporter.py     # Exportação para Excel formatado (.xlsx)
│   └── powerbi_exporter.py   # Exportação para Power BI (CSV + JSON)
├── data/
│   ├── raw/                  # Arquivos de entrada (Excel/CSV do usuário)
│   ├── processed/            # Dados limpos e processados
│   └── exports/              # Exportações diversas
├── reports/                  # Relatório Excel gerado automaticamente
└── powerbi/                  # Arquivos CSV + JSON para o Power BI
```

---

## 🚀 Instalação

```bash
# Clone o repositório
git clone <url-do-repo>
cd saude_publica

# (Recomendado) Crie um ambiente virtual
python -m venv .venv
.venv\Scripts\activate        # Windows
# source .venv/bin/activate   # Linux / macOS

# Instale as dependências
pip install -r requirements.txt
```

---

## ▶️ Uso

### Modo demo (dados sintéticos)
```bash
python main.py
```

### Com arquivo Excel ou CSV real
```bash
python main.py --input data/raw/meus_dados.xlsx
```

### Escolher modelo de previsão e horizonte
```bash
python main.py --input data/raw/meus_dados.xlsx --model arima --steps 24
```

### Opções completas
```
--input    Caminho para .xlsx ou .csv de entrada
--model    Modelo de previsão: linear | ewma | arima  (padrão: arima)
--steps    Semanas futuras a prever                   (padrão: 12)
--no-excel Pula a geração do relatório Excel
--no-pbi   Pula a exportação para Power BI
```

---

## 📋 Formato do Arquivo de Entrada

O arquivo Excel/CSV deve ter **pelo menos** estas colunas (nomes em minúsculas):

| Coluna       | Tipo        | Descrição                        |
|--------------|-------------|----------------------------------|
| `data`       | Data        | Data de referência (semanal/diária) |
| `municipio`  | Texto       | Nome do município                |
| `casos`      | Inteiro     | Novos casos confirmados          |
| `obitos`     | Inteiro     | Óbitos no período                |
| `recuperados`| Inteiro     | Pacientes recuperados            |

---

## 📊 Saídas Geradas

### Relatório Excel (`reports/relatorio_saude_publica.xlsx`)
| Aba                 | Conteúdo                                     |
|---------------------|----------------------------------------------|
| Dados Brutos        | Série temporal completa                      |
| Resumo Estatístico  | Totais, taxas e médias por município         |
| Totais Semanais     | Agregação semanal + média móvel              |
| Previsões           | Projeções com intervalos de confiança 95%   |
| Anomalias           | Semanas com desvio atípico (Z-score > 2.5)  |
| Ranking             | Municípios ordenados por total de casos      |
| Correlações         | Matriz de correlação (casos/óbitos/recuperados) |

### Arquivos Power BI (`powerbi/`)
| Arquivo                    | Uso no Power BI                        |
|----------------------------|----------------------------------------|
| `dados_brutos.csv`         | Tabela fato principal                  |
| `totais_semanais.csv`      | Gráfico de linha temporal              |
| `previsoes.csv`            | Gráfico de previsão com banda de IC   |
| `resumo_estatistico.csv`   | KPI cards e tabela resumo              |
| `anomalias.csv`            | Tabela de alertas                      |
| `ranking_municipios.csv`   | Gráfico de barras ranking              |
| `saude_publica_full.json`  | Data flow / REST API                   |
| `metadata.json`            | Documentação + medidas DAX sugeridas   |

---

## 🔮 Modelos de Previsão

| Modelo   | Classe                   | Descrição                                  |
|----------|--------------------------|--------------------------------------------|
| `linear` | `LinearTrendForecaster`  | Regressão linear – rápido, baseline        |
| `ewma`   | `EWMAForecaster`         | Média exponencial ponderada – suave        |
| `arima`  | `ARIMAForecaster`        | ARIMA(2,1,2) – mais preciso para sazonalidade |

---

## 📦 Dependências

```
pandas      >= 2.0
openpyxl    >= 3.1
numpy       >= 1.26
statsmodels >= 0.14   (necessário para ARIMA)
scikit-learn>= 1.4
```

---

## 🗂️ Git – Boas Práticas

```bash
# Inicializar repositório
git init

# Primeiro commit
git add .
git commit -m "feat: análise e previsão de saúde pública – versão inicial"

# Novo ciclo de análise
git add reports/ powerbi/
git commit -m "data: relatório semana 2025-W40"
```

---

## 📄 Licença

Uso interno. Adaptado livremente para fins de análise em saúde pública.
