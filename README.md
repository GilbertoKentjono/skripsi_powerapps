# Analisis Scalability Threshold Delegation Query Power Apps: Komparasi Dataverse dan Azure SQL

Repositori pendukung Tugas Akhir — Gilberto Poetro Kentjono (C14230224), Informatika, Universitas Kristen Petra.
Dosen pembimbing: Agustinus Noertjahyana.

Berisi seluruh script, data mentah pengukuran, hasil analisis, dan bukti pendukung yang dipakai di buku.

## Struktur

```
scripts/
  dataset/        pembuatan dataset sintetis dan eksternal (UCI Online Retail II, Olist)
  database/       skema dan import ke Azure SQL
  azure-function/ Custom API untuk pola S4 (Azure Functions, Python 3.11)
  playwright/     orkestrasi pengukuran otomatis di Power Apps
  analysis/       analisis statistik, validasi lintas-dataset, evaluasi decision framework
data/
  final/          data yang dipakai di buku (beku, jangan diubah)
  void/           sesi yang tidak dipakai, beserta alasannya
figures/          diagram untuk buku
evidence/         screenshot App checker dan konfigurasi Azure
docs/             catatan pendukung
```

## Pola yang diuji

| Kode | Pola | Delegasi |
|---|---|---|
| S1 | `Filter()` + `Sort()` delegable, `ClearCollect` | delegable |
| S2 | `Not(IsBlank())` (baseline non-delegable) | non-delegable |
| S3 | Collection pagination dengan kursor `Seq` | delegable per halaman |
| S4 | Custom API via Azure Functions (agregat COUNT) | di luar Power Apps |

## Reproduksi analisis

Butuh Python 3.11 dengan `pandas`, `numpy`, `scipy`, `ruptures`.

```
cd data/final
python ../../scripts/analysis/validate_external.py    # menghasilkan ext_summary.csv, ext_ground_truth.csv
python ../../scripts/analysis/evaluate_framework.py   # menghasilkan framework_confusion_f1.csv
python ../../scripts/analysis/match_appi.py           # menghasilkan appi_s4_summary.csv, appi_s4_matched.csv
```

Diagram decision framework dirender dari `figures/decision_tree.dot` dengan Graphviz:

```
cd figures
dot -Tpng decision_tree.dot -o decision_tree.png
```

## Dataset

Dataset tidak disertakan. Buat ulang dengan script di `scripts/dataset/` (seed deterministik = 42).

- Sintetis: `generate_dataset.py`
- UCI Online Retail II — https://archive.ics.uci.edu/dataset/502/online+retail+ii (CC BY 4.0)
- Brazilian E-Commerce Public Dataset by Olist — https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce (CC BY-NC-SA 4.0)

Unduh dataset mentah, lalu jalankan `prepare_external.py`.

## Credential

Tidak ada credential di repositori ini. Salin `.env.example` menjadi `.env` dan isi nilainya sendiri.

```
Skripsi
├─ data
│  ├─ external
│  │  ├─ olist_10000.csv
│  │  ├─ olist_100000.csv
│  │  ├─ olist_5000.csv
│  │  ├─ olist_50000.csv
│  │  ├─ uci_10000.csv
│  │  ├─ uci_100000.csv
│  │  ├─ uci_5000.csv
│  │  └─ uci_50000.csv
│  ├─ ext_20261015_020351.csv
│  ├─ ext_20261015_125044.csv
│  ├─ final
│  │  ├─ appi.csv
│  │  ├─ appi_s4_matched.csv
│  │  ├─ appi_s4_summary.csv
│  │  ├─ ext_20261016_025842.csv
│  │  ├─ ext_20261017_014519.csv
│  │  ├─ ext_ground_truth.csv
│  │  ├─ ext_rule_validation.csv
│  │  ├─ ext_summary.csv
│  │  ├─ framework_confusion_f1.csv
│  │  ├─ raw_20260912_024306.csv
│  │  ├─ README.md
│  │  └─ selectivity_report.csv
│  ├─ holdout
│  │  └─ dataset_25000.csv
│  ├─ pilot
│  │  ├─ raw_20260910_230921.csv
│  │  ├─ raw_20260912_150602.csv
│  │  ├─ raw_20260912_155825.csv
│  │  └─ raw_20260913_031314.csv
│  ├─ README.md
│  └─ train
│     ├─ dataset_10000.csv
│     ├─ dataset_100000.csv
│     ├─ dataset_5000.csv
│     └─ dataset_50000.csv
├─ docs
├─ figures
│  ├─ decision_tree.dot
│  ├─ decision_tree.png
│  ├─ decision_tree.svg
│  └─ Untitled Diagram.drawio
├─ gen_s3.py
├─ README.md
├─ results
│  ├─ ext_20261014_152818.csv
│  ├─ ext_20261014_154048.csv
│  ├─ ext_20261014_191218.csv
│  ├─ ext_20261014_195744.csv
│  ├─ ext_20261015_020351.csv
│  ├─ ext_20261015_125044.csv
│  ├─ raw_20260910_153248.csv
│  ├─ raw_20260910_153858.csv
│  ├─ raw_20260912_154642.csv
│  ├─ raw_20260912_155347.csv
│  └─ raw_20260912_160340.csv
├─ s4-api
│  ├─ .python_packages
│  ├─ function_app.py
│  ├─ host.json
│  ├─ local.settings.json
│  └─ requirements.txt
└─ scripts
   ├─ .env
   ├─ analysis
   │  ├─ breakpoints.csv
   │  ├─ comparison_rm2.csv
   │  ├─ evaluate_framework.py
   │  ├─ fig_completeness.png
   │  ├─ fig_scalability.png
   │  ├─ match_appi.py
   │  ├─ stat_dunn_DV_10k.csv
   │  ├─ stat_dunn_DV_5k.csv
   │  ├─ stat_dunn_SQL_10k.csv
   │  ├─ stat_dunn_SQL_5k.csv
   │  ├─ stat_kruskal.csv
   │  ├─ summary.csv
   │  └─ validate_external.py
   ├─ analyze_results.py
   ├─ azure
   │  ├─ create_tables.sql
   │  └─ import_to_sql.py
   ├─ create_tables_external.sql
   ├─ data_backup
   │  ├─ holdout
   │  │  └─ dataset_25000.csv
   │  └─ train
   │     ├─ dataset_10000.csv
   │     ├─ dataset_100000.csv
   │     ├─ dataset_5000.csv
   │     └─ dataset_50000.csv
   ├─ generate_dataset.py
   ├─ import_external_to_sql.py
   ├─ playwright
   │  ├─ auth_setup.py
   │  ├─ auth_state.json
   │  ├─ discover_selectors.py
   │  ├─ metrics_logger.py
   │  ├─ run_experiment.py
   │  └─ run_external.py
   ├─ prepare_external.py
   ├─ raw
   │  ├─ olist_customers_dataset.csv
   │  ├─ olist_orders_dataset.csv
   │  ├─ olist_order_items_dataset.csv
   │  ├─ olist_products_dataset.csv
   │  └─ online_retail_II.xlsx
   └─ test_playwright.py

```