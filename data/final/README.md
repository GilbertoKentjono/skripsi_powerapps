# data/final

Data yang dipakai di buku. File di folder ini beku: jangan diedit. Kalau ada koreksi, buat file baru dan catat alasannya di sini.

## Data mentah pengukuran

| File | Isi | Waktu (WIB) |
|---|---|---|
| `raw_20260912_024306.csv` | Sesi sintetis utama: S1–S4 × DV/SQL × 5k/10k/25k/50k/100k | 12 Sep 2026, 02:43–04:30 |
| `ext_20261016_025842.csv` | Sesi eksternal utama: 40 kombinasi UCI + Olist | 16 Okt 2026, 02:59–05:48 |
| `ext_20261017_014519.csv` | Rerun 4 kombinasi yang tercemar + 1 kontrol | 17 Okt 2026, 01:46–02:04 |
| `appi.csv` | Export tabel `requests` App Insights (`appi-skripsi`), timestamp UTC | sejak 11 Sep 2026 |
| `selectivity_report.csv` | Jumlah baris cocok dan selektivitas tiap dataset eksternal | — |
| `boundary_expected.csv` | Prediksi uji tambahan, dibekukan sebelum run: V, predikat, s estimasi, baris prediksi, baris benar | 11 Nov 2026, sebelum 23:36 |
| `bnd_20261111_233618.csv` | Sesi uji tambahan: S1 × DV/SQL × 11 sel (9k, 11k, 12k, 15k, 20k, 10k_s05–s50) | 11–12 Nov 2026, 23:36–01:02 |

Kolom CSV pengukuran: `timestamp, pattern, source, scale, run_no, phase (warmup/measure), rows, roundtrip_ms, fn_ms, raw_status`.
Setiap kombinasi: 2 warmup + 5 measure. Hanya baris `phase=measure` dengan status `DONE` yang dianalisis.

## Catatan sesi eksternal

Pada sesi utama, 4 kombinasi S1/S2 jalur Azure SQL (OLIST10k, OLIST5k untuk S1; UCI5k, OLIST10k untuk S2) melambat menjadi 21–37 s
dalam jendela 04:56–05:40 WIB. S4 SQL pada jendela yang sama tetap normal, jadi DB tidak bermasalah; anomali ada di jalur konektor
SQL Power Apps. Keempat kombinasi diukur ulang di `ext_20261017_014519.csv`. Data final = sesi utama tanpa 4 kombinasi itu + rerun.

Kontrol S1 SQL UCI5k: median 1168 ms (utama) vs 1005 ms (rerun), Mann-Whitney p = 0,016. Ada efek sesi kecil (~14%),
tidak mengubah keputusan karena semua median S1 jauh di bawah SLA 2000 ms.

## Catatan sesi uji tambahan

V diemulasikan dengan `Seq <= V` pada tabel 25k (prefiks deterministik). Selektivitas divariasikan dengan `JumlahTransaksi >= T`
pada tabel 10k. T untuk s05 dikoreksi manual ke 20 karena nilai diskret membuat s05 dan s10 sempat bernilai T sama; koreksi
dilakukan sebelum prediksi dibekukan. Run 4 SQL_11k tercatat 200.263 ms; tidak diulang karena jumlah baris identik di kelima run
dan median sel tidak terpengaruh.

## Hasil analisis

| File | Dibuat oleh | Dipakai di |
|---|---|---|
| `synthetic/summary.csv` | `analyze_results.py` | Tabel 4.4 |
| `synthetic/breakpoints.csv` | `analyze_results.py` | Tabel 4.5 |
| `synthetic/stat_kruskal.csv` | `analyze_results.py` | Tabel 4.6 |
| `synthetic/stat_dunn_{DV,SQL}_{5k,10k}.csv` | `analyze_results.py` | Lampiran A |
| `synthetic/comparison_rm2.csv` | `analyze_results.py` | arsip awal RM2; digantikan `rm2_effect_size.csv` |
| `rm2_effect_size.csv` | `deepen_analysis.py` | Tabel 4.7, Lampiran B |
| `truncation_model.csv` | `deepen_analysis.py` | Tabel 4.13, Lampiran C |
| `framework_sensitivity.csv` | `deepen_analysis.py` | Tabel 4.15 |
| `bnd_summary.csv` | `evaluate_boundary.py` | Tabel 4.12 |
| `bnd_confusion_f1.csv` | `evaluate_boundary.py` | Tabel 4.11 (baris uji tambahan) |
| `ext_summary.csv` | `validate_external.py` | tabel hasil eksternal (Bab 4, lampiran) |
| `ext_ground_truth.csv` | `validate_external.py` | input `evaluate_framework.py` |
| `ext_rule_validation.csv` | `validate_external.py` | arsip versi awal; digantikan `framework_confusion_f1.csv` |
| `framework_confusion_f1.csv` | `evaluate_framework.py` | tabel evaluasi decision framework (Bab 4) |
| `appi_s4_summary.csv` | `match_appi.py` | tabel tiga lapis waktu S4 (Bab 4) |
| `appi_s4_matched.csv` | `match_appi.py` | bukti pasangan request ↔ run |

Cakupan App Insights: 149 dari 182 run S4 (82%). 33 run eksternal di jendela 04:21–04:48 WIB tidak punya telemetri,
padahal statusnya `DONE` dan `fn_ms` tercatat. `fn_ms` di CSV tetap data utama.
