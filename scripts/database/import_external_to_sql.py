"""
import_external_to_sql.py

Membuat tabel dan mengimpor dataset eksternal (UCI dan Olist, masing-masing
empat skala) ke Azure SQL, lalu menjalankan UPDATE STATISTICS dan memverifikasi
hasil impor terhadap selectivity_report.csv dari prepare_external.py.

Cara pakai:
    python import_external_to_sql.py --data data/external --sql create_tables_external.sql
    python import_external_to_sql.py --data data/external --drop      # bangun ulang
    python import_external_to_sql.py --data data/external --dry-run   # cek tanpa koneksi

Kredensial dibaca dari .env:
    SQL_CONN=Driver={ODBC Driver 18 for SQL Server};Server=tcp:...;Database=...;Uid=...;Pwd=...;Encrypt=yes;
"""

import argparse
import os
import re
import sys

import pandas as pd
from dotenv import load_dotenv

SCALES = [5_000, 10_000, 50_000, 100_000]
LABEL = {5_000: "5k", 10_000: "10k", 50_000: "50k", 100_000: "100k"}
BATCH = 5_000

DATASETS = {
    "uci": {
        "prefix": "UCI",
        "columns": ["ID", "Seq", "Invoice", "StockCode", "Description", "Country",
                    "InvoiceDate", "Quantity", "Price", "CustomerID"],
        "filter_sql": "Quantity >= 6",
    },
    "olist": {
        "prefix": "Olist",
        "columns": ["ID", "Seq", "OrderID", "ProductID", "Category", "CustomerState",
                    "PurchaseDate", "Price", "FreightValue", "ProductWeight"],
        "filter_sql": "FreightValue >= 20",
    },
}


def split_sql(path):
    """Pecah berkas SQL menjadi pernyataan tunggal (tanpa GO)."""
    text = open(path, encoding="utf-8").read()
    text = re.sub(r"--[^\n]*", "", text)
    return [s.strip() for s in text.split(";") if s.strip()]


def table_name(ds, scale):
    return f"{DATASETS[ds]['prefix']}{LABEL[scale]}"


def load_csv(data_dir, ds, scale):
    path = os.path.join(data_dir, f"{ds}_{scale}.csv")
    df = pd.read_csv(path, dtype=str, keep_default_na=False)
    cols = DATASETS[ds]["columns"]
    missing = [c for c in cols if c not in df.columns]
    if missing:
        raise ValueError(f"{path}: kolom tidak ditemukan {missing}")
    return df[cols]


def to_rows(df):
    return [tuple(r) for r in df.itertuples(index=False, name=None)]


def run(args):
    report_path = os.path.join(args.data, "selectivity_report.csv")
    expected = pd.read_csv(report_path) if os.path.exists(report_path) else None
    if expected is None:
        print(f"[PERINGATAN] {report_path} tidak ditemukan; verifikasi filter dilewati")

    plan = []
    for ds in DATASETS:
        for scale in SCALES:
            df = load_csv(args.data, ds, scale)
            if len(df) != scale:
                sys.exit(f"[GAGAL] {ds}_{scale}.csv berisi {len(df)} baris")
            plan.append((ds, scale, df))
    print(f"Berkas siap: {len(plan)} tabel, "
          f"{sum(len(d) for _, _, d in plan):,} baris total")

    if args.dry_run:
        stmts = split_sql(args.sql)
        print(f"Dry run: {len(stmts)} pernyataan SQL terbaca, "
              f"{sum(s.upper().startswith('CREATE TABLE') for s in stmts)} CREATE TABLE")
        for ds, scale, df in plan:
            print(f"  {table_name(ds, scale):<10} {len(df):>7,} baris  "
                  f"contoh ID {df.ID.iloc[0]}")
        return

    import pyodbc
    load_dotenv()
    conn = pyodbc.connect(os.environ["SQL_CONN"], autocommit=False)
    cur = conn.cursor()

    if args.drop:
        for ds, scale, _ in plan:
            cur.execute(f"DROP TABLE IF EXISTS dbo.{table_name(ds, scale)}")
        conn.commit()
        print("Tabel lama dihapus")

    for stmt in split_sql(args.sql):
        m = re.search(r"CREATE TABLE dbo\.(\w+)", stmt)
        if m:
            cur.execute("SELECT OBJECT_ID(?, 'U')", f"dbo.{m.group(1)}")
            if cur.fetchone()[0] is not None:
                print(f"  {m.group(1)} sudah ada, dilewati")
                continue
        try:
            cur.execute(stmt)
        except pyodbc.ProgrammingError as e:
            if "already exists" in str(e):
                continue
            raise
    conn.commit()
    print("Skema siap")

    cur.fast_executemany = True
    for ds, scale, df in plan:
        tbl = table_name(ds, scale)
        cur.execute(f"SELECT COUNT(*) FROM dbo.{tbl}")
        if cur.fetchone()[0] > 0:
            print(f"  {tbl}: sudah berisi data, dilewati (pakai --drop untuk ulang)")
            continue

        cols = DATASETS[ds]["columns"]
        sql = (f"INSERT INTO dbo.{tbl} ({', '.join(cols)}) "
               f"VALUES ({', '.join('?' * len(cols))})")
        rows = to_rows(df)
        for i in range(0, len(rows), BATCH):
            cur.executemany(sql, rows[i:i + BATCH])
        conn.commit()
        cur.execute(f"UPDATE STATISTICS dbo.{tbl} WITH FULLSCAN")
        conn.commit()
        print(f"  {tbl}: {len(rows):,} baris diimpor")

    print("\n=== VERIFIKASI ===")
    ok_all = True
    for ds, scale, _ in plan:
        tbl = table_name(ds, scale)
        cur.execute(f"""
            SELECT COUNT(*), COUNT(DISTINCT ID), COUNT(DISTINCT Seq), MIN(Seq), MAX(Seq),
                   SUM(CASE WHEN {DATASETS[ds]['filter_sql']} THEN 1 ELSE 0 END)
            FROM dbo.{tbl}""")
        total, uid, useq, smin, smax, match = cur.fetchone()

        ok = total == uid == useq == scale and smin == 1 and smax == scale
        exp_match = None
        if expected is not None:
            row = expected[(expected.dataset == ds) & (expected.skala == scale)]
            if len(row):
                exp_match = int(row.baris_cocok.iloc[0])
                ok = ok and match == exp_match

        flag = "OK" if ok else "GAGAL"
        ok_all &= ok
        exp_txt = f" (seharusnya {exp_match:,})" if exp_match is not None else ""
        print(f"  [{flag:5}] {tbl:<10} total {total:>7,}  Seq {smin}-{smax}  "
              f"cocok filter {match:>6,}{exp_txt}")

    conn.close()
    print("\nSemua tabel lolos verifikasi" if ok_all else "\nADA TABEL YANG GAGAL")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default=os.path.join("data", "external"))
    ap.add_argument("--sql", default="create_tables_external.sql")
    ap.add_argument("--drop", action="store_true", help="hapus tabel lama sebelum impor")
    ap.add_argument("--dry-run", action="store_true", help="cek berkas tanpa koneksi DB")
    run(ap.parse_args())


if __name__ == "__main__":
    main()