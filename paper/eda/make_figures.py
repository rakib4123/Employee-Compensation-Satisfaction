"""Generate the four EDA figures for the compensation-satisfaction proposal.

Design rules applied (see the dataviz skill):
  * form first  - magnitude -> bar, relationship -> scatter, polarity -> diverging heatmap
  * color by job - single hue for one series, categorical slots 1-2 for two groups,
    blue<->red with a NEUTRAL GRAY midpoint for the correlation matrix (never a rainbow),
    status palette for the data-quality panel
  * palette validated with scripts/validate_palette.js (all checks pass, light mode,
    --pairs all for the scatter's two slots)
  * secondary encoding everywhere colour carries meaning, because IEEE papers get
    printed in greyscale: marker shape in the scatter, hatching + text labels in the
    quality panel, printed values in the heatmap cells
  * text wears text tokens, never the series colour

Usage:  venv/bin/python paper/eda/make_figures.py
"""

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.colors import LinearSegmentedColormap
from matplotlib.patches import Patch
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "survey_analysis.csv"

# --- palette (validated; see references/palette.md) --------------------------
SERIES_1 = "#2a78d6"   # categorical slot 1, blue
SERIES_2 = "#eb6834"   # categorical slot 2, orange
SEQ_MID = "#5598e7"    # blue ramp step 350
DIVERGING_NEG = "#d03b3b"
DIVERGING_MID = "#f0efec"   # neutral gray - NOT a hue
DIVERGING_POS = "#2a78d6"
STATUS = {"OK": "#0ca30c", "WARN": "#fab219", "FAIL": "#d03b3b"}
TEXT_PRIMARY = "#0b0b0b"
TEXT_SECONDARY = "#52514e"
GRID = "#d8d7d3"

plt.rcParams.update({
    "font.family": "serif",
    "font.serif": ["DejaVu Serif"],
    "font.size": 8,
    "axes.titlesize": 8.5,
    "axes.labelsize": 8,
    "xtick.labelsize": 7.5,
    "ytick.labelsize": 7.5,
    "legend.fontsize": 7,
    "axes.edgecolor": TEXT_SECONDARY,
    "axes.labelcolor": TEXT_PRIMARY,
    "text.color": TEXT_PRIMARY,
    "xtick.color": TEXT_SECONDARY,
    "ytick.color": TEXT_SECONDARY,
    "figure.dpi": 300,
    "savefig.dpi": 300,
    "savefig.bbox": "tight",
    "savefig.pad_inches": 0.02,
})

COL_W = 3.4   # IEEE single-column width, inches


def recessive_axes(ax, grid_axis="y"):
    """Grid and spines recede; the data is the loudest thing on the chart."""
    ax.set_axisbelow(True)
    ax.grid(axis=grid_axis, color=GRID, linewidth=0.6)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    for side in ("left", "bottom"):
        ax.spines[side].set_linewidth(0.7)


def fig_satisfaction(df):
    """Magnitude across five ordered categories -> bar. One series, so no legend:
    the title names it. Five bars is few enough to label every one."""
    counts = df["satisfaction"].value_counts().reindex([1, 2, 3, 4, 5], fill_value=0)
    labels = ["1\nVery\ndissat.", "2\nDissat.", "3\nNeutral", "4\nSatisfied", "5\nVery\nsatisfied"]

    fig, ax = plt.subplots(figsize=(COL_W, 2.2))
    bars = ax.bar(range(5), counts.values, color=SERIES_1, width=0.68, zorder=3)
    for rect, value in zip(bars, counts.values):
        pct = 100 * value / counts.sum()
        ax.text(rect.get_x() + rect.get_width() / 2, value + 0.12,
                f"{value}\n({pct:.0f}%)", ha="center", va="bottom",
                fontsize=6.8, color=TEXT_SECONDARY, linespacing=1.15)

    mean = df["satisfaction"].mean()
    ax.axvline(mean - 1, color=TEXT_PRIMARY, linestyle=(0, (4, 2)), linewidth=1.0, zorder=4)
    ax.text(mean - 0.92, counts.max() * 0.93, f"mean {mean:.2f}",
            fontsize=6.8, color=TEXT_PRIMARY, ha="left")

    ax.set_xticks(range(5))
    ax.set_xticklabels(labels, linespacing=1.2)
    ax.set_ylabel("Respondents")
    ax.set_ylim(0, counts.max() + 1.5)
    ax.set_yticks(range(0, counts.max() + 2, 2))
    recessive_axes(ax)
    fig.savefig(HERE / "fig1_satisfaction.pdf")
    plt.close(fig)
    return counts


