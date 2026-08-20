"""Argparse CLI for the OKF kernel."""
from __future__ import annotations

import argparse

from okf.capabilities import cmd_capabilities
from okf.cards import cmd_card
from okf.compile import cmd_compile
from okf.config import load_config
from okf.lint import cmd_lint
from okf.optimize import cmd_optimize
from okf.pack import cmd_lookup, cmd_pack
from okf.paths import (
    DEFAULT_MAX_CARDS,
    DEFAULT_TOKEN_BUDGET,
    MIN_PACK_SCORE,
    PROMPT_CARD_MAX_CHARS,
)
from okf.scrape import cmd_scrape
from okf.serve import cmd_serve
from okf.tokens import cmd_tokens


def main(argv: list[str] | None = None) -> int:
    """
    intent: Parse the subcommand and dispatch.
    input: argv.
    output: subcommand exit code.
    role: main.
    side_effects: per subcommand.
    """
    cfg = load_config()
    default_max_cards = int(cfg.get("max_cards", DEFAULT_MAX_CARDS))
    default_budget = int(cfg.get("token_budget", DEFAULT_TOKEN_BUDGET))
    default_min_score = int(cfg.get("min_pack_score", MIN_PACK_SCORE))

    parser = argparse.ArgumentParser(
        prog="okf.py",
        description="OKF kernel — capabilities, lookup, pack, cards, tokens, "
        "compile, lint, optimize, scrape, and serve.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser(
        "capabilities",
        help="Probe Brain/Filesystem/Python/Git/Shell and list enabled features",
    )
    p.add_argument("--json", action="store_true", help="Machine-readable JSON report")
    p.add_argument(
        "--strict",
        action="store_true",
        help="Exit 4 when runtime_hint is BLOCKED (baseline or brain missing)",
    )
    p.set_defaults(func=cmd_capabilities)

    p = sub.add_parser("lookup", help="Search the vault; --card emits budgeted Prompt Cards")
    p.add_argument("query", help="Search string (title, tags, path, description)")
    p.add_argument("--card", action="store_true",
                   help="Emit ## Prompt Card (or path stub) for each hit")
    p.add_argument("--json", action="store_true",
                   help="Machine-readable JSON (hits or Prompt Pack)")
    p.add_argument("--paths", action="store_true",
                   help="Print concept paths only (one per line)")
    p.add_argument("--limit", type=int, default=5, help="Max hits (default 5)")
    p.add_argument("--type", dest="type_filter", default=None,
                   help="Filter by frontmatter type (e.g. Concept, Playbook)")
    p.add_argument("--max-cards", type=int, default=default_max_cards,
                   help=f"With --card, stop after N cards (default {default_max_cards})")
    p.add_argument("--budget", type=int, default=default_budget,
                   help=f"With --card, token budget for the pack "
                        f"(default {default_budget}; tiktoken if installed else heuristic)")
    p.add_argument("--min-score", dest="min_score", type=int, default=default_min_score,
                   help=f"Relevance floor; ranked hits below this are dropped "
                        f"(default {default_min_score}, 0 disables)")
    p.set_defaults(func=cmd_lookup)

    p = sub.add_parser(
        "pack",
        help="Capability line + cards-only Prompt Pack (markdown|json|xml) — "
        "never a full vault dump",
    )
    p.add_argument("query", help="Search string for pack assembly")
    p.add_argument(
        "--style",
        choices=("markdown", "json", "xml"),
        default="markdown",
        help="Output format (default markdown)",
    )
    p.add_argument("-o", "--output", default=None, help="Write to file instead of stdout")
    p.add_argument("--limit", type=int, default=5, help="Max hits to consider (default 5)")
    p.add_argument("--type", dest="type_filter", default=None, help="Filter by type")
    p.add_argument("--max-cards", type=int, default=default_max_cards)
    p.add_argument("--budget", type=int, default=default_budget)
    p.add_argument("--min-score", dest="min_score", type=int, default=default_min_score,
                   help=f"Relevance floor (default {default_min_score}, 0 disables)")
    p.add_argument("--no-caps", dest="no_caps", action="store_true",
                   help="Omit the leading capability line")
    p.set_defaults(func=cmd_pack)

    p = sub.add_parser("card", help="Extract Prompt Cards from known paths")
    p.add_argument("paths", nargs="+",
                   help="Markdown concept/standard paths (vault-relative or absolute)")
    p.add_argument("--max-chars", type=int, default=PROMPT_CARD_MAX_CHARS,
                   help=f"Warn if a card exceeds this many characters "
                        f"(~150 tokens). Default {PROMPT_CARD_MAX_CHARS}.")
    p.set_defaults(func=cmd_card)

    p = sub.add_parser(
        "tokens",
        help="Count tokens for files or directories (tiktoken if installed, else heuristic)",
    )
    p.add_argument(
        "paths",
        nargs="+",
        help="File(s) and/or directory(ies) to measure",
    )
    p.add_argument(
        "--json",
        action="store_true",
        help="Machine-readable JSON report",
    )
    p.add_argument(
        "--no-recursive",
        action="store_true",
        help="For directories, only count immediate files (no descent)",
    )
    p.add_argument(
        "--all",
        action="store_true",
        help="When walking directories, include every file (not just text extensions)",
    )
    p.add_argument(
        "--ext",
        action="append",
        default=None,
        metavar="EXT",
        help="Limit directory walks to extension(s); repeatable (e.g. --ext md --ext py). "
        "Explicit file paths are always counted.",
    )
    p.set_defaults(func=cmd_tokens)

    p = sub.add_parser(
        "compile",
        help="Rebuild graph.json / index.json (v2+inverted) / prompt_cards.json + HTML embed",
    )
    p.add_argument(
        "--force",
        action="store_true",
        help="Ignore incremental compile cache; re-parse every concept",
    )
    p.set_defaults(func=cmd_compile)

    p = sub.add_parser("lint", help="Vault health check; embeds report into okf-brain.html")
    p.set_defaults(func=cmd_lint)

    p = sub.add_parser("optimize",
                       help="Normalize Reference concepts, rebuild their indexes, recompile")
    p.set_defaults(func=cmd_optimize)

    p = sub.add_parser("scrape", help="Fetch upstream docs into vault/ as a Reference")
    p.add_argument("query", help="Catalog keyword (e.g. 'workflow syntax') or a direct URL")
    p.set_defaults(func=cmd_scrape)

    p = sub.add_parser("serve", help="Read-only local brain visualizer (loopback only)")
    p.add_argument("--host", default="127.0.0.1",
                   help="bind address (default: 127.0.0.1 — local only)")
    p.add_argument("--port", type=int, default=8080, help="listen port (default 8080)")
    p.add_argument("--verbose", action="store_true", help="log each HTTP request")
    p.set_defaults(func=cmd_serve)

    args = parser.parse_args(argv)
    return args.func(args)

