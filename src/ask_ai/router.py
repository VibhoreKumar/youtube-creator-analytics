"""
router.py
-----------
Decides whether a question needs an exact SQL answer or a fuzzy
explanation, then sends it to the right helper.
"""
from google import genai
from google.genai import types

from src.settings import get_gemini_api_key
from src.ask_ai.sql_helper import run_sql_question
from src.ask_ai.explain_helper import answer_explanatory_question


def classify_question(question):
    client = genai.Client(api_key=get_gemini_api_key())

    system_prompt = """Classify the question as either "sql" or "explain".

Use "sql" for questions asking for exact numbers, averages, counts, or
comparisons - things a database query can compute directly.
Example: "What is the average engagement rate for micro creators?"

Use "explain" for open-ended questions asking for reasoning or explanation.
Example: "Why might this creator look suspicious?"

Reply with ONLY the single word: sql OR explain
"""

    response = client.models.generate_content(
        model="gemini-3.5-flash-lite",
        contents=question,
        config=types.GenerateContentConfig(system_instruction=system_prompt),
    )

    answer = response.text.strip().lower()
    return "sql" if "sql" in answer else "explain"


def ask_question(question, engine, full_df):
    question_type = classify_question(question)
    print(f"Question type: {question_type}")

    if question_type == "sql":
        return run_sql_question(question, engine)
    else:
        return answer_explanatory_question(question, full_df)