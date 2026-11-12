"""
analyze_results.py

Analisis hasil pengukuran delegation query Power Apps.
Referensi: Proposal Skripsi bagian 9.3 dan 9.4.

Cara pakai:
    python analyze_results.py results/raw_20260912_024306.csv

Output (folder analysis/):
    summary.csv             ringkasan per kombinasi
    breakpoints.csv         segmented regression + titik lampau SLA
    stat_kruskal.csv        uji Kruskal-Wallis antar pola
    stat_dunn_<skala>.csv   post-hoc Dunn per skala
    comparison_rm2.csv      komparasi Dataverse vs Azure SQL
    fig_scalability.png     kurva scalability
    fig_completeness.png    kurva retrieval completeness
"""

import os
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import ruptures as rpt
import scikit_posthocs as sp
from scipy import stats

SLA_MS = 2000
ALPHA = 0.05
CV_THRESHOLD = 20.0

SCALE_ORDER = ["5k", "10k", "25k", "50k", "100k"]
SCALE_N = {"5k": 5_000, "10k": 10_000, "25k": 25_000, "50k": 50_000, "100k": 100_000}

# Jumlah baris yang SEHARUSNYA memenuhi filter (hasil validasi dataset, Tabel 3.3)
EXPECTED_MATCH = {"5k": 984, "10k": 1925, "25k": 4962, "50k": 10040, "100k": 20056}

OUT_DIR = "analysis"


def load(path):
    df = pd.read_csv(path)
    df = df[df.phase == "measure"].copy()
    df = df[df.raw_status.str.startswith("DONE")].copy()
    df["roundtrip_ms"] = pd.to_numeric(df.roundtrip_ms, errors="coerce")
    df["rows"] = pd.to_numeric(df["rows"], errors="coerce")
    df["fn_ms"] = pd.to_numeric(df.fn_ms, errors="coerce")
    df = df.dropna(subset=["roundtrip_ms"])
    df["n_total"] = df.scale.map(SCALE_N)
    df["expected"] = df.scale.map(EXPECTED_MATCH)
    return df


def summarise(df):
    g = df.groupby(["pattern", "source", "scale"], as_index=False).agg(
        n_run=("roundtrip_ms", "count"),
        rows=("rows", "median"),
        expected=("expected", "first"),
        mean_ms=("roundtrip_ms", "mean"),
        median_ms=("roundtrip_ms", "median"),
        sd_ms=("roundtrip_ms", "std"),
        min_ms=("roundtrip_ms", "min"),
        max_ms=("roundtrip_ms", "max"),
        fn_ms=("fn_ms", "median"),
    )
    g["cv_pct"] = (g.sd_ms / g.mean_ms * 100).round(1)
    g["cv_flag"] = np.where(g.cv_pct > CV_THRESHOLD, "di atas ambang", "ok")
    g["completeness_pct"] = (g["rows"] / g.expected * 100).round(1)
    g["throughput_rps"] = (g["rows"] / (g.median_ms / 1000)).round(1)
    g["overhead_ms"] = (g.median_ms - g.fn_ms).round(1)
    g["lewat_sla"] = np.where(g.median_ms > SLA_MS, "ya", "tidak")

    g["_o"] = g.scale.map({s: i for i, s in enumerate(SCALE_ORDER)})
    g = g.sort_values(["pattern", "source", "_o"]).drop(columns="_o")
    for c in ["mean_ms", "median_ms", "sd_ms", "min_ms", "max_ms"]:
        g[c] = g[c].round(1)
    return g


