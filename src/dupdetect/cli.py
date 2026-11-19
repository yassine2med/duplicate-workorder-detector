"""Command line entry: python -m dupdetect work_orders.csv"""
from __future__ import annotations

import argparse
import sys

from .detector import find_pairs, group_pairs, load_orders


def main(argv: list[str] | None = None) -> int:
    """Entry point. Returns a process exit code."""
    parser = argparse.ArgumentParser(prog="dupdetect", description="Flag likely duplicate work orders")
    parser.add_argument("csv", help="work order CSV with id, location, description, created")
    parser.add_argument("--location-min", type=float, default=90.0, help="minimum location score, 0-100")
    parser.add_argument("--description-min", type=float, default=70.0, help="minimum description score, 0-100")
    parser.add_argument("--window", type=int, default=14, help="days apart allowed")
    args = parser.parse_args(argv)
    try:
        orders = load_orders(args.csv)
        pairs = find_pairs(orders, args.location_min, args.description_min, args.window)
    except (OSError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    groups = group_pairs(pairs)
    print(f"{len(orders)} work orders, {len(pairs)} pairs, {len(groups)} duplicate groups")
    for number, group in enumerate(groups, start=1):
        original, *copies = group
        print(f"\nGroup {number}: keep {original.id}, review {', '.join(c.id for c in copies)}")
        print(f"  {original.location} | {original.description}")
    print("\nPairs (score = 40% location + 60% description)")
    for p in pairs:
        print(f"{p.first.id} {p.second.id}  score {p.score:5.1f}  loc {p.location_score:5.1f}  desc {p.description_score:5.1f}  {p.days_apart} d apart")
    return 0
