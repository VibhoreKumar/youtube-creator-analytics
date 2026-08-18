import sys
from pathlib import Path
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.analyze.fraud_check import run_fraud_check


def main():
    input_path = Path("data/cleaned/youtube_creators_clean.csv")
    df = pd.read_csv(input_path)

    df = run_fraud_check(df)

    output_folder = Path("data/final")
    output_folder.mkdir(parents=True, exist_ok=True)
    output_path = output_folder / "creators_with_anomaly_flags.csv"
    df.to_csv(output_path, index=False)

    print(f"\nSaved to {output_path}")

    print("\nTop 10 genuinely flagged channels (worth reviewing first):")
    genuinely_flagged = df[df["anomaly_flag"] == "unusually_high_engagement"]
    top_flagged = genuinely_flagged.sort_values("engagement_z_score", ascending=False).head(10)
    print(top_flagged[["channel_title", "tier", "niche_query", "subscriber_count", "engagement_rate", "engagement_z_score"]])

if __name__ == "__main__":
    main()