# MarketLane launch decision memo

**Synthetic scenario analysis. No marketplace observations, interviews, revenue, or causal launch effects are claimed.**

Decision: validate a two-category, oldest-first pilot before broad expansion. Under the declared model, mean fill rate is
90.3% for focused supply/demand versus 75.1% across eight categories.
This is a model comparison, not a forecast. The complete fee, concentration and cost trade-offs are in `scenario_summary.csv`.

The simpler oldest-first policy achieves 93.7% fill versus 90.3% for the daily optimizer.
The optimizer maximizes today's matches and then surplus, but does not protect older jobs against future expiry.
This result favors retaining the simpler baseline in this model. It does not prove greedy is generally optimal.

The experiment compares four policies over 40 paired seeds (160 runs) and nine demand/fee combinations
over 12 seeds (108 sensitivity runs). Policies within the same category configuration receive identical
exogenous demand, supplier attributes and availability. Across category counts, the same random streams are reused,
but categories and eligibility deliberately change; this is not a randomized empirical experiment.

Each buyer has a budget, category, quality requirement and three-day expiry. Each available seller provides at most
one service slot per day, has two possible skills and a reservation payout. Eligibility enforces all constraints.
An assignment optimizer maximizes match count, then supplier surplus; oldest-first greedy matching is a baseline.
The optimizer is a daily myopic policy, not a globally optimal multi-day plan. Age priority is not guaranteed by it.

Financial accounting: GMV = seller payout + platform fees. Contribution = platform fees - processing cost - support
cost - acquisition cost for **all** arriving buyers, including unmatched buyers. Acquisition cost is assumed, not learned.
Revenue cannot be interpreted as profit. Earnings Gini includes inactive sellers and measures concentration, not fairness.

All cohorts are drained beyond the final arrival day so unresolved demand is not silently counted as successful.
Paired bootstrap intervals quantify uncertainty in the simulated mean from finite seeds, not model realism or market risk.
The model omits repeat demand, strategic pricing, service failure, churn, competition, taxes and fixed operating cost.

Before investing: measure real supply availability, acceptable payouts, buyer patience, support burden and acquisition
cost; then replace assumptions and rerun. A higher take rate affects seller feasibility in this model, but buyer price
elasticity and seller behavior are not estimated. The proposed pilot must test those omitted responses.
