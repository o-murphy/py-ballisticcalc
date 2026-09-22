"""Build the benchmark report page from `benchmarks/benchmarks.csv`.

Writes:
    - docs/concepts/bench.svg          (mean time in ms, grouped bars, log scale)
    - docs/concepts/bench_speedup.svg  (x times faster than python.rk4, grouped bars, log scale)
    - docs/concepts/bench.md   (page embedding the chart plus a results table)

For every (engine, case) the run with the most repeats (then the latest) is used.

Usage:
    uv run python scripts/bench_report.py
    uv run python scripts/bench_report.py --csv benchmarks/benchmarks.csv --out-dir docs/concepts
"""
from __future__ import annotations

import argparse
import csv
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

CASES = ("Trajectory", "Zero")
COLORS = {"Trajectory": "#009688", "Zero": "#ff9800"}  # teal / orange, readable on light and dark
REFERENCE = "python.rk4"
TEXT_COLOR = "#888888"  # neutral, readable on light and dark backgrounds
FONT_SIZE = 15  # base font size; value labels and ticks are derived from it


def load_best(csv_path: Path) -> tuple[dict[tuple[str, str], dict], dict]:
    """Return the best row per (engine, case) and the last row (for version info)."""
    rows = list(csv.DictReader(csv_path.open(encoding="utf-8")))
    if not rows:
        raise SystemExit(f"No rows in {csv_path}")
    best: dict[tuple[str, str], dict] = {}
    for row in rows:
        row["repeats"] = int(row["repeats"])
        key = (row["engine"], row["case"])
        if key not in best or (row["repeats"], row["timestamp"]) >= (best[key]["repeats"], best[key]["timestamp"]):
            best[key] = row
    return best, rows[-1]


def fmt_ms(value: float) -> str:
    return f"{value:.3g}" if value < 100 else f"{value:.0f}"


def fmt_x(value: float) -> str:
    return f"{value:.3g}" if value < 1000 else f"{value:.0f}"


def short_label(engine: str) -> str:
    """Compact chart label: `module:FooIntegrationEngine` -> `Foo`; `<engine>.<method>` names are kept as is."""
    if ":" in engine:
        return engine.split(":", 1)[1].removesuffix("IntegrationEngine")
    return engine


def draw_chart(
    values: dict[tuple[str, str], float],
    engines: list[str],
    svg_path: Path,
    *,
    title: str,
    ylabel: str,
    fmt,
    baseline: float | None = None,
) -> None:
    """Grouped bars (one per case) per engine on a log scale.

    With `baseline` set, bars start at that value (bars below it point down) and a reference line is drawn.
    """
    fig, ax = plt.subplots(figsize=(max(9.0, 2.0 * len(engines) + 1.5), 6.5))
    width = 0.38
    xs = range(len(engines))
    for i, case in enumerate(CASES):
        offset = (i - (len(CASES) - 1) / 2) * width
        vals = [values[(e, case)] for e in engines]
        if baseline is None:
            bars = ax.bar([x + offset for x in xs], vals, width, label=case, color=COLORS[case])
        else:
            bars = ax.bar(
                [x + offset for x in xs], [v - baseline for v in vals], width,
                bottom=baseline, label=case, color=COLORS[case],
            )
        for x, value in zip(xs, vals):
            below = baseline is not None and value < baseline
            ax.annotate(
                fmt(value), (x + offset, value),
                xytext=(0, -2 if below else 2), textcoords="offset points",
                ha="center", va="top" if below else "bottom", fontsize=FONT_SIZE - 4, color=TEXT_COLOR,
            )
    if baseline is not None:
        ax.axhline(baseline, color=TEXT_COLOR, linewidth=0.8, linestyle="--")
    ax.set_yscale("log")
    ax.set_ylabel(ylabel, color=TEXT_COLOR, fontsize=FONT_SIZE)
    ax.set_xticks(list(xs))
    ax.set_xticklabels([short_label(e) for e in engines], rotation=30, ha="right", color=TEXT_COLOR, fontsize=FONT_SIZE)
    ax.tick_params(axis="y", colors=TEXT_COLOR, labelsize=FONT_SIZE)
    ax.set_title(title, color=TEXT_COLOR, fontsize=FONT_SIZE + 3)
    ax.grid(axis="y", which="major", color=TEXT_COLOR, alpha=0.25, linewidth=0.6)
    ax.set_axisbelow(True)
    for spine in ax.spines.values():
        spine.set_color(TEXT_COLOR)
    ax.margins(y=0.2)
    legend = ax.legend(frameon=False, fontsize=FONT_SIZE)
    for text in legend.get_texts():
        text.set_color(TEXT_COLOR)
    fig.tight_layout()
    fig.savefig(svg_path, format="svg", transparent=True, metadata={"Date": None})
    plt.close(fig)


