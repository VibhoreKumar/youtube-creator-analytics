"""
load_db.py
------------
Loads our final cleaned/analyzed data into a real Postgres database
(hosted on Supabase), and provides a reusable way to connect to it.
"""
import pandas as pd
from sqlalchemy import create_engine, text
from sqlalchemy.engine import URL


def get_engine(connection_params):
    """Builds a SQLAlchemy engine from connection pieces - reused anywhere
    we need to talk to the database."""
    db_url = URL.create(
        drivername="postgresql+psycopg2",
        username=connection_params["user"],
        password=connection_params["password"],
        host=connection_params["host"],
        port=connection_params["port"],
        database=connection_params["database"],
    )
    return create_engine(db_url)


def load_creators_into_db(csv_path, connection_params):
    df = pd.read_csv(csv_path)
    engine = get_engine(connection_params)

    df.to_sql("creators", engine, if_exists="replace", index=False)

    with engine.connect() as conn:
        result = conn.execute(text("SELECT COUNT(*) FROM creators"))
        row_count = result.scalar()
        print(f"Loaded {row_count} rows into the 'creators' table on Supabase")

        result = conn.execute(text(
            "SELECT column_name, data_type FROM information_schema.columns "
            "WHERE table_name = 'creators'"
        ))
        print("\nColumns in the table:")
        for row in result:
            print(f"  {row[0]} ({row[1]})")

    engine.dispose()