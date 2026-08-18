"""
get_youtube_data.py
---------------------
Run this file to pull real creator data from YouTube and save it as a CSV.
"""
import sys
from pathlib import Path

# Add the PROJECT ROOT (not src/) to the path, so "src" can be imported
# as a package - e.g. `from src.settings import ...`
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.fetch_data.youtube import fetch_all_youtube_data
from src.settings import get_data_raw_folder


def main():
    channels_df = fetch_all_youtube_data()

    output_folder = get_data_raw_folder()
    output_path = output_folder / "youtube_creators_real.csv"
    channels_df.to_csv(output_path, index=False)

    print(f"\nSaved {len(channels_df)} real YouTube channels to {output_path}")

    channels_with_engagement = channels_df["engagement_rate"].notna().sum()
    print(f"Channels with a calculated engagement rate: {channels_with_engagement}")


if __name__ == "__main__":
    main()