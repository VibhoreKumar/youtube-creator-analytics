"""
explain_helper.py
-------------------
Answers fuzzy/explanatory questions using Gemini, grounded only in real
rows found via simple keyword matching (a simplified form of RAG).
"""
from google import genai
from google.genai import types

from src.settings import get_gemini_api_key


def find_relevant_rows(question, df, max_rows=15):
    question_lower = question.lower().strip()

    # Priority 1: does a specific channel name appear in the question?
    # This is checked FIRST and separately, so a specific name always wins
    # over a broader niche/tier match.
    name_matches = df[df["channel_title"].apply(
        lambda title: str(title).lower().strip() in question_lower
    )]
    if len(name_matches) > 0:
        return name_matches.head(max_rows)

    # Priority 2: no specific channel named - fall back to niche/tier keywords
    keyword_matches = df[df.apply(
        lambda row: (
            str(row["tier"]).lower() in question_lower or
            str(row["niche_query"]).lower() in question_lower
        ), axis=1
    )]
    if len(keyword_matches) > 0:
        return keyword_matches.head(max_rows)

    # Priority 3: nothing matched at all - show the most unusual flagged creators
    flagged = df[df["anomaly_flag"] == "unusually_high_engagement"]
    if "engagement_z_score" in df.columns:
        flagged = flagged.sort_values("engagement_z_score", ascending=False)
    return flagged.head(max_rows)


def rows_to_text(rows_df):
    lines = []
    for _, row in rows_df.iterrows():
        lines.append(
            f"- {row['channel_title']} | tier: {row['tier']} | niche: {row['niche_query']} | "
            f"subscribers: {row['subscriber_count']} | engagement_rate: {row['engagement_rate']} | "
            f"flag: {row['anomaly_flag']}"
        )
    return "\n".join(lines)


def answer_explanatory_question(question, df):
    client = genai.Client(api_key=get_gemini_api_key())

    relevant_rows = find_relevant_rows(question, df)
    context_text = rows_to_text(relevant_rows)

    system_prompt = f"""You answer questions about real YouTube creator data.
Only use the data given below - never make up numbers or facts.
If the data doesn't have enough information to answer, say so clearly.

Relevant data:
{context_text}
"""

    response = client.models.generate_content(
        model="gemini-3.5-flash-lite",
        contents=question,
        config=types.GenerateContentConfig(system_instruction=system_prompt),
    )

    return response.text