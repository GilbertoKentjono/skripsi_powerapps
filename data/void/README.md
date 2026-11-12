# data/void

Sesi pengukuran lengkap yang tidak dipakai di buku. Disimpan untuk transparansi.

| File | Alasan tidak dipakai |
|---|---|
| `ext_20261015_020351.csv` | Sesi eksternal pertama. Ada 6 run duplikat karena status `DONE` lama terbaca sebelum run baru mulai (guard `RUNNING` sudah ditambahkan di `run_external.py`), dan ada aktivitas streaming selama sesi. |
| `ext_20261015_125044.csv` | Sesi siang hari (12:51–15:50 WIB), di luar jendela off-peak. S1/S2 jalur Azure SQL melambat ke 25–40 s pada 12:55–14:55 sementara S4 SQL normal (anomali konektor). |
