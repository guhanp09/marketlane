import itertools
from dataclasses import replace

import numpy as np
import pytest

from marketlane.core import Scenario, allocate, gini, paired_interval, simulate


def test_optimizer_preserves_scarce_supplier():
    eligible = np.array([[True, True], [True, False]])
    value = np.array([[5, 4], [3, 0]])
    assert len(allocate(eligible, value, "greedy")) == 1
    assert set(allocate(eligible, value)) == {(0, 1), (1, 0)}


def test_optimizer_matches_bruteforce_cardinality_and_value():
    rng = np.random.default_rng(7)
    for _ in range(30):
        eligible = rng.random((3, 3)) < .5
        values = rng.integers(-10, 50, (3, 3))
        candidates = []
        for assignment in itertools.product(range(-1, 3), repeat=3):
            used = [j for j in assignment if j >= 0]
            if len(used) != len(set(used)):
                continue
            if any(j >= 0 and not eligible[i, j] for i, j in enumerate(assignment)):
                continue
            candidates.append((len(used), sum(values[i,j] for i,j in enumerate(assignment) if j >= 0)))
        selected = allocate(eligible, values)
        assert (len(selected), sum(values[i,j] for i,j in selected)) == max(candidates)


@pytest.mark.parametrize("shape", [(0, 2), (2, 0), (2, 3)])
def test_no_eligible_edges(shape):
    assert allocate(np.zeros(shape, dtype=bool), np.zeros(shape)) == []


def test_financial_ledger_and_terminal_states():
    m, matches, _ = simulate(Scenario(days=4), 8)
    assert m["matches"] + m["expired"] == m["arrivals"]
    assert m["platform_fee"] + m["supplier_payout"] == pytest.approx(m["gmv"])
    assert m["contribution"] == pytest.approx(m["platform_fee"]-m["payment_cost"]-m["support_cost"]-m["acquisition_cost"])
    assert len({(x["day"], x["supplier"]) for x in matches}) == len(matches)
    assert len({x["job"] for x in matches}) == len(matches)


def test_zero_supply_expires_every_job():
    m, _, _ = simulate(Scenario(sellers=0, days=4))
    assert m["matches"] == 0 and m["arrivals"] == m["expired"]
    assert m["contribution"] < 0 and m["median_wait_days"] is None


def test_common_randomness_preserved_across_policies():
    base = Scenario(days=5)
    a, _, ad = simulate(base, 12)
    b, _, bd = simulate(replace(base, policy="greedy"), 12)
    assert a["arrivals"] == b["arrivals"]
    assert [x["available_supplier_slots"] for x in ad] == [x["available_supplier_slots"] for x in bd]


def test_repeatability():
    assert simulate(Scenario(days=3), 5) == simulate(Scenario(days=3), 5)


def test_gini_boundaries_and_zero_difference_interval():
    assert gini([2, 2, 2]) == 0
    assert gini([0, 0, 3]) == pytest.approx(2/3)
    assert paired_interval([0, 0, 0]) == {"mean": 0., "low": 0., "high": 0.}


def test_invalid_configuration():
    with pytest.raises(ValueError):
        Scenario(take_rate=1.2)