def fig_salary_scatter(df):
    """Relationship between two measures -> scatter. Two groups, so a legend is
    present; marker SHAPE carries the split as well as colour, so the split
    survives greyscale printing."""
    d = df.dropna(subset=["salary", "satisfaction"]).copy()
    d["implausible"] = d["salary"] > 200_000
    ok, bad = d[~d["implausible"]], d[d["implausible"]]

    r_all = d["salary"].corr(d["satisfaction"])
    r_ok = ok["salary"].corr(ok["satisfaction"])

    fig, ax = plt.subplots(figsize=(COL_W, 2.35))
    ax.scatter(ok["salary"] / 1000, ok["satisfaction"], s=42, marker="o",
               facecolor=SERIES_1, edgecolor="white", linewidth=0.8, zorder=3,
               label=f"Plausible (n={len(ok)})")
    ax.scatter(bad["salary"] / 1000, bad["satisfaction"], s=52, marker="^",
               facecolor=SERIES_2, edgecolor="white", linewidth=0.8, zorder=3,
               label=f"Implausible (n={len(bad)})")

    # The threshold line needs no in-plot label: the legend already names the two
    # groups, and the caption states where the cut sits. Fewer marks, same reading.
    ax.axvline(200, color=TEXT_SECONDARY, linestyle=(0, (3, 3)), linewidth=0.8, zorder=2)

    # Two respondents share (50k, 3). Label the coincidence rather than jitter it,
    # so no point is drawn at a value nobody reported.
    dupes = (d.groupby(["salary", "satisfaction"]).size()
             .reset_index(name="n").query("n > 1"))
    for _, row in dupes.iterrows():
        ax.annotate(f"×{int(row['n'])}",
                    xy=(row["salary"] / 1000, row["satisfaction"]),
                    xytext=(7, -8), textcoords="offset points",
                    fontsize=6.2, color=TEXT_SECONDARY)

    ax.text(0.035, 0.955,
            f"all points:  r = {r_all:+.2f}\nplausible only:  r = {r_ok:+.2f}",
            transform=ax.transAxes, fontsize=6.8, va="top", ha="left",
            color=TEXT_PRIMARY, linespacing=1.4,
            bbox=dict(boxstyle="round,pad=0.3", facecolor="white",
                      edgecolor=GRID, linewidth=0.6))

    ax.set_xlabel("Reported monthly salary (BDT thousands)")
    ax.set_ylabel("Satisfaction (1–5)")
    ax.set_yticks(range(1, 6))
    ax.set_ylim(0.5, 5.9)
    recessive_axes(ax, grid_axis="both")
    ax.set_ylim(0.5, 6.15)
    ax.legend(loc="lower right", frameon=True, framealpha=1,
              edgecolor=GRID, borderpad=0.35, handletextpad=0.35,
              labelspacing=0.3)
    fig.savefig(HERE / "fig2_salary_scatter.pdf")
    plt.close(fig)
    return r_all, r_ok, len(ok), len(bad)


def fig_correlation(df):
    """Polarity (sign of association) -> diverging scale: two hues with a NEUTRAL
    GRAY midpoint, symmetric about zero. Cell values are printed, so the reading
    never depends on colour alone."""
    cols = ["satisfaction", "salary", "manager_rating", "skills_self",
            "trainings", "experience_years", "age"]
    names = ["Satisfaction", "Salary", "Manager rating", "Skills (self)",
             "Trainings", "Experience", "Age"]
    corr = df[cols].corr(method="spearman")

    cmap = LinearSegmentedColormap.from_list(
        "diverging", [DIVERGING_NEG, DIVERGING_MID, DIVERGING_POS])

    fig, ax = plt.subplots(figsize=(COL_W, 2.9))
    mask = np.triu(np.ones_like(corr, dtype=bool), k=1)
    shown = np.ma.masked_array(corr.values, mask)
    im = ax.imshow(shown, cmap=cmap, vmin=-1, vmax=1)

    for i in range(len(cols)):
        for j in range(len(cols)):
            if mask[i, j]:
                continue
            value = corr.values[i, j]
            ax.text(j, i, f"{value:.2f}", ha="center", va="center", fontsize=6.0,
                    color="white" if abs(value) > 0.55 else TEXT_PRIMARY)

    ax.set_xticks(range(len(cols)))
    ax.set_yticks(range(len(cols)))
    ax.set_xticklabels(names, rotation=45, ha="right")
    ax.set_yticklabels(names)
    ax.set_xticks(np.arange(len(cols) + 1) - 0.5, minor=True)
    ax.set_yticks(np.arange(len(cols) + 1) - 0.5, minor=True)
    ax.grid(which="minor", color="white", linewidth=1.4)
    ax.tick_params(which="minor", length=0)
    for side in ax.spines:
        ax.spines[side].set_visible(False)

    cbar = fig.colorbar(im, ax=ax, shrink=0.62, ticks=[-1, 0, 1], pad=0.03)
    cbar.ax.set_yticklabels(["−1", "0", "+1"], fontsize=6.5)
    cbar.outline.set_visible(False)
    cbar.ax.tick_params(length=0)
    fig.savefig(HERE / "fig3_correlation.pdf")
    plt.close(fig)
    return corr