def find_breakpoints(summary):
    out = []
    for (pat, src), grp in summary.groupby(["pattern", "source"]):
        grp = grp.copy()
        grp["_o"] = grp.scale.map({s: i for i, s in enumerate(SCALE_ORDER)})
        grp = grp.sort_values("_o")
        y = grp.median_ms.to_numpy(dtype=float)

        def bic_of(idx):
            """BIC = n*ln(RSS/n) + k*ln(n); idx = batas akhir tiap segmen."""
            rss, start = 0.0, 0
            for end in idx:
                seg = y[start:end]
                rss += float(((seg - seg.mean()) ** 2).sum())
                start = end
            n = len(y)
            k = len(idx)
            return n * np.log(max(rss, 1e-9) / n) + k * np.log(n)

        bkp_scale, n_bkps_best, bic_best = None, 0, None
        if len(y) >= 4:
            signal = y.reshape(-1, 1)
            # Model pembanding: tanpa breakpoint sama sekali
            bic_best = bic_of([len(y)])
            # min_size=2 agar tiap segmen minimal 2 titik
            max_bkps = max(len(y) // 2 - 1, 1)
            for n_bkps in range(1, max_bkps + 1):
                try:
                    idx = rpt.Dynp(model="l2", min_size=2, jump=1).fit(signal).predict(
                        n_bkps=n_bkps
                    )
                except Exception:
                    continue
                bic = bic_of(idx)
                if bic < bic_best:
                    bic_best, n_bkps_best = bic, n_bkps
                    first = idx[0]
                    bkp_scale = SCALE_ORDER[first] if first < len(SCALE_ORDER) else None

        sla_scale = None
        for _, r in grp.iterrows():
            if r.median_ms > SLA_MS:
                sla_scale = r.scale
                break

        out.append(dict(
            pattern=pat, source=src, n_titik_skala=len(y),
            breakpoint_skala=bkp_scale, n_breakpoint=n_bkps_best,
            bic=None if bic_best is None else round(bic_best, 2),
            skala_lampau_sla=sla_scale if sla_scale else "tidak dalam rentang uji",
            median_terkecil=round(float(y.min()), 1),
            median_terbesar=round(float(y.max()), 1),
        ))
    return pd.DataFrame(out)


def kruskal_tests(df):
    rows, dunn_tables = [], {}
    for (src, scale), grp in df.groupby(["source", "scale"]):
        groups = [g.roundtrip_ms.to_numpy() for _, g in grp.groupby("pattern")]
        names = [p for p, _ in grp.groupby("pattern")]
        if len(groups) < 2:
            continue
        h, p = stats.kruskal(*groups)
        n = sum(len(g) for g in groups)
        eps2 = (h - len(groups) + 1) / (n - len(groups)) if n > len(groups) else np.nan
        rows.append(dict(
            source=src, scale=scale, pola_diuji=", ".join(names), n_total=n,
            H=round(float(h), 3), p_value=float(p),
            signifikan="ya" if p < ALPHA else "tidak",
            epsilon_squared=round(float(eps2), 3),
        ))
        if p < ALPHA and len(groups) > 2:
            dunn = sp.posthoc_dunn(
                grp, val_col="roundtrip_ms", group_col="pattern", p_adjust="holm"
            )
            dunn_tables[f"{src}_{scale}"] = dunn.round(4)

    res = pd.DataFrame(rows)
    if not res.empty:
        res["_o"] = res.scale.map({s: i for i, s in enumerate(SCALE_ORDER)})
        res = res.sort_values(["source", "_o"]).drop(columns="_o")
    return res, dunn_tables


def compare_sources(df):
    rows = []
    for (pat, scale), grp in df.groupby(["pattern", "scale"]):
        dv = grp[grp.source == "DV"].roundtrip_ms.to_numpy()
        sql = grp[grp.source == "SQL"].roundtrip_ms.to_numpy()
        if len(dv) == 0 or len(sql) == 0:
            continue
        u, p = stats.mannwhitneyu(dv, sql, alternative="two-sided")
        med_dv, med_sql = float(np.median(dv)), float(np.median(sql))
        rows.append(dict(
            pattern=pat, scale=scale,
            median_DV_ms=round(med_dv, 1), median_SQL_ms=round(med_sql, 1),
            delta_ms=round(med_dv - med_sql, 1),
            rasio_DV_per_SQL=round(med_dv / med_sql, 2) if med_sql else np.nan,
            lebih_cepat="Dataverse" if med_dv < med_sql else "Azure SQL",
            U=float(u), p_value=float(p),
            signifikan="ya" if p < ALPHA else "tidak",
        ))
    res = pd.DataFrame(rows)
    if not res.empty:
        res["_o"] = res.scale.map({s: i for i, s in enumerate(SCALE_ORDER)})
        res = res.sort_values(["pattern", "_o"]).drop(columns="_o")
    return res


def plot_scalability(summary, path):
    fig, ax = plt.subplots(figsize=(9, 5.5))
    markers = {"DV": "o", "SQL": "s"}
    colors = {"S1": "#1f77b4", "S2": "#ff7f0e", "S3": "#2ca02c", "S4": "#d62728"}
    for (pat, src), grp in summary.groupby(["pattern", "source"]):
        grp = grp.copy()
        grp["_o"] = grp.scale.map({s: i for i, s in enumerate(SCALE_ORDER)})
        grp = grp.sort_values("_o")
        ax.plot(grp.scale.map(SCALE_N), grp.median_ms,
                marker=markers[src], linestyle="-" if src == "DV" else "--",
                color=colors.get(pat, "gray"),
                label=f"{pat} - {'Dataverse' if src == 'DV' else 'Azure SQL'}")
    ax.axhline(SLA_MS, color="red", linestyle=":", linewidth=1.2)
    ax.text(5200, SLA_MS * 1.08, "Ambang SLA 2 detik", color="red", fontsize=9)
    ax.set_xscale("log"); ax.set_yscale("log")
    ax.set_xticks(list(SCALE_N.values())); ax.set_xticklabels(SCALE_ORDER)
    ax.set_xlabel("Volume data (record)")
    ax.set_ylabel("Median execution time (ms, skala log)")
    ax.set_title("Kurva Scalability per Pola dan Sumber Data")
    ax.grid(True, which="both", alpha=0.3)
    ax.legend(fontsize=8, ncol=2)
    fig.tight_layout(); fig.savefig(path, dpi=200); plt.close(fig)


def plot_completeness(summary, path):
    fig, ax = plt.subplots(figsize=(9, 5))
    markers = {"DV": "o", "SQL": "s"}
    colors = {"S1": "#1f77b4", "S2": "#ff7f0e", "S3": "#2ca02c", "S4": "#d62728"}
    for (pat, src), grp in summary.groupby(["pattern", "source"]):
        grp = grp.copy()
        grp["_o"] = grp.scale.map({s: i for i, s in enumerate(SCALE_ORDER)})
        grp = grp.sort_values("_o")
        ax.plot(grp.scale.map(SCALE_N), grp.completeness_pct,
                marker=markers[src], linestyle="-" if src == "DV" else "--",
                color=colors.get(pat, "gray"),
                label=f"{pat} - {'Dataverse' if src == 'DV' else 'Azure SQL'}")
    ax.set_xscale("log")
    ax.set_xticks(list(SCALE_N.values())); ax.set_xticklabels(SCALE_ORDER)
    ax.set_ylim(0, 110)
    ax.set_xlabel("Volume data (record)")
    ax.set_ylabel("Retrieval completeness (%)")
    ax.set_title("Retrieval Completeness per Pola dan Sumber Data")
    ax.grid(True, alpha=0.3); ax.legend(fontsize=8, ncol=2)
    fig.tight_layout(); fig.savefig(path, dpi=200); plt.close(fig)


def main():
    if len(sys.argv) < 2:
        print("Cara pakai: python analyze_results.py <path_ke_raw.csv>")
        sys.exit(1)

    path = sys.argv[1]
    os.makedirs(OUT_DIR, exist_ok=True)

    df = load(path)
    print(f"Data dimuat: {len(df)} measurement run, "
          f"{df.groupby(['pattern','source','scale']).ngroups} kombinasi\n")

    summary = summarise(df)
    summary.to_csv(os.path.join(OUT_DIR, "summary.csv"), index=False)
    print("=== RINGKASAN PER KOMBINASI ===")
    print(summary[["pattern", "source", "scale", "rows", "median_ms", "cv_pct",
                   "completeness_pct", "throughput_rps", "lewat_sla"]]
          .to_string(index=False))
    n_flag = (summary.cv_pct > CV_THRESHOLD).sum()
    print(f"\nKombinasi dengan CV di atas {CV_THRESHOLD}%: {n_flag} dari {len(summary)}")

    bkp = find_breakpoints(summary)
    bkp.to_csv(os.path.join(OUT_DIR, "breakpoints.csv"), index=False)
    print("\n=== BREAKPOINT DAN AMBANG SLA ===")
    print(bkp.to_string(index=False))

    kw, dunn_tables = kruskal_tests(df)
    kw.to_csv(os.path.join(OUT_DIR, "stat_kruskal.csv"), index=False)
    print("\n=== KRUSKAL-WALLIS ANTAR POLA ===")
    print(kw.to_string(index=False))
    for key, tbl in dunn_tables.items():
        tbl.to_csv(os.path.join(OUT_DIR, f"stat_dunn_{key}.csv"))
    if dunn_tables:
        print(f"\nTabel Dunn post-hoc disimpan: {len(dunn_tables)} berkas")

    cmp2 = compare_sources(df)
    cmp2.to_csv(os.path.join(OUT_DIR, "comparison_rm2.csv"), index=False)
    print("\n=== KOMPARASI SUMBER DATA (RM2) ===")
    print(cmp2.to_string(index=False))

    plot_scalability(summary, os.path.join(OUT_DIR, "fig_scalability.png"))
    plot_completeness(summary, os.path.join(OUT_DIR, "fig_completeness.png"))
    print(f"\nSeluruh keluaran tersimpan di folder '{OUT_DIR}/'")


if __name__ == "__main__":
    main()