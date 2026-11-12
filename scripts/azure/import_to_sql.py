"""
import_to_sql.py

Import dataset CSV ke Azure SQL menggunakan pyodbc bulk insert,
lalu menjalankan UPDATE STATISTICS dan verifikasi selectivity.
Referensi: Proposal Skripsi bagian 5.2 dan 9.1.

Prasyarat:
    pip install pyodbc python-dotenv
    Install "ODBC Driver 18 for SQL Server" dari Microsoft.
    Tabel sudah dibuat lewat create_tables.sql.

Isi file .env di folder yang sama:
    SQL_SERVER=sql-skripsi.database.windows.net
    SQL_DATABASE=db-skripsi
    SQL_USERNAME=sqladmin
    SQL_PASSWORD=<password kamu>

Cara pakai:
    python import_to_sql.py              # import semua skala
    python import_to_sql.py 5k           # import satu skala saja
"""

import csv
import os
import sys
import time

import pyodbc
from dotenv import load_dotenv

load_dotenv()

# ---------------------------------------------------------------------------
# Konfigurasi
# ---------------------------------------------------------------------------

SERVER = os.getenv("SQL_SERVER")
DATABASE = os.getenv("SQL_DATABASE")
USERNAME = os.getenv("SQL_USERNAME")
PASSWORD = os.getenv("SQL_PASSWORD")

DRIVER = "{ODBC Driver 18 for SQL Server}"

CONN_STR = (
    f"DRIVER={DRIVER};"
    f"SERVER={SERVER};"
    f"DATABASE={DATABASE};"
    f"UID={USERNAME};"
    f"PWD={PASSWORD};"
    "Encrypt=yes;"
    "TrustServerCertificate=no;"
    "Connection Timeout=60;"
)

# skala -> (nama tabel, path CSV)
DATASETS = {
    "5k":   ("TestDataset5k",   os.path.join("data", "train",   "dataset_5000.csv")),
    "10k":  ("TestDataset10k",  os.path.join("data", "train",   "dataset_10000.csv")),
    "25k":  ("TestDataset25k",  os.path.join("data", "holdout", "dataset_25000.csv")),
    "50k":  ("TestDataset50k",  os.path.join("data", "train",   "dataset_50000.csv")),
    "100k": ("TestDataset100k", os.path.join("data", "train",   "dataset_100000.csv")),
}

COLUMNS = [
    "ID", "Nama", "Email", "Wilayah", "KategoriProduk",
    "Tanggal", "JumlahTransaksi", "Status", "Rating", "Seq"
]

BATCH_SIZE = 1000


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def check_env():
    missing = [
        name for name, val in [
            ("SQL_SERVER", SERVER), ("SQL_DATABASE", DATABASE),
            ("SQL_USERNAME", USERNAME), ("SQL_PASSWORD", PASSWORD),
        ] if not val
    ]
    if missing:
        print("[GAGAL] Variabel .env belum lengkap: " + ", ".join(missing))
        sys.exit(1)


def read_csv(path):
    """Baca CSV, kembalikan list of tuple sesuai urutan COLUMNS."""
    rows = []
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for r in reader:
            rows.append((
                r["ID"],
                r["Nama"],
                r["Email"],
                r["Wilayah"],
                r["KategoriProduk"],
                r["Tanggal"],
                int(r["JumlahTransaksi"]),
                r["Status"],
                int(r["Rating"]),
                int(r["Seq"]),
            ))
    return rows


def import_one(conn, scale_key):
    table, csv_path = DATASETS[scale_key]

    if not os.path.exists(csv_path):
        print(f"[LEWAT] {scale_key}: file tidak ditemukan -> {csv_path}")
        return

    print(f"\n=== {scale_key} -> {table} ===")
    print(f"  Membaca {csv_path} ...")
    rows = read_csv(csv_path)
    print(f"  {len(rows):,} baris dibaca dari CSV")

    cur = conn.cursor()
    cur.fast_executemany = True

    # Kosongkan tabel dulu supaya import berulang tidak menduplikasi
    cur.execute(f"DELETE FROM {table}")
    conn.commit()

    placeholders = ", ".join(["?"] * len(COLUMNS))
    collist = ", ".join(COLUMNS)
    sql = f"INSERT INTO {table} ({collist}) VALUES ({placeholders})"

    t0 = time.perf_counter()
    for i in range(0, len(rows), BATCH_SIZE):
        batch = rows[i:i + BATCH_SIZE]
        cur.executemany(sql, batch)
        conn.commit()
        done = min(i + BATCH_SIZE, len(rows))
        print(f"  ... {done:,}/{len(rows):,}", end="\r")
    elapsed = time.perf_counter() - t0
    print(f"\n  Insert selesai dalam {elapsed:.1f} detik")

    # UPDATE STATISTICS -- sesuai proposal 5.2, supaya Query Optimizer
    # memakai statistik yang akurat sebelum pengujian dimulai.
    print("  Menjalankan UPDATE STATISTICS WITH FULLSCAN ...")
    cur.execute(f"UPDATE STATISTICS {table} WITH FULLSCAN")
    conn.commit()

    verify(cur, table)


def verify(cur, table):
    """Verifikasi jumlah baris, duplikasi ID, dan selectivity kolom Status."""
    cur.execute(f"SELECT COUNT(*) FROM {table}")
    total = cur.fetchone()[0]

    cur.execute(f"SELECT COUNT(DISTINCT ID) FROM {table}")
    distinct_id = cur.fetchone()[0]

    print(f"  Total baris      : {total:,}")
    if distinct_id != total:
        print(f"  [MASALAH] ID unik hanya {distinct_id:,} -- ada duplikasi!")
    else:
        print(f"  ID unik          : {distinct_id:,} (tidak ada duplikat)")

    cur.execute(f"SELECT Status, COUNT(*) FROM {table} GROUP BY Status ORDER BY Status")
    print("  Distribusi Status:")
    for status, count in cur.fetchall():
        pct = count / total * 100 if total else 0
        print(f"    {status:<12} {count:>8,}  ({pct:.2f}%)")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    check_env()

    targets = sys.argv[1:] if len(sys.argv) > 1 else list(DATASETS.keys())
    for t in targets:
        if t not in DATASETS:
            print(f"[GAGAL] Skala '{t}' tidak dikenal. Pilihan: {', '.join(DATASETS)}")
            sys.exit(1)

    print(f"Menghubungkan ke {SERVER} / {DATABASE} ...")
    try:
        conn = pyodbc.connect(CONN_STR)
    except pyodbc.Error as e:
        print(f"[GAGAL] Tidak bisa konek: {e}")
        print("Cek: IP kamu sudah di-allowlist di firewall Azure SQL?")
        print("     ODBC Driver 18 for SQL Server sudah terinstall?")
        sys.exit(1)
    print("Terhubung.")

    for t in targets:
        import_one(conn, t)

    conn.close()
    print("\nSelesai.")


if __name__ == "__main__":
    main()