def fig_quality(df):
    """State per column -> status palette, which is reserved for exactly this and
    never reused as a series colour. Hatching plus a printed status word means the
    state is legible without colour."""
    fields = ["job_title_other", "salary", "experience_years", "projects_led",
              "age", "satisfaction", "manager_rating", "publications"]
    labels = ["Other job title", "Salary", "Experience", "Projects led",
              "Age", "Satisfaction", "Manager rating", "Publications"]
    pct = [100 * df[f].isna().mean() for f in fields]

    def state(p):
        return "FAIL" if p > 30 else ("WARN" if p > 5 else "OK")

    states = [state(p) for p in pct]
    hatches = {"OK": "", "WARN": "///", "FAIL": "xxx"}

    order = np.argsort(pct)
    pct = [pct[i] for i in order]
    labels = [labels[i] for i in order]
    states = [states[i] for i in order]

    fig, ax = plt.subplots(figsize=(COL_W, 2.5))
    bars = ax.barh(range(len(labels)), pct, height=0.66, zorder=3,
                   color=[STATUS[s] for s in states],
                   hatch=[hatches[s] for s in states],
                   edgecolor="white", linewidth=0.7)
    for rect, p, s in zip(bars, pct, states):
        ax.text(p + 1.2, rect.get_y() + rect.get_height() / 2,
                f"{p:.0f}%  {s}", va="center", fontsize=6.6, color=TEXT_SECONDARY)

    ax.axvline(5, color=TEXT_SECONDARY, linestyle=(0, (2, 2)), linewidth=0.7, zorder=2)
    ax.axvline(30, color=TEXT_SECONDARY, linestyle=(0, (2, 2)), linewidth=0.7, zorder=2)
    ax.text(5, len(labels) - 0.25, " warn 5%", fontsize=6.0, color=TEXT_SECONDARY)
    ax.text(30, len(labels) - 0.25, " fail 30%", fontsize=6.0, color=TEXT_SECONDARY)

    ax.set_yticks(range(len(labels)))
    ax.set_yticklabels(labels)
    ax.set_xlabel("Missing values (% of 13 responses)")
    ax.set_xlim(0, 88)
    recessive_axes(ax, grid_axis="x")
    legend = [Patch(facecolor=STATUS[s], hatch=hatches[s], edgecolor="white", label=s)
              for s in ("OK", "WARN", "FAIL")]
    ax.legend(handles=legend, loc="lower right", frameon=True, framealpha=1,
              edgecolor=GRID, ncol=3, borderpad=0.4, handletextpad=0.4,
              columnspacing=0.9)
    fig.savefig(HERE / "fig4_data_quality.pdf")
    plt.close(fig)
    return dict(zip(labels, zip(pct, states)))


def main():
    df = pd.read_csv(DATA)
    counts = fig_satisfaction(df)
    r_all, r_ok, n_ok, n_bad = fig_salary_scatter(df)
    corr = fig_correlation(df)
    quality = fig_quality(df)

    print("fig1 satisfaction counts:", counts.to_dict())
    print(f"fig2 r(all)={r_all:+.3f} n={n_ok + n_bad} | r(plausible)={r_ok:+.3f} n={n_ok}")
    print("fig3 satisfaction correlates (spearman):")
    print(corr["satisfaction"].drop("satisfaction").round(3).to_string())
    print("fig4 quality:", {k: (round(v[0], 1), v[1]) for k, v in quality.items()})
    print("\nwrote 4 PDFs to", HERE)


if __name__ == "__main__":
    main()
