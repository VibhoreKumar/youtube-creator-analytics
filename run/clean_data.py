import sys
from pathlib import Path
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.clean_data.clean import clean_youtube_data


def main():
    raw_path = Path("data/raw/youtube_creators_real.csv")
    df = pd.read_csv(raw_path)

    cleaned_df = clean_youtube_data(df)

    output_folder = Path("data/cleaned")
    output_folder.mkdir(parents=True, exist_ok=True)
    output_path = output_folder / "youtube_creators_clean.csv"
    cleaned_df.to_csv(output_path, index=False)

    print(f"\nSaved cleaned data to {output_path}")


if __name__ == "__main__":
    main()