"""
prepare_external.py

Menyiapkan dua dataset eksternal untuk cross-dataset validation (RM3 lapis 3):
  - UCI Online Retail II  (online_retail_II.xlsx)
  - Kaggle Brazilian E-Commerce by Olist (berkas CSV)

Dataset dipotong menjadi empat skala dengan pendekatan yang sama dengan dataset
sintetis: diacak sekali dengan seed tetap, lalu diambil prefiksnya. Dengan
begitu setiap skala merupakan prefiks deterministik dari skala yang lebih besar,
sehingga distribusi atribut konsisten lintas skala.

Kolom ID (UUID) dan Seq (1..N) ditambahkan agar struktur pengujian identik
dengan dataset sintetis: ID sebagai alternate key saat impor ke Dataverse,
Seq sebagai anchor iterasi pola S3 dan kolom pengurutan pola S1.

Cara pakai:
    python prepare_external.py --source raw/ --out data/external/
    python prepare_external.py --source raw/ --out data/external/ --only olist
"""

import argparse
import os
import uuid

import numpy as np
import pandas as pd

SEED = 42
SCALES = [5_000, 10_000, 50_000, 100_000]
DATA_ROW_LIMIT = 2_000

# Filter yang dipakai sebagai kriteria penyaringan pada pengujian.
# Dipilih karena wajar secara domain, bukan karena menghasilkan selectivity
# tertentu. Nilai selectivity aktual diukur dan dilaporkan apa adanya.
UCI_FILTER_COL = "Quantity"
UCI_FILTER_MIN = 6           # "pesanan dalam jumlah banyak"
OLIST_FILTER_COL = "FreightValue"
OLIST_FILTER_MIN = 20.0      # "ongkos kirim tinggi"

# Seed berbeda per dataset agar UUID tidak identik antar dataset
SEED_OFFSET = {"uci": 0, "olist": 1000}


def load_uci(src):
    path = os.path.join(src, "online_retail_II.xlsx")
    print(f"Membaca {path} (butuh beberapa menit, berkas 45 MB) ...")
    sheets = ["Year 2009-2010", "Year 2010-2011"]
    df = pd.concat(
        [pd.read_excel(path, sheet_name=s) for s in sheets], ignore_index=True
    )
    print(f"  baris mentah: {len(df):,}")

    before = len(df)
    df = df.dropna(subset=["Description"]).copy()
    print(f"  dibuang karena Description kosong: {before - len(df):,}")
    df["Customer ID"] = df["Customer ID"].fillna(0).astype("int64")

    out =  pd.DataFrame({
        "Invoice": df["Invoice"].astype(str),
        "StockCode": df["StockCode"].astype(str),
        "Description": df["Description"].astype(str).str.slice(0, 200),
        "Country": df["Country"].astype(str),
        "InvoiceDate": pd.to_datetime(df["InvoiceDate"]).dt.strftime("%Y-%m-%d"),
        "Quantity": df["Quantity"].astype("int64"),
        "Price": df["Price"].astype(float).round(2),
        "CustomerID": df["Customer ID"],
    }) 
    return out.sort_values(list(out.columns), kind="mergesort").reset_index(drop=True)


def load_olist(src):
    print("Membaca berkas Olist dan melakukan join ...")
    o = pd.read_csv(os.path.join(src, "olist_orders_dataset.csv"))
    i = pd.read_csv(os.path.join(src, "olist_order_items_dataset.csv"))
    p = pd.read_csv(os.path.join(src, "olist_products_dataset.csv"))
    c = pd.read_csv(os.path.join(src, "olist_customers_dataset.csv"))

    df = (
        i.merge(o[["order_id", "customer_id", "order_purchase_timestamp"]],
                on="order_id", how="inner")
         .merge(p[["product_id", "product_category_name", "product_weight_g"]],
                on="product_id", how="inner")
         .merge(c[["customer_id", "customer_state"]], on="customer_id", how="inner")
    )
    print(f"  baris setelah join: {len(df):,}")

    before = len(df)
    df = df.dropna(subset=["product_category_name", "product_weight_g"]).copy()
    print(f"  dibuang karena kategori/berat kosong: {before - len(df):,}")

    out = pd.DataFrame({
        "OrderID": df["order_id"].astype(str),
        "ProductID": df["product_id"].astype(str),
        "Category": df["product_category_name"].astype(str),
        "CustomerState": df["customer_state"].astype(str),
        "PurchaseDate": pd.to_datetime(
            df["order_purchase_timestamp"]).dt.strftime("%Y-%m-%d"),
        "Price": df["price"].astype(float).round(2),
        "FreightValue": df["freight_value"].astype(float).round(2),
        "ProductWeight": df["product_weight_g"].astype("int64"),
    })
    return out.sort_values(list(out.columns), kind="mergesort").reset_index(drop=True)


