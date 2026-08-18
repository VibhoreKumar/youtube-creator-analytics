"""
budget_planner.py
--------------------
Works out how many rupees a brand should spend on each creator tier to
maximize real engaged reach, using our real engagement-rate data plus a
synthetic (clearly labeled) cost-per-post estimate, since real brand
campaign costs aren't publicly available anywhere.

Two metrics, two jobs:
- engagement_rate       -> audience QUALITY/trust signal (already have this)
- engaged_reach_per_rupee -> actual IMPACT per rupee spent (this file's job)
"""
import pandas as pd
import numpy as np

# SYNTHETIC cost-per-post ranges in INR, by tier - clearly labeled as modeled,
# not real, since no public source publishes real brand-to-creator payments
COST_RANGES_INR = {
    "nano":  (800, 12_000),
    "micro": (8_000, 100_000),
    "macro": (100_000, 1_250_000),
    "mega":  (1_250_000, 12_500_000),
}


def add_synthetic_cost(df, seed=42):
    """Adds a realistic-but-synthetic cost_per_post_inr column, by tier."""
    rng = np.random.default_rng(seed)
    costs = []
    for tier in df["tier"]:
        low, high = COST_RANGES_INR[tier]
        costs.append(rng.uniform(low, high))
    df["cost_per_post_inr"] = costs
    return df


def add_engaged_reach_metrics(df):
    """
    engaged_audience = how many real people are expected to engage
                        (engagement_rate * subscriber_count)
    engaged_reach_per_rupee = the real efficiency metric - how much engaged
                        audience you get for each rupee spent
    """
    df["engaged_audience"] = df["engagement_rate"] * df["subscriber_count"]
    df["engaged_reach_per_rupee"] = df["engaged_audience"] / df["cost_per_post_inr"]
    return df


def summarize_by_tier(df):
    """
    Only uses channels with real engagement data and a 'normal' or
    'unusually_high_engagement' fraud flag - excludes sample_too_small and
    not_enough_data rows, since those can't be trusted for this calculation.
    """
    usable = df[df["anomaly_flag"].isin(["normal", "unusually_high_engagement"])]

    summary = usable.groupby("tier").agg(
        avg_engagement_rate=("engagement_rate", "mean"),
        avg_cost_per_post_inr=("cost_per_post_inr", "mean"),
        avg_engaged_reach_per_rupee=("engaged_reach_per_rupee", "mean"),
        creator_count=("channel_id", "count"),
    ).reset_index()

    return summary.sort_values("avg_engaged_reach_per_rupee", ascending=False)


def recommend_budget_split(tier_summary, total_budget_inr, max_tier_share=0.6, min_tier_share=0.05):
    """
    Simple, explainable allocation: give each tier a minimum floor, then
    hand remaining budget to whichever tier currently has the best
    engaged-reach-per-rupee, one chunk at a time, respecting a max share
    so the recommendation stays diversified rather than all-in on one tier.
    """
    tiers = tier_summary["tier"].tolist()
    reach_per_rupee = dict(zip(tier_summary["tier"], tier_summary["avg_engaged_reach_per_rupee"]))

    allocation = {t: total_budget_inr * min_tier_share for t in tiers}
    remaining = total_budget_inr * (1 - min_tier_share * len(tiers))
    cap = {t: total_budget_inr * max_tier_share for t in tiers}

    chunk = total_budget_inr * 0.02  # spend in small 2%-of-budget increments
    while remaining >= chunk:
        # pick whichever tier still has room under its cap AND the best reach-per-rupee
        eligible = [t for t in tiers if allocation[t] + chunk <= cap[t]]
        if not eligible:
            break
        best_tier = max(eligible, key=lambda t: reach_per_rupee[t])
        allocation[best_tier] += chunk
        remaining -= chunk

    result = pd.DataFrame({
        "tier": tiers,
        "allocated_inr": [round(allocation[t], 2) for t in tiers],
        "pct_of_budget": [round(100 * allocation[t] / total_budget_inr, 1) for t in tiers],
    })
    result = result.merge(tier_summary, on="tier")
    result["expected_engaged_reach"] = (result["allocated_inr"] * result["avg_engaged_reach_per_rupee"]).round(0)

    return result.sort_values("allocated_inr", ascending=False)