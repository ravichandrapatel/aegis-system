#!/usr/bin/env python3
"""Fill BENCH_REPORT_TEMPLATE.html from a JSON payload.

Usage:
  python3 render_bench_report.py --data report_data.json --out report.html
  python3 render_bench_report.py --data report_data.json --template BENCH_REPORT_TEMPLATE.html --out report.html

The JSON must provide every {{PLACEHOLDER}} key used by the template (see --list-keys).
HTML fragment fields may contain markup; scalars are escaped unless the key ends with _HTML
or is listed in RAW_KEYS.
"""

from __future__ import annotations

import argparse
import html
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DEFAULT_TEMPLATE = HERE / "BENCH_REPORT_TEMPLATE.html"

# Keys whose values are inserted without HTML-escaping (pre-built fragments).
RAW_KEYS = frozenset(
    {
        "EXECUTIVE_SUMMARY_HTML",
        "KPI_CARDS_HTML",
        "DASHBOARD_BARS_HTML",
        "METRICS_TABLE_ROWS",
        "ARCHITECTURE_TABLE_ROWS",
        "RUNTIME_TABLE_ROWS",
        "RUNTIME_FINDINGS_OKF_HTML",
        "RUNTIME_FINDINGS_BASE_HTML",
        "BENEFITS_OKF_HTML",
        "BENEFITS_BASE_HTML",
        "PARENT_FINDINGS_ROWS",
        "METHODOLOGY_LIST_HTML",
        "VERDICT_LINES_HTML",
        "ARTIFACT_FLOW_OKF",
        "ARTIFACT_FLOW_BASE",
        "METHODOLOGY_NOTE",
        "METHODOLOGY_NOTE_CLASS",
    }
)

PLACEHOLDER_RE = re.compile(r"\{\{([A-Z0-9_]+)\}\}")


def list_keys(template_text: str) -> list[str]:
    return sorted(set(PLACEHOLDER_RE.findall(template_text)))


def kpi_card(
    title: str,
    okf: str,
    base: str,
    delta: str,
    winner: str,
    *,
    kind: str = "scored",
) -> str:
    """kind: 'scored' (default) or 'info' (dashed card; winner should be '—')."""
    is_info = str(kind).lower() in {"info", "informational", "non-scoring", "non_scoring"}
    cls = "kpi info" if is_info else "kpi"
    tag = (
        '<span class="tag info">INFO</span>'
        if is_info
        else '<span class="tag scored">SCORED</span>'
    )
    return (
        f'<article class="{cls}"><h3>{html.escape(title)} {tag}</h3>\n'
        f'<div class="vals"><span class="okf">OKF {html.escape(okf)}</span>'
        f'<span class="base">Base {html.escape(base)}</span></div>\n'
        f'<div class="meta"><span class="delta">{html.escape(delta)}</span>'
        f'<span class="win">{html.escape(winner)}</span></div></article>'
    )


def metric_row(
    name: str,
    okf: str,
    base: str,
    delta: str,
    winner: str,
    *,
    status_cells: bool = False,
    info: bool = False,
) -> str:
    """info=True → informational row (italic label; winner should be '—')."""
    tr_cls = ' class="info"' if info else ""
    if status_cells:
        def cell(v: str) -> str:
            cls = "ok" if str(v).upper().startswith("PASS") else (
                "bad" if str(v).upper().startswith("FAIL") else ""
            )
            return f'<td class="{cls}">{html.escape(str(v))}</td>' if cls else f"<td>{html.escape(str(v))}</td>"

        return (
            f"<tr{tr_cls}><td>{html.escape(name)}</td>{cell(okf)}{cell(base)}"
            f"<td>{html.escape(delta)}</td><td class='w'>{html.escape(winner)}</td></tr>"
        )
    return (
        f"<tr{tr_cls}><td>{html.escape(name)}</td><td>{html.escape(str(okf))}</td>"
        f"<td>{html.escape(str(base))}</td><td>{html.escape(str(delta))}</td>"
        f"<td class='w'>{html.escape(winner)}</td></tr>"
    )


def bar_pair(label: str, okf_width: float, okf_label: str, base_width: float, base_label: str,
             rem_width: float | None = None, rem_label: str | None = None) -> str:
    parts = [
        f'<div class="bar-row"><div class="label">{html.escape(label)}</div><div>',
        f'<div class="track" style="margin-bottom:6px"><div class="fill okf" style="width:{okf_width:.1f}%">{html.escape(okf_label)}</div></div>',
    ]
    if rem_width is not None and rem_label is not None:
        parts.append(
            f'<div class="track" style="margin-bottom:4px"><div class="fill base" style="width:{base_width:.1f}%">{html.escape(base_label)}</div></div>'
        )
        parts.append(
            f'<div class="track"><div class="fill rem" style="width:{rem_width:.1f}%">{html.escape(rem_label)}</div></div>'
        )
    else:
        parts.append(
            f'<div class="track"><div class="fill base" style="width:{base_width:.1f}%">{html.escape(base_label)}</div></div>'
        )
    parts.append("</div></div>")
    return "\n".join(parts)


