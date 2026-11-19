from datetime import date
from pathlib import Path

import pytest

from dupdetect import WorkOrder, find_pairs, group_pairs, load_orders, normalize
from dupdetect.cli import main

SAMPLE = Path(__file__).resolve().parent.parent / "data" / "work_orders.csv"


def wo(id_, loc, desc, day=1):
    return WorkOrder(id_, loc, desc, date(2026, 5, day))


def test_normalize_expands_and_strips():
    assert normalize("Bldg A, Rm 101!") == "building a room 101"


def test_normalize_stopwords():
    assert normalize("The door is at the end", drop_stopwords=True) == "door end"


def test_same_job_different_wording_is_flagged():
    pairs = find_pairs([
        wo("1", "Building A, Room 101", "Thermostat not responding"),
        wo("2", "Bldg A Rm 101", "thermostat is not responding - room too hot", 2),
    ])
    assert len(pairs) == 1 and pairs[0].days_apart == 1


def test_different_room_not_flagged():
    pairs = find_pairs([
        wo("1", "Building A, Room 101", "Thermostat not responding"),
        wo("2", "Building A, Room 102", "Thermostat not responding"),
    ])
    assert pairs == []


def test_different_problem_same_room_not_flagged():
    pairs = find_pairs([
        wo("1", "Building B, Room 210", "Leaking faucet in restroom"),
        wo("2", "Building B, Room 210", "Outlet dead near window"),
    ])
    assert pairs == []


def test_outside_window_is_recurrence_not_duplicate():
    orders = [wo("1", "Annex D, Room 2", "Door will not latch", 1),
              wo("2", "Annex D, Room 2", "Door will not latch", 30)]
    assert find_pairs(orders, window_days=14) == []
    assert len(find_pairs(orders, window_days=60)) == 1


def test_input_order_does_not_matter():
    a = wo("1", "Building A, Room 1", "Exit sign out", 1)
    b = wo("2", "Building A, Room 1", "Exit sign out", 2)
    assert [(p.first.id, p.second.id) for p in find_pairs([b, a])] == [("1", "2")]


def test_groups_merge_three_way_duplicate():
    orders = [wo("1", "Building C, Room 305", "Stained ceiling tile sagging", 1),
              wo("2", "Bldg C Rm 305", "Ceiling tile stained and sagging", 1),
              wo("3", "Building C, Room 305", "Stained ceiling tile sagging", 2),
              wo("4", "Building D, Room 1", "Toilet running", 2)]
    groups = group_pairs(find_pairs(orders))
    assert len(groups) == 1
    assert [o.id for o in groups[0]] == ["1", "2", "3"]


def test_no_orders_and_no_pairs():
    assert find_pairs([]) == [] and group_pairs([]) == []


def test_bad_thresholds_rejected():
    with pytest.raises(ValueError):
        find_pairs([], location_min=150)
    with pytest.raises(ValueError):
        find_pairs([], window_days=-1)


def test_score_weighting():
    pair = find_pairs([wo("1", "Building A", "Exit sign out"), wo("2", "Building A", "Exit sign out", 2)])[0]
    assert pair.score == 100.0


def test_load_orders_errors(tmp_path):
    bad = tmp_path / "bad.csv"
    bad.write_text("id,location\n1,A\n")
    with pytest.raises(ValueError, match="missing columns"):
        load_orders(bad)
    bad.write_text("id,location,description,created\n1,A,x,05/01/2026\n")
    with pytest.raises(ValueError, match="line 2"):
        load_orders(bad)


def test_cli_on_sample(capsys):
    assert main([str(SAMPLE)]) == 0
    out = capsys.readouterr().out
    assert "20 work orders" in out and "WO-3001" in out


def test_cli_missing_file(tmp_path, capsys):
    assert main([str(tmp_path / "none.csv")]) == 1
    assert "error" in capsys.readouterr().err
