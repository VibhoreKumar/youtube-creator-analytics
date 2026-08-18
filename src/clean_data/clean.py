import pandas as pd


def fill_missing_values(df):
    """Fill in the missing values that are expected/normal, not errors."""
    df["country"] = df["country"].fillna("Unknown")
    df["description"] = df["description"].fillna("")
    return df


def flag_missing_engagement(df):
    """
    Instead of silently leaving engagement_rate blank, add a clear
    True/False column so later analysis can filter these out on purpose.
    """
    df["has_engagement_data"] = df["engagement_rate"].notnull()
    return df


def remove_duplicate_channels(df):
    """Check for and remove duplicate channel_id rows, if any exist."""
    duplicate_count = df.duplicated(subset=["channel_id"]).sum()
    print(f"Duplicate channel_id rows found: {duplicate_count}")
    df = df.drop_duplicates(subset=["channel_id"])
    return df


def add_channel_age(df):
    """Converts published_at to a real date and calculates channel age in days."""
    df["published_at"] = pd.to_datetime(df["published_at"],format="ISO8601")
    today = pd.Timestamp.now(tz="UTC")
    df["channel_age_days"] = (today - df["published_at"]).dt.days
    return df


def assign_tier(subscriber_count):
    """Same tier rule we used for the synthetic data - applied to real subscriber counts."""
    if subscriber_count < 10_000:
        return "nano"
    elif subscriber_count < 100_000:
        return "micro"
    elif subscriber_count < 1_000_000:
        return "macro"
    else:
        return "mega"


def add_tier_column(df):
    df["tier"] = df["subscriber_count"].apply(assign_tier)
    return df


def clean_youtube_data(df):
    """Runs every cleaning step in order and returns the cleaned DataFrame."""
    print(f"Starting rows: {len(df)}")

    df = fill_missing_values(df)
    df = flag_missing_engagement(df)
    df = remove_duplicate_channels(df)
    df = add_channel_age(df)
    df = add_tier_column(df)

    print(f"Final rows: {len(df)}")
    print()
    print("Tier breakdown:")
    print(df["tier"].value_counts())

    return df