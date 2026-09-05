"""
keep_alive.py
---------------
Runs a trivial query against Supabase to reset its "last activity" clock,
preventing the free-tier project from auto-pausing after 7 days idle.

Meant to be run on a schedule via GitHub Actions, not manually.
"""
import sys
from pathlib import Path
from sqlalchemy import text

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.database.load_db import get_engine
from src.settings import get_supabase_connection_params


def main():
    engine = get_engine(get_supabase_connection_params())
    with engine.connect() as conn:
        result = conn.execute(text("SELECT 1"))
        result.scalar()
    print("Keep-alive ping successful - Supabase project stays active.")


if __name__ == "__main__":
    main()