def write_markdown(best: dict, engines: list[str], last: dict, md_path: Path, svg_name: str, speedup_svg_name: str | None) -> None:
    ref = {c: float(best[(REFERENCE, c)]["mean_ms"]) for c in CASES} if (REFERENCE, "Zero") in best else None
    lines = [
        "# Benchmarks",
        "",
        "Mean time per call for each engine (lower is better), generated from",
        "[`benchmarks/benchmarks.csv`](https://github.com/o-murphy/py-ballisticcalc/blob/master/benchmarks/benchmarks.csv) by `scripts/bench_report.py`.",
        "Each engine has two bars: `Trajectory` (fire a trajectory) and `Zero` (find the zero angle).",
        "The vertical scales are logarithmic.",
        "",
        "## Mean time",
        "",
        f"![Mean time per call by engine]({svg_name})",
        "",
    ] + ([
        f"## Speedup vs `{REFERENCE}`",
        "",
        f"![Speedup vs {REFERENCE}]({speedup_svg_name})",
        "",
    ] if speedup_svg_name else []) + [
        f"- **Version:** `{last['version']}` (branch `{last['branch']}`, commit `{last['git_hash']}`)",
        "- Where an engine was run several times, the run with the most repeats is used.",
        "- Only engines present in the benchmark data are listed.",
        "",
        "## Results",
        "",
    ]
    if ref:
        lines += [
            f"| Engine | Trajectory, ms | vs `{REFERENCE}` | Zero, ms | vs `{REFERENCE}` | Repeats |",
            "|--------|---------------:|-----------:|---------:|-----------:|--------:|",
        ]
    else:
        lines += ["| Engine | Trajectory, ms | Zero, ms | Repeats |", "|--------|---------------:|---------:|--------:|"]
    for e in engines:
        t, z = (float(best[(e, c)]["mean_ms"]) for c in CASES)
        repeats = best[(e, "Trajectory")]["repeats"]
        if ref:
            lines.append(
                f"| `{e}` | {t:.3f} | {fmt_x(ref['Trajectory'] / t)}x | {z:.3f} | {fmt_x(ref['Zero'] / z)}x | {repeats} |"
            )
        else:
            lines.append(f"| `{e}` | {t:.3f} | {z:.3f} | {repeats} |")
    lines += [
        "",
        "!!! note",
        "    Adaptive engines (`cython.rkck`, `cython.dopri`, `cython.tsitouras`) take far fewer steps than",
        "    fixed-step RK4, which is why `Zero` shows such a large gap. Results depend on hardware and workload;",
        "    treat them as relative figures. See [Engines](engines.md) for the engine overview.",
        "",
    ]
    md_path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--csv", type=Path, default=Path("benchmarks/benchmarks.csv"))
    parser.add_argument("--out-dir", type=Path, default=Path("docs/concepts"))
    args = parser.parse_args()

    best, last = load_best(args.csv)
    engines = sorted(
        {e for e, c in best if all((e, k) in best for k in CASES)},
        key=lambda e: -float(best[(e, "Trajectory")]["mean_ms"]),
    )
    args.out_dir.mkdir(parents=True, exist_ok=True)
    svg_path = args.out_dir / "bench.svg"
    times = {(e, c): float(best[(e, c)]["mean_ms"]) for e in engines for c in CASES}
    draw_chart(
        times, engines, svg_path,
        title="Mean time per call by engine (lower is better)",
        ylabel="mean time per call, ms (log scale)",
        fmt=fmt_ms,
    )
    speedup_path = None
    if all((REFERENCE, c) in best for c in CASES):
        speedup_path = args.out_dir / "bench_speedup.svg"
        speedups = {(e, c): times[(REFERENCE, c)] / times[(e, c)] for e in engines for c in CASES}
        draw_chart(
            speedups, engines, speedup_path,
            title=f"Speedup vs {REFERENCE} (higher is better)",
            ylabel=f"x times faster than {REFERENCE} (log scale)",
            fmt=lambda v: f"{fmt_x(v)}x",
            baseline=1.0,
        )
    write_markdown(best, engines, last, args.out_dir / "bench.md", svg_path.name, speedup_path.name if speedup_path else None)
    print(f"Wrote {svg_path}{', ' + str(speedup_path) if speedup_path else ''} and {args.out_dir / 'bench.md'} ({len(engines)} engines)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
