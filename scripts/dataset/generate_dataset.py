"""
generate_dataset.py

Generate dataset sintetis untuk pengujian delegation query Power Apps.
Referensi: Proposal Skripsi bagian 5.2 (Data yang Digunakan).

Cara pakai:
    python generate_dataset.py

Output:
    data/train/dataset_5000.csv
    data/train/dataset_10000.csv
    data/train/dataset_50000.csv
    data/train/dataset_100000.csv
    data/holdout/dataset_25000.csv   <- JANGAN dipakai untuk analisis RM1/RM2,
                                          cuma untuk internal holdout validation
                                          decision framework (RM3).

Setiap skala di-generate SECARA INDEPENDEN (bukan subsample dari skala
terbesar), dengan random seed di-reset ke 42 sebelum tiap skala, supaya
hasilnya reproducible sesuai proposal.

Kolom Seq adalah integer berurutan 1..N yang berfungsi sebagai anchor
cursor-based pagination pada pola S3. UUID tidak dipakai sebagai anchor
karena operator perbandingan (>, <=) pada kolom teks tidak delegable di
Power Apps, sehingga tiap iterasi S3 akan diproses client-side dan pola
S3 kehilangan perbedaannya dengan S2. Seq adalah kolom kontrol teknis,
bukan atribut data domain.
"""

import csv
import os
import random
import uuid
from datetime import date, timedelta

from faker import Faker

# ---------------------------------------------------------------------------
# Konfigurasi
# ---------------------------------------------------------------------------

SEED = 42

# Skala yang dipakai untuk training/pengujian utama (RM1 & RM2)
TRAIN_SCALES = [5_000, 10_000, 50_000, 100_000]

# Skala yang disisihkan sebagai internal holdout validation set (RM3)
HOLDOUT_SCALES = [25_000]

OUTPUT_DIR_TRAIN = os.path.join("data", "train")
OUTPUT_DIR_HOLDOUT = os.path.join("data", "holdout")

# Pilihan Choice/Option Set. HARUS SAMA PERSIS dengan Option Set yang nanti
# didefinisikan di Dataverse -- kalau beda, import bakal gagal/ke-null.
WILAYAH_CHOICES = [
    "Jawa",
    "Sumatra",
    "Kalimantan",
    "Sulawesi",
    "Bali & Nusa Tenggara",
    "Papua & Maluku",
]

KATEGORI_PRODUK_CHOICES = [
    "Elektronik",
    "Fashion",
    "Makanan & Minuman",
    "Kesehatan",
    "Rumah Tangga",
    "Olahraga",
    "Buku & Alat Tulis",
    "Otomotif",
]

# Status dikontrol supaya selectivity filter status == "Selesai" ~20%
# di seluruh skala (lihat proposal 5.2). Silakan ganti label sesuai
# kebutuhan, yang penting bobotnya tetap 20/80.
STATUS_CHOICES = ["Selesai", "Pending"]
STATUS_WEIGHTS = [0.20, 0.80]

TANGGAL_START = date(2024, 1, 1)
TANGGAL_END = date(2026, 8, 29)

JUMLAH_TRANSAKSI_MIN = 1
JUMLAH_TRANSAKSI_MAX = 20

RATING_MIN = 1
RATING_MAX = 5

CSV_COLUMNS = [
    "ID",
    "Nama",
    "Email",
    "Wilayah",
    "KategoriProduk",
    "Tanggal",
    "JumlahTransaksi",
    "Status",
    "Rating",
    "Seq"
]


# ---------------------------------------------------------------------------
# Generasi
# ---------------------------------------------------------------------------

def _random_date(fake: Faker) -> str:
    delta_days = (TANGGAL_END - TANGGAL_START).days
    offset = random.randint(0, delta_days)
    d = TANGGAL_START + timedelta(days=offset)
    return d.isoformat()


