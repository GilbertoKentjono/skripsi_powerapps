"""Evaluasi uji tambahan (subbab 4.7.1): sel dekat batas dan variasi selektivitas.

Jalankan dari data/final:
    python ../../scripts/analysis/evaluate_boundary.py

Input : bnd_20261111_233618.csv (hasil run), boundary_expected.csv (prediksi beku)
Output: bnd_summary.csv (Tabel 4.12), bnd_confusion_f1.csv (baris uji tambahan Tabel 4.11)
"""
import pandas as pd

SLA_MS = 2000
d = pd.read_csv("bnd_20261111_233618.csv")
d = d[(d.phase == "measure") & d.raw_status.str.startswith("DONE")]
e = pd.read_csv("boundary_expected.csv").set_index("cell")

g = (d.groupby(["source", "scale"])
       .agg(rows=("rows", "first"), n_unique_rows=("rows", "nunique"),
            median_ms=("roundtrip_ms", "median"), max_ms=("roundtrip_ms", "max"))
       .reset_index())

out = []
for _, r in g.iterrows():
    x = e.loc[r.scale]
    vs = x.V * x.s_est
    complete = r.rows / x.true_rows >= 0.999
    out.append(dict(
        source=r.source, cell=r.scale, V=x.V, s_est=x.s_est, true_rows=x.true_rows,
        pred_rows=round(min(vs, 2000)), rows=int(r.rows), n_unique_rows=r.n_unique_rows,
        match_min_true_2000=int(r.rows) == min(x.true_rows, 2000),
        pred_error_pct=round(abs(min(vs, 2000) - r.rows) / r.rows * 100, 2),
        completeness=round(r.rows / x.true_rows, 3), median_ms=r.median_ms, max_ms=r.max_ms,
        actual_unsafe=not (complete and r.median_ms < SLA_MS),
        mechanistic_unsafe=vs > 2000, mechanistic_k09_unsafe=vs > 1800,
        volume_unsafe=x.V > 10000, latency_unsafe=x.V > 50000))
s = pd.DataFrame(out).sort_values(["source", "V", "s_est"])
s.to_csv("bnd_summary.csv", index=False)

rows = []
for rule in ["latency_unsafe", "volume_unsafe", "mechanistic_unsafe", "mechanistic_k09_unsafe"]:
    p, a = s[rule], s.actual_unsafe
    tp, fn, fp, tn = (p & a).sum(), (~p & a).sum(), (p & ~a).sum(), (~p & ~a).sum()
    f1 = 2 * tp / (2 * tp + fp + fn) if tp else 0.0
    rows.append(dict(rule=rule, TP=tp, FN=fn, FP=fp, TN=tn, n=len(s),
                     accuracy=round((tp + tn) / len(s), 3), F1=round(f1, 3),
                     FNR=round(fn / (tp + fn), 3), FPR=round(fp / (fp + tn), 3) if fp + tn else None))
pd.DataFrame(rows).to_csv("bnd_confusion_f1.csv", index=False)
print(pd.DataFrame(rows).to_string(index=False))
print("mean pred error %:", s.pred_error_pct.mean().round(2), "| max:", s.pred_error_pct.max())
