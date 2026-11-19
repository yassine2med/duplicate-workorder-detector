"""Fuzzy duplicate detection for work orders."""
from .detector import Pair, WorkOrder, find_pairs, group_pairs, load_orders, normalize

__all__ = ["Pair", "WorkOrder", "find_pairs", "group_pairs", "load_orders", "normalize"]
