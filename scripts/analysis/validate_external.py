"""Validasi lintas-dataset decision framework (UCI Online Retail II & Olist).

Input : sesi utama eksternal, sesi rerun, data sintetis (untuk melatih aturan).
Output: tabel median per kombinasi, uji kontrol antar sesi, metrik aturan
        (akurasi, FNR, FPR) untuk aturan mekanistik vs aturan berbasis volume.
"""
import pandas as pd, numpy as np
from scipy.stats import mannwhitneyu

MAIN   = "ext_20261016_025842.csv"
RERUN  = "ext_20261017_014519.csv"
SYNTH  = "raw_20260912_024306.csv"
TAINTED = {("S1","SQL","OLIST10k"), ("S1","SQL","OLIST5k"),
           ("S2","SQL","UCI5k"),   ("S2","SQL","OLIST10k")}   # anomali 04:56-05:40
CONTROL = ("S1","SQL","UCI5k")
SLA, LIMIT = 2000, 2000                                        # ms, Data Row Limit

# jumlah baris sebenarnya (selectivity_report.csv)
TRUE = {"UCI5k":1985,"UCI10k":3912,"UCI50k":19547,"UCI100k":39359,
        "OLIST5k":1388,"OLIST10k":2800,"OLIST50k":13953,"OLIST100k":27886}
V    = {f"{d}{s}": n for d in ("UCI","OLIST")
        for s, n in (("5k",5000),("10k",10000),("50k",50000),("100k",100000))}
# selektivitas populasi: diestimasi dari skala terbesar; ganti dengan nilai
# s_pop di selectivity_report.csv bila ada
SEL  = {"UCI": TRUE["UCI100k"]/100000, "OLIST": TRUE["OLIST100k"]/100000}

def load(path):
    d = pd.read_csv(path)
    return d[(d.phase=="measure") & d.raw_status.str.startswith("DONE")].copy()

# ---------- 1. gabung sesi ----------
main, rerun = load(MAIN), load(RERUN)
key = lambda d: list(zip(d.pattern, d.source, d.scale))
main_clean = main[[k not in TAINTED for k in key(main)]]
rerun_use  = rerun[[k in TAINTED for k in key(rerun)]]
ext = pd.concat([main_clean.assign(session="utama"),
                 rerun_use.assign(session="rerun")], ignore_index=True)
n_combo = ext.groupby(["pattern","source","scale"]).ngroups
print(f"Kombinasi final: {n_combo} (harus 40), run measure: {len(ext)} (harus 200)")

# ---------- 2. uji kontrol antar sesi ----------
c1 = main[[k == CONTROL for k in key(main)]].roundtrip_ms
c2 = rerun[[k == CONTROL for k in key(rerun)]].roundtrip_ms
u, p = mannwhitneyu(c1, c2, alternative="two-sided")
print(f"\nKontrol {CONTROL}: median utama={c1.median():.0f} ms, rerun={c2.median():.0f} ms, "
      f"Mann-Whitney U={u:.1f}, p={p:.3f} -> {'sebanding' if p>=0.05 else 'BEDA'}")

# ---------- 3. ringkasan ----------
s = (ext.groupby(["pattern","source","scale"])
        .agg(rows=("rows","median"), med=("roundtrip_ms","median"),
             q1=("roundtrip_ms", lambda x: x.quantile(.25)),
             q3=("roundtrip_ms", lambda x: x.quantile(.75)),
             cv=("roundtrip_ms", lambda x: x.std()/x.mean()))
        .reset_index())
s["true_rows"] = s.scale.map(TRUE)
s["completeness"] = (s.rows / s.true_rows).round(3)
s.loc[s.pattern=="S4","completeness"] = (s.rows/s.true_rows).round(3)  # COUNT agregat
order = {k:i for i,k in enumerate(["UCI5k","UCI10k","UCI50k","UCI100k",
                                   "OLIST5k","OLIST10k","OLIST50k","OLIST100k"])}
s = s.sort_values(["pattern","scale","source"], key=lambda c: c.map(order) if c.name=="scale" else c)
print("\nRingkasan per kombinasi:")
print(s.to_string(index=False, float_format=lambda x: f"{x:.3f}" if x<10 else f"{x:.0f}"))
s.to_csv("ext_summary.csv", index=False)