def shuffle_once(df, seed):
    """Acak sekali dengan seed tetap. Prefiks hasil acakan inilah yang dipakai
    sebagai setiap skala, sehingga tiap skala merupakan prefiks deterministik
    dari skala yang lebih besar."""
    return df.sample(frac=1.0, random_state=seed).reset_index(drop=True)


def add_keys(df, seed):
    """Tambahkan ID (UUID) dan Seq (1..N). UUID dibangkitkan dengan generator
    ber-seed agar hasilnya dapat direproduksi."""
    rng = np.random.default_rng(seed)
    ids = [str(uuid.UUID(bytes=bytes(rng.integers(0, 256, 16, dtype=np.uint8)),
                         version=4)) for _ in range(len(df))]
    out = df.copy()
    out.insert(0, "ID", ids)
    out.insert(1, "Seq", range(1, len(df) + 1))
    return out


def filter_mask(df, name):
    if name == "uci":
        return df[UCI_FILTER_COL] >= UCI_FILTER_MIN
    return df[OLIST_FILTER_COL] >= OLIST_FILTER_MIN


def filter_label(name):
    if name == "uci":
        return f"{UCI_FILTER_COL} >= {UCI_FILTER_MIN}"
    return f"{OLIST_FILTER_COL} >= {OLIST_FILTER_MIN}"


def validate(df, name, scale):
    ok, n = True, len(df)
    if n != scale:
        print(f"  [GAGAL] {name} {scale}: jumlah baris {n}, seharusnya {scale}")
        ok = False
    if df.ID.nunique() != n:
        print(f"  [GAGAL] {name} {scale}: ada duplikasi ID")
        ok = False
    if list(df.Seq) != list(range(1, n + 1)):
        print(f"  [GAGAL] {name} {scale}: Seq tidak berurutan 1..{n}")
        ok = False
    if df.isna().any().any():
        print(f"  [GAGAL] {name} {scale}: masih ada nilai kosong")
        ok = False
    if ok:
        print(f"  [OK]    {name} {scale}: {n:,} baris, ID unik, Seq 1..{n}, tanpa null")
    return ok


def process(name, full, out_dir, report):
    print(f"\n=== {name.upper()} ===")
    print(f"Filter: {filter_label(name)}")
    seed = SEED + SEED_OFFSET[name]

    if len(full) < max(SCALES):
        print(f"  [PERINGATAN] populasi {len(full):,} baris, "
              f"kurang dari skala terbesar {max(SCALES):,}")

    keyed = add_keys(shuffle_once(full, seed), seed)
    print(f"Selectivity populasi: {filter_mask(keyed, name).mean()*100:.2f}%")

    for scale in SCALES:
        if scale > len(keyed):
            print(f"  [LEWATI] skala {scale:,} melebihi populasi")
            continue

        sub = keyed.iloc[:scale].copy()
        validate(sub, name, scale)

        n_match = int(filter_mask(sub, name).sum())
        s = n_match / scale
        prediksi = "S1 lengkap" if n_match <= DATA_ROW_LIMIT else "S1 terpotong"

        path = os.path.join(out_dir, f"{name}_{scale}.csv")
        sub.to_csv(path, index=False, encoding="utf-8")
        print(f"          baris cocok filter {n_match:,} "
              f"(selectivity {s*100:.2f}%) -> {prediksi}")
        print(f"          disimpan ke {path}")

        report.append(dict(
            dataset=name, skala=scale, baris_cocok=n_match,
            selectivity_pct=round(s * 100, 2),
            ambang_s1=round(DATA_ROW_LIMIT / s) if s else None,
            prediksi_kerangka=prediksi,
        ))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", default="raw", help="folder berkas dataset mentah")
    ap.add_argument("--out", default=os.path.join("data", "external"))
    ap.add_argument("--only", choices=["uci", "olist"], help="proses satu dataset saja")
    args = ap.parse_args()

    os.makedirs(args.out, exist_ok=True)
    report = []

    if args.only in (None, "uci"):
        process("uci", load_uci(args.source), args.out, report)
    if args.only in (None, "olist"):
        process("olist", load_olist(args.source), args.out, report)

    rep = pd.DataFrame(report)
    rep_path = os.path.join(args.out, "selectivity_report.csv")
    rep.to_csv(rep_path, index=False)

    print("\n=== RINGKASAN SELECTIVITY DAN PREDIKSI KERANGKA ===")
    print(rep.to_string(index=False))
    print(f"\nLaporan disimpan ke {rep_path}")


if __name__ == "__main__":
    main()