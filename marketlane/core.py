from dataclasses import asdict, dataclass

import numpy as np
from scipy.optimize import linear_sum_assignment


@dataclass(frozen=True)
class Scenario:
    name: str = "broad"
    categories: int = 8
    sellers: int = 24
    arrival_rate: float = 14
    availability: float = .60
    take_rate: float = .15
    payment_rate: float = .025
    support_cost: float = 4.0
    buyer_acquisition_cost: float = 6.0
    days: int = 28
    patience: int = 3
    policy: str = "optimal"

    def __post_init__(self):
        if self.categories < 1 or self.sellers < 0 or self.arrival_rate <= 0:
            raise ValueError("Invalid market dimensions.")
        if not 0 <= self.availability <= 1 or not 0 <= self.take_rate < 1:
            raise ValueError("Availability and fee are probabilities.")
        if self.days <= 0 or self.patience < 1 or self.policy not in {"greedy", "optimal"}:
            raise ValueError("Invalid horizon, patience, or matching policy.")
        if min(self.payment_rate, self.support_cost, self.buyer_acquisition_cost) < 0:
            raise ValueError("Costs cannot be negative.")


def allocate(eligible, surplus, policy="optimal"):
    """One job per supplier slot; maximum cardinality, then total surplus.

    Dummy columns allow every job to stay unmatched. Ineligible edges can never win.
    The bonus exceeds all possible surplus variation, so a further match dominates.
    """
    eligible, surplus = np.asarray(eligible, dtype=bool), np.asarray(surplus, dtype=float)
    if eligible.shape != surplus.shape or eligible.ndim != 2:
        raise ValueError("Eligibility and surplus matrices must have equal 2-D shapes.")
    if not np.isfinite(surplus).all():
        raise ValueError("Surplus must be finite.")
    if policy not in {"greedy", "optimal"}:
        raise ValueError("Unknown allocation policy.")
    jobs, sellers = eligible.shape
    if jobs == 0 or sellers == 0:
        return []
    if policy == "greedy":
        available = set(range(sellers))
        matches = []
        for i in range(jobs):
            options = [j for j in sorted(available) if eligible[i, j]]
            if options:
                j = max(options, key=lambda k: (surplus[i, k], -k))
                matches.append((i, j))
                available.remove(j)
        return matches
    bonus = 2 * jobs * float(np.abs(surplus).max()) + 1
    values = np.full((jobs, sellers + jobs), -bonus * (jobs + 1))
    values[:, sellers:] = 0
    values[:, :sellers] = np.where(eligible, bonus + surplus, -bonus * (jobs + 1))
    rows, cols = linear_sum_assignment(values, maximize=True)
    return [(int(i), int(j)) for i, j in zip(rows, cols) if j < sellers and eligible[i, j]]


def gini(values):
    x = np.sort(np.asarray(values, dtype=float))
    if len(x) == 0 or x.sum() == 0:
        return 0.0
    return float((2 * np.arange(1, len(x)+1) - len(x)-1).dot(x) / (len(x)*x.sum()))


