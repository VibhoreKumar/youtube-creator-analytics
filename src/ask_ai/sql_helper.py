"""
sql_helper.py
--------------
Turns a plain-English question into a real SQL query using Gemini, checks
it's safe (SELECT-only), runs it on our Postgres database, and returns
the result.
"""
from google import genai
from google.genai import types
import pandas as pd
from sqlalchemy import text

from src.settings import get_gemini_api_key

TABLE_SCHEMA = """
Table name: creators

Columns:
- channel_title (text)
- niche_query (text) - e.g. Beauty, Fitness, Tech Review, Gaming, etc.
- tier (text) - one of: nano, micro, macro, mega
- subscriber_count (integer)
- view_count (integer)
- video_count (integer)
- engagement_rate (float)
- anomaly_flag (text) - one of: normal, unusually_high_engagement, sample_too_small, not_enough_data
- cost_per_post_inr (float) - modeled/synthetic cost estimate in INR
- engaged_reach_per_rupee (float)
- country (text)
- channel_age_days (integer)
"""


def generate_sql_from_question(question):
    client = genai.Client(api_key=get_gemini_api_key())

    system_prompt = f"""You translate questions about a creator dataset into PostgreSQL queries.

{TABLE_SCHEMA}

Rules:
- Only write SELECT queries. Never INSERT, UPDATE, DELETE, or DROP.
- Reply with ONLY the SQL query - no explanation, no markdown formatting.
- Use ROUND() to keep decimal numbers readable.
"""

    response = client.models.generate_content(
        model="gemini-3.5-flash-lite",
        contents=question,
        config=types.GenerateContentConfig(system_instruction=system_prompt),
    )

    sql_query = response.text.strip()
    sql_query = sql_query.replace("```sql", "").replace("```", "").strip()
    return sql_query


def is_safe_query(sql_query):
    lowered = sql_query.strip().lower()
    if not lowered.startswith("select"):
        return False
    dangerous_words = ["insert", "update", "delete", "drop", "alter", "truncate"]
    for word in dangerous_words:
        if word in lowered:
            return False
    return True


def run_sql_question(question, engine):
    sql_query = generate_sql_from_question(question)
    print(f"Generated SQL:\n{sql_query}\n")

    if not is_safe_query(sql_query):
        raise ValueError("Generated query failed the safety check - refusing to run it.")

    with engine.connect() as conn:
        result_df = pd.read_sql(text(sql_query), conn)

    return result_df