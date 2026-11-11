import argparse
import json
from dataclasses import replace
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
import plotly.express as px

from .core import Scenario, paired_interval, simulate


def demo(output, seeds=40):
    base = Scenario()
    scenarios = [base, replace(base, name="focused", categories=2),
                 replace(base, name="focused_higher_fee", categories=2, take_rate=.25),
                 replace(base, name="focused_greedy", categories=2, policy="greedy")]
    rows = []
    for scenario in scenarios:
        for seed in range(seeds):
            metric, matches, daily = simulate(scenario, seed)
            rows.append({k:v for k,v in metric.items() if k != "parameters"})
            if seed == 0:
                dest = output / scenario.name
                dest.mkdir(parents=True, exist_ok=True)
                pd.DataFrame(matches).to_csv(dest / "match_ledger.csv", index=False)
                pd.DataFrame(daily).to_csv(dest / "daily.csv", index=False)
                (dest / "parameters.json").write_text(json.dumps(metric["parameters"], indent=2))
    frame = pd.DataFrame(rows)
    output.mkdir(parents=True, exist_ok=True)
    frame.to_csv(output / "simulation_runs.csv", index=False)
    summary = frame.groupby("scenario").mean(numeric_only=True).drop(columns="seed")
    summary.to_csv(output / "scenario_summary.csv")
    paired = {}
    reference = frame[frame.scenario == "focused"].set_index("seed")
    for alternative in ["broad", "focused_higher_fee", "focused_greedy"]:
        other = frame[frame.scenario == alternative].set_index("seed")
        paired[alternative+"_minus_focused"] = {name: paired_interval(other[name]-reference[name])
                                                  for name in ["fill_rate", "contribution", "supplier_earnings_gini"]}
    sensitivity = []
    for arrival in [7, 14, 21]:
        for fee in [.10, .15, .25]:
            scenario = replace(base, name=f"focused_d{arrival}_f{fee}", categories=2,
                               arrival_rate=arrival, take_rate=fee)
            for seed in range(12):
                metric, _, _ = simulate(scenario, seed)
                sensitivity.append({"demand": arrival, "take_rate": fee, "seed": seed,
                                    "fill_rate": metric["fill_rate"], "contribution": metric["contribution"]})
    pd.DataFrame(sensitivity).to_csv(output / "sensitivity.csv", index=False)
    metrics = {"data_type": "synthetic model", "comparison_runs": len(rows), "paired_seeds": seeds,
               "sensitivity_runs": len(sensitivity), "summary": summary.to_dict(orient="index"),
               "paired_mean_intervals": paired,
               "decision": "VALIDATE_ASSUMPTIONS_BEFORE_LAUNCH"}
    (output / "metrics.json").write_text(json.dumps(metrics, indent=2))
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.5))
    labels = ["Broad", "Focused", "Focused\n25% fee", "Focused\ngreedy"]
    ordered = summary.reindex([s.name for s in scenarios])
    axes[0].bar(labels, ordered.fill_rate, color=["#536b8a", "#007d72", "#b57738", "#809786"])
    axes[0].set(title="Fulfilment fraction", ylim=(0, 1), ylabel="Matched / all arrivals")
    axes[1].bar(labels, ordered.contribution, color=["#536b8a", "#007d72", "#b57738", "#809786"])
    axes[1].axhline(0, color="#222", linewidth=.8)
    axes[1].set(title="Contribution after modeled acquisition cost", ylabel="Illustrative currency units / cohort")
    fig.suptitle(f"MarketLane · {seeds} paired synthetic runs per policy")
    fig.tight_layout()
    fig.savefig(output / "comparison.png", dpi=170)
    plt.close(fig)
    chart = px.scatter(frame, x="fill_rate", y="contribution", color="scenario",
                       hover_data=["seed", "supplier_earnings_gini"], template="plotly_white")
    chart.update_layout(title="MarketLane · fulfilment and contribution across synthetic runs")
    chart.write_html(output / "tradeoff.html", include_plotlyjs=True)
    focused, broad = summary.loc["focused"], summary.loc["broad"]
    greedy = summary.loc["focused_greedy"]
    note = f"""# MarketLane launch decision memo

**Synthetic scenario analysis. No marketplace observations, interviews, revenue, or causal launch effects are claimed.**

Decision: validate a two-category, oldest-first pilot before broad expansion. Under the declared model, mean fill rate is
{focused.fill_rate:.1%} for focused supply/demand versus {broad.fill_rate:.1%} across eight categories.
This is a model comparison, not a forecast. The complete fee, concentration and cost trade-offs are in `scenario_summary.csv`.

The simpler oldest-first policy achieves {greedy.fill_rate:.1%} fill versus {focused.fill_rate:.1%} for the daily optimizer.
The optimizer maximizes today's matches and then surplus, but does not protect older jobs against future expiry.
This result favors retaining the simpler baseline in this model. It does not prove greedy is generally optimal.

The experiment compares four policies over {seeds} paired seeds ({len(rows)} runs) and nine demand/fee combinations
over 12 seeds ({len(sensitivity)} sensitivity runs). Policies within the same category configuration receive identical
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
"""
    (output / "decision.md").write_text(note)
    print(json.dumps({"comparison_runs": len(rows), "sensitivity_runs": len(sensitivity),
                      "summary": summary[["fill_rate", "contribution", "supplier_earnings_gini"]].to_dict("index")}, indent=2))


def main():
    parser = argparse.ArgumentParser(description="Compare service-marketplace launch scenarios.")
    parser.add_argument("command", choices=["demo", "simulate"])
    parser.add_argument("--output", type=Path, default=Path("reports"))
    parser.add_argument("--seeds", type=int, default=40)
    parser.add_argument("--config", type=Path)
    parser.add_argument("--seed", type=int, default=0)
    args = parser.parse_args()
    if args.command == "demo":
        if args.seeds < 2:
            parser.error("Use at least two simulation seeds.")
        demo(args.output, args.seeds)
    else:
        if not args.config:
            parser.error("simulate requires --config")
        scenario = Scenario(**json.loads(args.config.read_text()))
        metrics, matches, daily = simulate(scenario, args.seed)
        args.output.mkdir(parents=True, exist_ok=True)
        (args.output / "metrics.json").write_text(json.dumps(metrics, indent=2))
        pd.DataFrame(matches).to_csv(args.output / "match_ledger.csv", index=False)
        pd.DataFrame(daily).to_csv(args.output / "daily.csv", index=False)
        print(json.dumps(metrics, indent=2))


if __name__ == "__main__":
    main()