def simulate(scenario=None, seed=0):
    scenario = scenario or Scenario()
    # Separate randomness streams ensure policies see identical arrivals and availability.
    seeds = np.random.SeedSequence(seed).spawn(3)
    supplier_rng, demand_rng, availability_rng = [np.random.default_rng(s) for s in seeds]
    suppliers = []
    for i in range(scenario.sellers):
        first = int(supplier_rng.integers(scenario.categories))
        second = int(supplier_rng.integers(scenario.categories))
        suppliers.append({"id": i, "skills": {first, second},
                          "reserve": float(supplier_rng.uniform(65, 120)),
                          "quality": float(supplier_rng.uniform(.55, 1))})
    jobs, matches = [], []
    waits, earnings = [], np.zeros(scenario.sellers)
    daily = []
    available_slots = 0
    gmv = fee = processing = support = 0.0
    # Drain the cohort after arrivals stop so every job is matched or expired.
    for day in range(scenario.days + scenario.patience):
        if day < scenario.days:
            for _ in range(int(demand_rng.poisson(scenario.arrival_rate))):
                jobs.append({"id": len(jobs), "created": day, "category": int(demand_rng.integers(scenario.categories)),
                             "budget": float(demand_rng.uniform(85, 190)),
                             "min_quality": float(demand_rng.uniform(.5, .85)), "status": "pending"})
        for job in jobs:
            if job["status"] == "pending" and day - job["created"] >= scenario.patience:
                job["status"] = "expired"
        pending = sorted([j for j in jobs if j["status"] == "pending"], key=lambda j: (j["created"], j["id"]))
        availability = availability_rng.random(scenario.sellers) < scenario.availability
        available = [s for s, active in zip(suppliers, availability) if active]
        available_slots += len(available)
        eligible = np.zeros((len(pending), len(available)), dtype=bool)
        surplus = np.zeros_like(eligible, dtype=float)
        for i, job in enumerate(pending):
            payout = job["budget"] * (1-scenario.take_rate)
            for j, supplier in enumerate(available):
                eligible[i, j] = (job["category"] in supplier["skills"]
                                  and supplier["quality"] >= job["min_quality"]
                                  and payout >= supplier["reserve"])
                surplus[i, j] = payout - supplier["reserve"]
        matched = allocate(eligible, surplus, scenario.policy)
        for i, j in matched:
            job, supplier = pending[i], available[j]
            job["status"] = "matched"
            payout = job["budget"] * (1 - scenario.take_rate)
            earnings[supplier["id"]] += payout
            wait = day - job["created"]
            waits.append(wait)
            gmv += job["budget"]
            fee += job["budget"] * scenario.take_rate
            processing += job["budget"] * scenario.payment_rate
            support += scenario.support_cost
            matches.append({"day": day, "job": job["id"], "supplier": supplier["id"], "wait_days": wait,
                            "price": job["budget"], "supplier_payout": payout,
                            "platform_fee": job["budget"] * scenario.take_rate})
        daily.append({"day": day, "pending_at_match": len(pending), "matches": len(matched),
                      "available_supplier_slots": len(available)})
    expired = sum(j["status"] == "expired" for j in jobs)
    outstanding = sum(j["status"] == "pending" for j in jobs)
    acquisition = len(jobs) * scenario.buyer_acquisition_cost
    assert len(matches) + expired + outstanding == len(jobs)
    assert outstanding == 0
    assert np.isclose(earnings.sum() + fee, gmv)
    metrics = {"scenario": scenario.name, "seed": seed, "arrivals": len(jobs), "matches": len(matches),
               "expired": expired, "fill_rate": len(matches)/len(jobs) if jobs else 0,
               "median_wait_days": float(np.median(waits)) if waits else None,
               "p90_wait_days": float(np.quantile(waits, .9)) if waits else None,
               "gmv": gmv, "platform_fee": fee, "supplier_payout": float(earnings.sum()),
               "payment_cost": processing, "support_cost": support, "acquisition_cost": acquisition,
               "contribution": fee-processing-support-acquisition,
               "supplier_utilization": len(matches)/available_slots if available_slots else 0,
               "supplier_earnings_gini": gini(earnings), "active_suppliers": int((earnings > 0).sum()),
               "parameters": asdict(scenario)}
    return metrics, matches, daily


def paired_interval(differences, seed=91, resamples=2000):
    """Bootstrap Monte Carlo mean difference; model uncertainty is not included."""
    values = np.asarray(differences, dtype=float)
    if len(values) < 2:
        raise ValueError("At least two paired simulation seeds are required.")
    rng = np.random.default_rng(seed)
    means = rng.choice(values, (resamples, len(values)), replace=True).mean(axis=1)
    return {"mean": float(values.mean()), "low": float(np.quantile(means, .025)),
            "high": float(np.quantile(means, .975))}
