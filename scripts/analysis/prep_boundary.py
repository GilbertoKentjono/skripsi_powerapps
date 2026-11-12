"""Siapkan eksperimen tambahan revisi: sel dekat batas dan variasi selektivitas.

Jalankan dari folder Skripsi (root repo):
    python scripts/analysis/prep_boundary.py data/holdout/dataset_25000.csv data/train/dataset_10000.csv

Output:
  - ambang JumlahTransaksi untuk selektivitas 5/10/15/20/25/50% pada tabel 10k
  - jumlah baris sebenarnya (expected) setiap sel uji baru
  - selektivitas estimasi dari sampel 5.000 baris pertama (dipakai oleh model, dibekukan sebelum run)
  - boundary_expected.csv
"""
import sys, pandas as pd

d25 = pd.read_csv(sys.argv[1]); d10 = pd.read_csv(sys.argv[2])
rows = []

# --- A. sel dekat batas: V diemulasikan dengan Seq <= V pada tabel 25k, predikat Status = Selesai
s_est_status = (d25[d25.Seq <= 5000].Status == "Selesai").mean()
for V in (9000, 11000, 12000, 15000, 20000):
    true = int(((d25.Seq <= V) & (d25.Status == "Selesai")).sum())
    rows.append(dict(cell=f"{V//1000}k", V=V, predicate='Status = "Selesai" && Seq <= %d' % V,
                     s_est=round(s_est_status, 4), pred_rows=round(min(V * s_est_status, 2000)),
                     true_rows=true, model_safe=V * s_est_status <= 2000))

# --- B. variasi selektivitas pada V = 10.000, predikat JumlahTransaksi >= T
J = d10.JumlahTransaksi.sort_values(ascending=False).reset_index(drop=True)
# JumlahTransaksi diskret (~5% per nilai), sehingga 5% dan 10% sempat menghasilkan T yang sama.
# T untuk 5% dikoreksi manual menjadi 20 (488 baris) sebelum prediksi dibekukan.
T_OVERRIDE = {5: 20}
for pct in (5, 10, 15, 20, 25, 50):
    target = int(10000 * pct / 100)
    T = T_OVERRIDE.get(pct, J.iloc[target - 1])  # nilai ke-target dari atas
    true = int((d10.JumlahTransaksi >= T).sum())
    s_est = (d10[d10.Seq <= 5000].JumlahTransaksi >= T).mean()
    rows.append(dict(cell=f"10k_s{pct:02d}", V=10000, predicate=f"JumlahTransaksi >= {T}",
                     s_est=round(s_est, 4), pred_rows=round(min(10000 * s_est, 2000)),
                     true_rows=true, model_safe=10000 * s_est <= 2000))

out = pd.DataFrame(rows)
pd.set_option("display.width", 200)
print(out.to_string(index=False))
out.to_csv("boundary_expected.csv", index=False)
print("\nCatatan: kalau true_rows sebuah sel s jauh dari target (karena nilai kembar), ganti persentase atau terima apa adanya.")