# ---------- 4. ground truth eksternal ----------
# S1 'aman' bila lengkap DAN median < SLA (per sumber data)
cells = []
for (src, sc), r in s[s.pattern=="S1"].set_index(["source","scale"]).iterrows():
    truth_safe = (r.completeness >= 0.999) and (r.med < SLA)
    cells.append(dict(source=src, scale=sc, dataset=sc.rstrip("k0123456789") if False else ("UCI" if sc.startswith("UCI") else "OLIST"),
                      V=V[sc], true_rows=TRUE[sc], s1_rows=r.rows, med=r.med, truth_safe=truth_safe))
cells = pd.DataFrame(cells)

# ---------- 5. aturan dilatih dari data sintetis ----------
syn = load(SYNTH)
EXP_SYN = {"5k":984,"10k":1925,"25k":4962,"50k":10040,"100k":20056}
N_SYN   = {"5k":5000,"10k":10000,"25k":25000,"50k":50000,"100k":100000}
ss = syn[(syn.pattern=="S1") & (syn.source=="DV")].groupby("scale").agg(
        med=("roundtrip_ms","median"), rows=("rows","median"))
ss["comp"] = ss.rows / ss.index.map(EXP_SYN)
train = sorted(["5k","10k","50k","100k"], key=N_SYN.get)

# (a) latency breakpoint: 2 segmen, RSS minimum, min 2 titik
y = np.array([ss.loc[t,"med"] for t in train]); best = (np.inf, None)
for k in range(2, len(y)-1):
    rss = ((y[:k]-y[:k].mean())**2).sum() + ((y[k:]-y[k:].mean())**2).sum()
    if rss < best[0]: best = (rss, N_SYN[train[k]])
T_lat = best[1] or max(N_SYN.values())
# (b) empiris: skala terbesar tempat S1 lengkap & < SLA
T_emp = max(N_SYN[t] for t in train if ss.loc[t,"comp"] >= 0.999 and ss.loc[t,"med"] < SLA)

rules = {
    f"latency breakpoint (V < {T_lat})": lambda r: r.V <  T_lat,
    f"empiris volume (V <= {T_emp})":    lambda r: r.V <= T_emp,
    "mekanistik (V x s <= 2000)":        lambda r: r.V * SEL[r.dataset] <= LIMIT,
}

def metrics(df):
    acc = (df.pred_safe == df.truth_safe).mean()
    pos = df[~df.truth_safe]; neg = df[df.truth_safe]          # positif = harus pindah dari S1
    fnr = (pos.pred_safe).mean() if len(pos) else np.nan       # bilang aman padahal terpotong
    fpr = (~neg.pred_safe).mean() if len(neg) else np.nan      # bilang pindah padahal aman
    return acc, fnr, fpr, len(df), len(pos), len(neg)

print(f"\nSelektivitas dipakai: UCI={SEL['UCI']:.4f}, OLIST={SEL['OLIST']:.4f}")
print("\nValidasi lintas-dataset (16 sel = 2 dataset x 4 skala x 2 sumber):")
out = []
for name, f in rules.items():
    cells["pred_safe"] = cells.apply(f, axis=1)
    acc, fnr, fpr, n, npos, nneg = metrics(cells)
    out.append((name, acc, fnr, fpr))
    print(f"  {name:34s} acc={acc:.3f}  FNR={fnr:.3f}  FPR={fpr:.3f}  (n={n}, pos={npos}, neg={nneg})")
    wrong = cells[cells.pred_safe != cells.truth_safe]
    for r in wrong.itertuples():
        print(f"      salah: {r.source} {r.scale}  truth_safe={r.truth_safe}  pred_safe={r.pred_safe}  "
              f"S1 rows={r.s1_rows:.0f}/{r.true_rows}")
pd.DataFrame(out, columns=["rule","accuracy","FNR","FPR"]).to_csv("ext_rule_validation.csv", index=False)
cells.drop(columns="pred_safe").to_csv("ext_ground_truth.csv", index=False)
