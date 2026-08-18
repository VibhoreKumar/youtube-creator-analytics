"""
fraud_check.py
----------------
Flags channels whose engagement rate is a statistical outlier compared to
other channels in the same tier - either suspiciously HIGH (possible bots/
engagement pods) or suspiciously LOW (possible bought/inactive followers).

Important: this is REAL data with no ground truth. A flag here means
"statistically unusual, worth a human looking at it" - NOT "confirmed fake."


"""
import pandas as pd


def calculate_tier_stats(df, min_subscribers=1000):
    """
    For each niche+tier combination, calculates the average and standard
    deviation of engagement rate. We only use rows where has_engagement_data
    is True, and where subscriber_count is high enough that the engagement
    ratio isn't just noise from a tiny denominator.
    """
    valid_df = df[
        (df["has_engagement_data"] == True) &
        (df["subscriber_count"] >= min_subscribers)
    ]
    tier_stats = valid_df.groupby(["niche_query", "tier"])["engagement_rate"].agg(["mean", "std"])
    tier_stats = tier_stats.rename(columns={"mean": "tier_mean", "std": "tier_std"})
    tier_stats = tier_stats.reset_index()  # <-- important, see explanation below
    return tier_stats


def flag_channel(z_score, threshold=2.5):
    """Turns a z-score into a human-readable flag label."""
    if pd.isna(z_score):
        return "not_enough_data"
    elif z_score > threshold:
        return "unusually_high_engagement"
    elif z_score < -threshold:
        return "unusually_low_engagement"
    else:
        return "normal"


def add_anomaly_flags(df, threshold=2.5,min_subscribers=1000):
    tier_stats = calculate_tier_stats(df,min_subscribers)

    # merge tier_mean and tier_std onto every row, matched by tier
    df = df.merge(tier_stats, on=["tier","niche_query"], how="left")

    df["engagement_z_score"] = (df["engagement_rate"] - df["tier_mean"]) / df["tier_std"]
    df["anomaly_flag"] = df["engagement_z_score"].apply(lambda z: flag_channel(z, threshold))

    too_small = df["subscriber_count"] < min_subscribers
    df.loc[too_small, "anomaly_flag"] = "sample_too_small"

    return df


def run_fraud_check(df):
    df = add_anomaly_flags(df)

    print("Anomaly flag counts:")
    print(df["anomaly_flag"].value_counts())
    print()

    flagged = df[df["anomaly_flag"].isin(["unusually_high_engagement", "unusually_low_engagement"])]
    print(f"Total channels flagged for review: {len(flagged)}")

    return df