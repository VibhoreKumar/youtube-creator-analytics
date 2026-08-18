"""
plan_budget.py
----------------
Run this to see a recommended budget split across creator tiers.

Usage:
    python run/plan_budget.py
"""
import sys
from pathlib import Path
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.analyze.budget_planner import (
    add_synthetic_cost, add_engaged_reach_metrics,
    summarize_by_tier, recommend_budget_split
)


def main():
    input_path = Path("data/final/creators_with_anomaly_flags.csv")
    df = pd.read_csv(input_path)

    df = add_synthetic_cost(df)
    df = add_engaged_reach_metrics(df)

    tier_summary = summarize_by_tier(df)
    print("Tier summary (real engagement rate, synthetic cost):")
    print(tier_summary.to_string(index=False))

    total_budget = 500_000  # INR - change this to test different budget sizes
    print(f"\nRecommended split for a budget of ₹{total_budget:,}:")
    plan = recommend_budget_split(tier_summary, total_budget)
    print(plan[["tier", "allocated_inr", "pct_of_budget", "avg_engagement_rate", "expected_engaged_reach"]].to_string(index=False))

    output_folder = Path("data/final")
    output_folder.mkdir(parents=True, exist_ok=True)
    df.to_csv(output_folder / "creators_with_budget_metrics.csv", index=False)
    plan.to_csv(output_folder / "recommended_budget_split.csv", index=False)
    print(f"\nSaved detailed data and the budget plan to {output_folder}")


if __name__ == "__main__":
    main()