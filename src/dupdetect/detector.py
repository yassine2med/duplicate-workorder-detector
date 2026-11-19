"""Find likely duplicate work orders by location, description and date."""
from __future__ import annotations

import csv
import re
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from rapidfuzz import fuzz

REQUIRED = ("id", "location", "description", "created")
ABBREVIATIONS = {"bldg": "building", "bld": "building", "rm": "room", "flr": "floor", "ac": "air conditioning"}
STOPWORDS = {"a", "an", "the", "in", "at", "of", "on", "is", "are", "to", "near", "and", "with", "when"}


@dataclass(frozen=True)
class WorkOrder:
    """One work order row."""

    id: str
    location: str
    description: str
    created: date


@dataclass(frozen=True)
class Pair:
    """Two work orders judged to describe the same job."""

    first: WorkOrder
    second: WorkOrder
    location_score: float
    description_score: float
    days_apart: int

    @property
    def score(self) -> float:
        """Combined score, 40 percent location and 60 percent description."""
        return round(0.4 * self.location_score + 0.6 * self.description_score, 1)


def normalize(text: str, drop_stopwords: bool = False) -> str:
    """Lowercase, remove punctuation, expand short forms such as bldg and rm."""
    words = re.findall(r"[a-z0-9]+", text.lower())
    words = [ABBREVIATIONS.get(w, w) for w in words]
    if drop_stopwords:
        words = [w for w in words if w not in STOPWORDS]
    return " ".join(words)


def _number_tokens(text: str) -> frozenset[str]:
    """Tokens that contain a digit, such as room numbers. Two places only match if these agree."""
    return frozenset(w for w in text.split() if any(c.isdigit() for c in w))


def load_orders(path: str | Path) -> list[WorkOrder]:
    """Read work orders from CSV. Raises ValueError on missing columns or bad dates."""
    with open(path, newline="", encoding="utf-8-sig") as fh:
        reader = csv.DictReader(fh)
        missing = [c for c in REQUIRED if c not in (reader.fieldnames or [])]
        if missing:
            raise ValueError(f"missing columns: {', '.join(missing)}")
        orders = []
        for line, row in enumerate(reader, start=2):
            try:
                created = date.fromisoformat(row["created"].strip())
            except ValueError:
                raise ValueError(f"bad created date on line {line}") from None
            orders.append(WorkOrder(row["id"].strip(), row["location"], row["description"], created))
    return orders


def find_pairs(
    orders: list[WorkOrder],
    location_min: float = 90.0,
    description_min: float = 70.0,
    window_days: int = 14,
) -> list[Pair]:
    """Return pairs that match on location, description and a short date window.

    Orders are sorted by date so the inner loop stops once the window is passed.
    Room and building numbers must be identical: Room 101 never matches Room 102.
    """
    if not 0 <= location_min <= 100 or not 0 <= description_min <= 100:
        raise ValueError("thresholds must be between 0 and 100")
    if window_days < 0:
        raise ValueError("window_days cannot be negative")
    ordered = sorted(orders, key=lambda o: o.created)
    loc_keys = [normalize(o.location) for o in ordered]
    loc_numbers = [_number_tokens(k) for k in loc_keys]
    desc_keys = [normalize(o.description, drop_stopwords=True) for o in ordered]
    pairs = []
    for i, first in enumerate(ordered):
        for j in range(i + 1, len(ordered)):
            gap = (ordered[j].created - first.created).days
            if gap > window_days:
                break
            if loc_numbers[i] != loc_numbers[j]:
                continue
            loc = fuzz.token_sort_ratio(loc_keys[i], loc_keys[j])
            if loc < location_min:
                continue
            desc = fuzz.token_sort_ratio(desc_keys[i], desc_keys[j])
            if desc >= description_min:
                pairs.append(Pair(first, ordered[j], round(loc, 1), round(desc, 1), gap))
    return sorted(pairs, key=lambda p: -p.score)


def group_pairs(pairs: list[Pair]) -> list[list[WorkOrder]]:
    """Merge pairs into groups. Each group is sorted by date, so the first is the original."""
    parent: dict[str, str] = {}

    def find(key: str) -> str:
        parent.setdefault(key, key)
        while parent[key] != key:
            parent[key] = parent[parent[key]]
            key = parent[key]
        return key

    members: dict[str, WorkOrder] = {}
    for pair in pairs:
        members[pair.first.id], members[pair.second.id] = pair.first, pair.second
        parent[find(pair.first.id)] = find(pair.second.id)
    groups: dict[str, list[WorkOrder]] = {}
    for key, order in members.items():
        groups.setdefault(find(key), []).append(order)
    result = [sorted(g, key=lambda o: (o.created, o.id)) for g in groups.values()]
    return sorted(result, key=lambda g: (g[0].created, g[0].id))