def generate_dataset(n_records: int, seed: int = SEED):
    """
    Generate n_records baris data sintetis.
    Reset seed persis sebelum generate, supaya tiap skala reproducible
    dan independen satu sama lain (bukan hasil subsample).

    Return: list of dict, satu dict per baris (urutan kolom sesuai CSV_COLUMNS).
    """
    random.seed(seed)
    Faker.seed(seed)
    fake = Faker()

    rows = []
    seen_ids = set()

    for i in range(1, n_records + 1):        
        # ID di-generate manual (bukan pakai GUID otomatis Dataverse) supaya
        # nilainya identik persis di Azure SQL maupun Dataverse.
        row_id = str(uuid.uuid4())
        # jaga-jaga kalau ada tabrakan UUID (praktis mustahil, tapi tetap dicek)
        while row_id in seen_ids:
            row_id = str(uuid.uuid4())
        seen_ids.add(row_id)

        row = {
            "ID": row_id,
            "Nama": fake.name(),
            "Email": fake.email(),
            "Wilayah": random.choice(WILAYAH_CHOICES),
            "KategoriProduk": random.choice(KATEGORI_PRODUK_CHOICES),
            "Tanggal": _random_date(fake),
            "JumlahTransaksi": random.randint(JUMLAH_TRANSAKSI_MIN, JUMLAH_TRANSAKSI_MAX),
            "Status": random.choices(STATUS_CHOICES, weights=STATUS_WEIGHTS, k=1)[0],
            "Rating": random.randint(RATING_MIN, RATING_MAX),
            "Seq": i,
        }
        rows.append(row)

    return rows


# ---------------------------------------------------------------------------
# Validasi (sesuai proposal 5.2: no duplikasi ID, selectivity status ~20%)
# ---------------------------------------------------------------------------

def validate_dataset(rows, label: str, tolerance: float = 0.03) -> bool:
    """
    Cek dua hal:
      1. Tidak ada duplikasi ID.
      2. Proporsi Status == "Selesai" mendekati 20% (dalam toleransi).

    Return True kalau lolos semua, False kalau ada yang gagal (dan print alasannya).
    """
    ok = True
    n = len(rows)

    ids = [r["ID"] for r in rows]
    n_unique = len(set(ids))
    if n_unique != n:
        print(f"  [GAGAL] {label}: ada {n - n_unique} ID duplikat dari {n} baris")
        ok = False
    else:
        print(f"  [OK]    {label}: {n} ID semuanya unik")

    target_status = STATUS_CHOICES[0]  # "Selesai"
    target_weight = STATUS_WEIGHTS[0]  # 0.20
    n_target = sum(1 for r in rows if r["Status"] == target_status)
    actual_ratio = n_target / n if n else 0
    diff = abs(actual_ratio - target_weight)
    if diff > tolerance:
        print(
            f"  [GAGAL] {label}: proporsi Status='{target_status}' = {actual_ratio:.3%}, "
            f"melenceng dari target {target_weight:.0%} lebih dari toleransi {tolerance:.0%}"
        )
        ok = False
    else:
        print(
            f"  [OK]    {label}: proporsi Status='{target_status}' = {actual_ratio:.3%} "
            f"(target {target_weight:.0%})"
        )
    seqs = [r["Seq"] for r in rows]
    expected = list(range(1, n + 1))
    if seqs != expected:
        n_dup = n - len(set(seqs))
        print(
            f"  [GAGAL] {label}: kolom Seq tidak berurutan 1..{n} "
            f"(duplikat: {n_dup}, min: {min(seqs)}, max: {max(seqs)})"
        )
        ok = False
    else:
        print(f"  [OK]    {label}: Seq berurutan 1..{n} tanpa celah/duplikat")

    return ok


# ---------------------------------------------------------------------------
# Simpan ke CSV
# ---------------------------------------------------------------------------

def save_csv(rows, path: str):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    print("=== Generate dataset TRAIN (dipakai untuk RM1 & RM2) ===")
    for scale in TRAIN_SCALES:
        print(f"\nGenerating scale={scale} ...")
        rows = generate_dataset(scale, seed=SEED)
        validate_dataset(rows, label=f"scale={scale}")
        out_path = os.path.join(OUTPUT_DIR_TRAIN, f"dataset_{scale}.csv")
        save_csv(rows, out_path)
        print(f"  -> disimpan ke {out_path}")

    print("\n=== Generate dataset HOLDOUT (JANGAN dipakai untuk RM1/RM2) ===")
    for scale in HOLDOUT_SCALES:
        print(f"\nGenerating scale={scale} (HOLDOUT) ...")
        rows = generate_dataset(scale, seed=SEED)
        validate_dataset(rows, label=f"scale={scale} (holdout)")
        out_path = os.path.join(OUTPUT_DIR_HOLDOUT, f"dataset_{scale}.csv")
        save_csv(rows, out_path)
        print(f"  -> disimpan ke {out_path}")

    print("\nSelesai. Total file: ", len(TRAIN_SCALES) + len(HOLDOUT_SCALES))


if __name__ == "__main__":
    main()
