import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.database.load_db import load_creators_into_db
from src.settings import get_supabase_connection_params


def main():
    csv_path = Path("data/final/creators_with_budget_metrics.csv")
    connection_params = get_supabase_connection_params()

    load_creators_into_db(csv_path, connection_params)


if __name__ == "__main__":
    main()