def expand_helpers(data: dict) -> dict:
    """Optional structured helpers → HTML fragments if fragments not already set."""
    out = dict(data)

    if "kpis" in data and not out.get("KPI_CARDS_HTML"):
        out["KPI_CARDS_HTML"] = "\n".join(
            kpi_card(
                k["title"],
                k["okf"],
                k["base"],
                k.get("delta", ""),
                k["winner"],
                kind=k.get("kind", "scored"),
            )
            for k in data["kpis"]
        )

    if "metrics" in data and not out.get("METRICS_TABLE_ROWS"):
        out["METRICS_TABLE_ROWS"] = "\n".join(
            metric_row(
                m["name"],
                m["okf"],
                m["base"],
                m.get("delta", "—"),
                m["winner"],
                status_cells=m.get("status_cells", False),
                info=bool(m.get("info") or m.get("kind") in {"info", "informational", "non-scoring", "non_scoring"}),
            )
            for m in data["metrics"]
        )

    if "architecture" in data and not out.get("ARCHITECTURE_TABLE_ROWS"):
        rows = []
        for m in data["architecture"]:
            rows.append(metric_row(m["name"], m["okf"], m["base"], m.get("delta", "—"), m["winner"]))
        out["ARCHITECTURE_TABLE_ROWS"] = "\n".join(rows)

    if "runtime" in data and not out.get("RUNTIME_TABLE_ROWS"):
        out["RUNTIME_TABLE_ROWS"] = "\n".join(
            metric_row(m["name"], m["okf"], m["base"], m.get("delta", "—"), m["winner"],
                       status_cells=True)
            for m in data["runtime"]
        )

    if "parent_findings" in data and not out.get("PARENT_FINDINGS_ROWS"):
        out["PARENT_FINDINGS_ROWS"] = "\n".join(
            metric_row(m["name"], m["okf"], m["base"], m.get("delta", "—"), m["winner"],
                       status_cells=True)
            for m in data["parent_findings"]
        )

    if "dashboard" in data and not out.get("DASHBOARD_BARS_HTML"):
        bars = []
        for b in data["dashboard"]:
            bars.append(
                bar_pair(
                    b["label"],
                    float(b["okf_width"]),
                    b["okf_label"],
                    float(b["base_width"]),
                    b["base_label"],
                    rem_width=float(b["rem_width"]) if "rem_width" in b else None,
                    rem_label=b.get("rem_label"),
                )
            )
        out["DASHBOARD_BARS_HTML"] = "\n".join(bars)

    for src, dst in (
        ("runtime_findings_okf", "RUNTIME_FINDINGS_OKF_HTML"),
        ("runtime_findings_base", "RUNTIME_FINDINGS_BASE_HTML"),
        ("benefits_okf", "BENEFITS_OKF_HTML"),
        ("benefits_base", "BENEFITS_BASE_HTML"),
        ("methodology", "METHODOLOGY_LIST_HTML"),
        ("verdict_lines", "VERDICT_LINES_HTML"),
    ):
        if src in data and not out.get(dst):
            items = data[src]
            if src == "verdict_lines":
                out[dst] = "\n".join(f"<p>{x}</p>" if x.strip().startswith("<") else f"<p>{x}</p>" for x in items)
            else:
                out[dst] = "\n".join(
                    x if x.strip().startswith("<li") else f"<li>{x}</li>" for x in items
                )

    if "EXECUTIVE_SUMMARY_HTML" not in out and "executive_summary" in data:
        es = data["executive_summary"]
        out["EXECUTIVE_SUMMARY_HTML"] = es if es.strip().startswith("<") else f"<p>{es}</p>"

    if not out.get("METHODOLOGY_NOTE"):
        out["METHODOLOGY_NOTE"] = ""
        out["METHODOLOGY_NOTE_CLASS"] = "hidden"
    elif "METHODOLOGY_NOTE_CLASS" not in out:
        out["METHODOLOGY_NOTE_CLASS"] = ""

    return out


def render(template: str, data: dict) -> str:
    data = expand_helpers(data)
    keys = list_keys(template)
    missing = [k for k in keys if k not in data]
    if missing:
        raise SystemExit(f"Missing placeholder values: {', '.join(missing)}")

    def repl(match: re.Match[str]) -> str:
        key = match.group(1)
        val = data[key]
        if key in RAW_KEYS or key.endswith("_HTML"):
            return str(val)
        return html.escape(str(val))

    return PLACEHOLDER_RE.sub(repl, template)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--template", type=Path, default=DEFAULT_TEMPLATE)
    ap.add_argument("--data", type=Path, help="JSON object of placeholder values / helpers")
    ap.add_argument("--out", type=Path, help="Output HTML path")
    ap.add_argument("--list-keys", action="store_true", help="Print required {{PLACEHOLDER}} keys")
    ap.add_argument("--print-example", action="store_true", help="Print minimal example JSON skeleton")
    args = ap.parse_args()

    template = args.template.read_text(encoding="utf-8")
    keys = list_keys(template)

    if args.list_keys:
        print("\n".join(keys))
        return 0

    if args.print_example:
        example = {k: f"<{k}>" for k in keys}
        example.update(
            {
                "METHODOLOGY_NOTE_CLASS": "hidden",
                "METHODOLOGY_NOTE": "",
                "kpis": [
                    {
                        "title": "True Wall (scored)",
                        "okf": "10.0s",
                        "base": "12.0s (4+8)",
                        "delta": "+16.7%",
                        "winner": "OKF",
                        "kind": "scored",
                    },
                    {
                        "title": "Tool Turns (info)",
                        "okf": "9",
                        "base": "5+4=9",
                        "delta": "not scored alone",
                        "winner": "—",
                        "kind": "info",
                    },
                ],
            }
        )
        print(json.dumps(example, indent=2))
        return 0

    if not args.data or not args.out:
        ap.error("--data and --out are required unless --list-keys / --print-example")

    data = json.loads(args.data.read_text(encoding="utf-8"))
    html_out = render(template, data)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(html_out, encoding="utf-8")
    print(f"Wrote {args.out} ({args.out.stat().st_size} bytes)")
    leftover = set(PLACEHOLDER_RE.findall(html_out))
    if leftover:
        print(f"WARNING: unresolved placeholders remain: {sorted(leftover)}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
