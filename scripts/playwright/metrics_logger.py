"""
metrics_logger.py

Format logging hasil pengujian delegation query (S1-S4).
Referensi: Proposal Skripsi bagian 5.4 & 9.3 (protokol pengujian, CV).

Modul ini CUMA soal menyimpan & menghitung dari data yang SUDAH ada di
tangan (misal hasil pyodbc / azure-monitor-query yang nanti kamu ambil).
Modul ini sendiri tidak konek ke Azure sama sekali -- makanya bisa
ditest sepenuhnya pakai data dummy, seperti di bagian bawah file ini.

Cara pakai singkat:

    from metrics_logger import TestResult, ResultsLogger

    logger = ResultsLogger("results/raw_results.csv")

    logger.log_result(TestResult(
        pola="S1",
        sumber_data="Dataverse",
        skala=5000,
        run_ke=1,
        duration_ms=842.5,
    ))

    cv = logger.compute_cv(pola="S1", sumber_data="Dataverse", skala=5000)
    if logger.needs_rerun(pola="S1", sumber_data="Dataverse", skala=5000):
        print("CV > 20%, kombinasi ini perlu diulang")
"""

import csv
import os
import statistics
from dataclasses import dataclass, asdict, fields
from datetime import datetime, timezone
from typing import Optional


# ---------------------------------------------------------------------------
# Struktur satu baris hasil
# ---------------------------------------------------------------------------

@dataclass
class TestResult:
    pola: str            # "S1" | "S2" | "S3" | "S4"
    sumber_data: str     # "Dataverse" | "AzureSQL"
    skala: int           # 5000, 10000, 25000, 50000, 100000
    run_ke: int          # 1-5 (measurement run; warm-up TIDAK dicatat di sini)
    duration_ms: float
    timestamp: str = ""              # diisi otomatis kalau kosong
    retrieval_rate: Optional[float] = None   # cuma relevan untuk S2 & S3
    function_execution_ms: Optional[float] = None  # cuma diisi untuk S4
    notes: str = ""

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now(timezone.utc).isoformat()


CSV_FIELDNAMES = [f.name for f in fields(TestResult)]


# ---------------------------------------------------------------------------
# Logger
# ---------------------------------------------------------------------------

class ResultsLogger:
    """
    Simpan/ambil TestResult dari satu file CSV.
    Append-only: tiap log_result() nambah 1 baris ke file.
    """

    def __init__(self, csv_path: str):
        self.csv_path = csv_path
        os.makedirs(os.path.dirname(csv_path) or ".", exist_ok=True)
        if not os.path.exists(self.csv_path):
            with open(self.csv_path, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=CSV_FIELDNAMES)
                writer.writeheader()

    def log_result(self, result: TestResult) -> None:
        with open(self.csv_path, "a", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=CSV_FIELDNAMES)
            writer.writerow(asdict(result))

    def read_all(self) -> list:
        with open(self.csv_path, newline="", encoding="utf-8") as f:
            return list(csv.DictReader(f))

    def read_combo(self, pola: str, sumber_data: str, skala: int) -> list:
        """Ambil semua baris untuk satu kombinasi pola x sumber_data x skala."""
        rows = self.read_all()
        return [
            r for r in rows
            if r["pola"] == pola
            and r["sumber_data"] == sumber_data
            and int(r["skala"]) == skala
        ]

    def compute_cv(self, pola: str, sumber_data: str, skala: int) -> Optional[float]:
        """
        CV = std deviasi / rata-rata, dari duration_ms tiap run pada kombinasi ini.
        Return None kalau datanya kurang dari 2 baris (CV tidak bermakna).
        """
        rows = self.read_combo(pola, sumber_data, skala)
        durations = [float(r["duration_ms"]) for r in rows]
        if len(durations) < 2:
            return None
        mean = statistics.mean(durations)
        if mean == 0:
            return None
        std = statistics.stdev(durations)
        return std / mean

    def needs_rerun(self, pola: str, sumber_data: str, skala: int, threshold: float = 0.20) -> bool:
        """
        True kalau CV kombinasi ini > threshold (default 20%, sesuai proposal 9.3),
        atau kalau jumlah run belum genap 5 (belum lengkap).
        """
        rows = self.read_combo(pola, sumber_data, skala)
        if len(rows) < 5:
            return True
        cv = self.compute_cv(pola, sumber_data, skala)
        return cv is not None and cv > threshold

    def summary(self) -> dict:
        """
        Ringkasan cepat: berapa kombinasi yang sudah lengkap (>=5 run) dan
        berapa yang CV-nya masih di atas threshold.
        """
        rows = self.read_all()
        combos = set((r["pola"], r["sumber_data"], int(r["skala"])) for r in rows)
        result = {"total_kombinasi_ada_data": len(combos), "belum_lengkap_atau_cv_tinggi": []}
        for pola, sumber_data, skala in sorted(combos):
            if self.needs_rerun(pola, sumber_data, skala):
                result["belum_lengkap_atau_cv_tinggi"].append((pola, sumber_data, skala))
        return result


