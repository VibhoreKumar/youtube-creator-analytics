"""
ask_question.py
------------------
Run this to ask questions about the creator dataset in plain English.

Usage:
    python run/ask_question.py
"""
import sys
from pathlib import Path
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.database.load_db import get_engine
from src.settings import get_supabase_connection_params
from src.ask_ai.router import ask_question


def main():
    connection_params = get_supabase_connection_params()
    engine = get_engine(connection_params)

    full_df = pd.read_sql("SELECT * FROM creators", engine)

    print("Ask a question about the creator dataset (type 'quit' to stop):")
    while True:
        question = input("\n> ")
        if question.strip().lower() == "quit":
            break

        answer = ask_question(question, engine, full_df)

        if isinstance(answer, pd.DataFrame):
            print(answer.to_string(index=False))
        else:
            print(answer)


if __name__ == "__main__":
    main()