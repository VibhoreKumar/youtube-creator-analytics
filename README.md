# DealSense — Creator ROI Intelligence

A dashboard that helps brands find and evaluate real YouTube creators for
sponsorships/endorsements — real engagement data, anomaly detection for
suspicious accounts, budget allocation recommendations, and a natural-language
"ask your data" search bar powered by Gemini.

**Live app:** https://youtube-creator-analytics-jflipbqujlpcp4xnvmmuaa.streamlit.app/

> **Data note:** This project combines real YouTube creator data with a
> clearly-labeled synthetic cost layer, since real brand-to-creator campaign
> spend isn't publicly available anywhere. See
> [`docs/about_the_data.md`](docs/about_the_data.md) for exactly what's real
> vs. modeled, and known limitations.

---

## What it does

- **Pulls real creator data** from the YouTube Data API v3 — actual
  subscriber counts, view counts, and engagement rates computed from each
  channel's most recent videos' real likes/comments
- **Flags statistically unusual engagement** using a z-score anomaly
  detector, grouped by category + tier so a gaming channel is only compared
  to other gaming channels, not the whole platform
- **Recommends a budget split** across creator tiers using real engagement
  data and a modeled (synthetic, labeled) INR cost-per-post
- **Answers plain-English questions** about the data via a router that
  sends exact-number questions to real generated SQL, and open-ended
  questions to a grounded explanation — no hallucinated numbers
- **Ships as a live, deployed dashboard** — not just notebooks or scripts

---

## Architecture
YouTube Data API v3
│
▼
Fetch (Python) ──► Clean & tier-assign ──► Anomaly detection
│ │
▼ ▼
Supabase (Postgres) ◄──────────────────── Budget planner
│
▼
Streamlit app ◄──► Gemini (router: text-to-SQL / explain)

## Pipeline

Run in order to rebuild the dataset from scratch:

```bash
python run/get_youtube_data.py     # pull real creators from YouTube
python run/clean_data.py           # clean + assign tiers
python run/check_for_fraud.py      # flag anomalous engagement
python run/plan_budget.py          # generate budget recommendations
python run/load_database.py        # load everything into Postgres
streamlit run app/main.py          # launch the dashboard
```

---