# ---------------------------------------------------------------------------
# Test lokal pakai data dummy -- jalankan langsung: python metrics_logger.py
# Tidak butuh koneksi Azure sama sekali.
# ---------------------------------------------------------------------------

def _run_local_test():
    import random
    import tempfile

    print("=== Test lokal metrics_logger.py (data dummy) ===\n")

    tmp_path = os.path.join(tempfile.gettempdir(), "test_results.csv")
    if os.path.exists(tmp_path):
        os.remove(tmp_path)

    logger = ResultsLogger(tmp_path)

    # Kasus 1: kombinasi dengan duration stabil -> CV harus rendah, tidak perlu rerun
    random.seed(1)
    stable_durations = [800, 820, 810, 805, 815]
    for i, d in enumerate(stable_durations, start=1):
        logger.log_result(TestResult(
            pola="S1", sumber_data="Dataverse", skala=5000,
            run_ke=i, duration_ms=d,
        ))
    cv_stable = logger.compute_cv("S1", "Dataverse", 5000)
    print(f"Kombinasi stabil (S1/Dataverse/5000): CV = {cv_stable:.3%}")
    assert cv_stable < 0.20, "CV seharusnya rendah untuk data stabil"
    assert not logger.needs_rerun("S1", "Dataverse", 5000), "Seharusnya TIDAK perlu rerun"
    print("  [OK] CV rendah, needs_rerun() = False, sesuai ekspektasi\n")

    # Kasus 2: kombinasi dengan duration sangat bervariasi -> CV tinggi, perlu rerun
    volatile_durations = [500, 1800, 600, 2200, 700]
    for i, d in enumerate(volatile_durations, start=1):
        logger.log_result(TestResult(
            pola="S2", sumber_data="AzureSQL", skala=5000,
            run_ke=i, duration_ms=d, retrieval_rate=0.35,
        ))
    cv_volatile = logger.compute_cv("S2", "AzureSQL", 5000)
    print(f"Kombinasi volatile (S2/AzureSQL/5000): CV = {cv_volatile:.3%}")
    assert cv_volatile > 0.20, "CV seharusnya tinggi untuk data volatile"
    assert logger.needs_rerun("S2", "AzureSQL", 5000), "Seharusnya PERLU rerun"
    print("  [OK] CV tinggi, needs_rerun() = True, sesuai ekspektasi\n")

    # Kasus 3: kombinasi belum lengkap (baru 2 run dari 5)
    for i, d in enumerate([900, 910], start=1):
        logger.log_result(TestResult(
            pola="S4", sumber_data="Dataverse", skala=10000,
            run_ke=i, duration_ms=d, function_execution_ms=d * 0.7,
        ))
    print("Kombinasi belum lengkap (S4/Dataverse/10000): baru 2 dari 5 run")
    assert logger.needs_rerun("S4", "Dataverse", 10000), "Seharusnya PERLU rerun (belum lengkap)"
    print("  [OK] needs_rerun() = True karena belum genap 5 run\n")

    # Cek summary()
    summary = logger.summary()
    print("Summary:", summary)
    assert len(summary["belum_lengkap_atau_cv_tinggi"]) == 2, "Harusnya ada 2 kombinasi bermasalah"
    print("  [OK] summary() mendeteksi 2 kombinasi yang butuh perhatian\n")

    print(f"Semua test lulus. File CSV dummy ada di: {tmp_path}")
    print("(File ini boleh dihapus, cuma buat verifikasi logic di atas benar)")


if __name__ == "__main__":
    _run_local_test()
