"""
main.py
---------
Styled Streamlit dashboard matching the reference design - red accent
cards, gradient area chart, ranked list, and a data table with visual
progress bars.
"""
import sys
from pathlib import Path
import streamlit as st
import pandas as pd
import plotly.graph_objects as go


TIER_LABELS = {
    "nano": "Small & Engaged",
    "micro": "Growing",
    "macro": "Established",
    "mega": "Celebrity-Level",
}

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.database.load_db import get_engine
from src.settings import get_supabase_connection_params
from src.analyze.budget_planner import (
    add_synthetic_cost, add_engaged_reach_metrics,
    summarize_by_tier, recommend_budget_split
)
from src.ask_ai.router import ask_question


st.set_page_config(page_title="Creator ROI Intelligence", layout="wide", page_icon="📊")

# ---- custom CSS for the card look ----
st.markdown("""
<style>
.kpi-card {
    background: var(--secondary-background-color);
    border-left: 4px solid #E63946;
    border-radius: 10px;
    padding: 16px 18px;
    margin-bottom: 8px;
}
.kpi-label { font-size: 13px; opacity: 0.65; margin-bottom: 4px; }
.kpi-value { font-size: 26px; font-weight: 700; }
.kpi-delta { font-size: 12px; color: #E63946; margin-top: 2px; }

.rank-row {
    display: flex; align-items: center; justify-content: space-between;
    padding: 6px 0; font-size: 13px;
}
.rank-bar-bg {
    background: rgba(230,57,70,0.12); border-radius: 6px; height: 6px;
    width: 55%; overflow: hidden;
}
.rank-bar-fill { background: #E63946; height: 6px; }
</style>
""", unsafe_allow_html=True)


@st.cache_data
def load_data():
    connection_params = get_supabase_connection_params()
    engine = get_engine(connection_params)
    return pd.read_sql("SELECT * FROM creators", engine)


def get_cached_engine():
    return get_engine(get_supabase_connection_params())


def kpi_card(label, value, delta=None):
    delta_html = f'<div class="kpi-delta">{delta}</div>' if delta else ""
    st.markdown(f"""
    <div class="kpi-card">
        <div class="kpi-label">{label}</div>
        <div class="kpi-value">{value}</div>
        {delta_html}
    </div>
    """, unsafe_allow_html=True)


def show_kpi_row(df):
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        kpi_card("Total Creators", f"{len(df):,}")
    with col2:
        kpi_card("Avg Engagement Rate", f"{df['engagement_rate'].mean():.2%}")
    with col3:
        flagged = (df["anomaly_flag"] == "unusually_high_engagement").sum()
        kpi_card("Flagged for Review", flagged)
    with col4:
        kpi_card("Creator Tiers", df["tier"].nunique())


def show_trend_and_ranking(df):
    col1, col2 = st.columns([2, 1])

    with col1:
        st.markdown("**Top Categories by Engagement**")
        tier_order = ["nano", "micro", "macro", "mega"]
        tier_avg = df.groupby("tier")["engagement_rate"].mean().reindex(tier_order)
        tier_display_labels = [TIER_LABELS[t] for t in tier_order]

        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=tier_avg.index, y=tier_avg.values,
            mode="lines", line=dict(color="#E63946", width=3),
            fill="tozeroy", fillcolor="rgba(230,57,70,0.15)",
        ))
        fig.update_layout(
            height=280, margin=dict(l=10, r=10, t=10, b=10),
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            xaxis=dict(showgrid=False), yaxis=dict(showgrid=False, tickformat=".1%"),
        )
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.markdown("**Top Categories by Engagement**")
        niche_avg = df.groupby("niche_query")["engagement_rate"].mean().sort_values(ascending=False).head(8)
        max_val = niche_avg.max()

        for niche, value in niche_avg.items():
            pct_width = int((value / max_val) * 100)
            st.markdown(f"""
            <div class="rank-row">
                <span>{niche}</span>
                <div class="rank-bar-bg"><div class="rank-bar-fill" style="width:{pct_width}%"></div></div>
                <span>{value:.2%}</span>
            </div>
            """, unsafe_allow_html=True)


def show_fraud_table(df):
    st.markdown("**Anomaly Radar** — statistically unusual engagement, flagged for human review")

    flagged = df[df["anomaly_flag"] == "unusually_high_engagement"].copy()
    flagged = flagged.sort_values("engagement_z_score", ascending=False)
    flagged["z_score_visual"] = flagged["engagement_z_score"] / flagged["engagement_z_score"].max()

    st.dataframe(
        flagged[["channel_title", "tier", "niche_query", "subscriber_count", "engagement_rate", "z_score_visual"]],
        column_config={
            "channel_title": "Creator",
            "tier_label": "Tier",
            "niche_query": "Category",
            "subscriber_count": st.column_config.NumberColumn("Subscribers", format="%d"),
            "engagement_rate": st.column_config.NumberColumn("Engagement", format="%.4f"),
            "z_score_visual": st.column_config.ProgressColumn("Unusualness", min_value=0, max_value=1),
        },
        use_container_width=True, hide_index=True,
    )


def show_budget_section(df):
    st.markdown("**Budget Allocation Planner** — real engagement + modeled INR cost-per-post")

    budget = st.number_input("Total budget (INR)", min_value=10_000, value=500_000, step=10_000)

    df_with_cost = add_synthetic_cost(df.copy())
    df_with_cost = add_engaged_reach_metrics(df_with_cost)
    tier_summary = summarize_by_tier(df_with_cost)
    plan = recommend_budget_split(tier_summary, budget)
    plan["share_visual"] = plan["pct_of_budget"] / 100

    st.dataframe(
        plan[["tier", "allocated_inr", "share_visual", "avg_engagement_rate", "expected_engaged_reach"]],
        column_config={
            "tier": "Tier",
            "tier_label": "Tier",
            "allocated_inr": st.column_config.NumberColumn("Allocated (INR)", format="₹%d"),
            "share_visual": st.column_config.ProgressColumn("Share", min_value=0, max_value=1, format="%.0f%%"),
            "avg_engagement_rate": st.column_config.NumberColumn("Avg Engagement", format="%.4f"),
            "expected_engaged_reach": st.column_config.NumberColumn("Expected Reach", format="%d"),
        },
        use_container_width=True, hide_index=True,
    )
def show_creator_profile(df):
    st.markdown("**Select a creator**")
    creator_names = sorted(df["channel_title"].dropna().unique().tolist())
    selected = st.selectbox("creator_select", creator_names, label_visibility="collapsed")

    row = df[df["channel_title"] == selected].iloc[0]

    # header row - name, category, tier, country
    st.markdown(f"### {row['channel_title']}")
    badge_col1, badge_col2, badge_col3 = st.columns(3)
    badge_col1.markdown(f"**Category:** {row['niche_query']}")
    badge_col2.markdown(f"**Tier:** {TIER_LABELS.get(row['tier'], row['tier'])}")
    badge_col3.markdown(f"**Country:** {row['country'] if row['country'] else 'Unknown'}")

    st.write("")

    # 4 real metric cards, same style as the overview KPI cards
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        kpi_card("Followers", f"{int(row['subscriber_count']):,}")
    with c2:
        eng = f"{row['engagement_rate']:.2%}" if pd.notna(row['engagement_rate']) else "N/A"
        kpi_card("Engagement Rate", eng)
    with c3:
        kpi_card("Total Views", f"{int(row['view_count']):,}")
    with c4:
        kpi_card("Videos Posted", f"{int(row['video_count']):,}")

    st.write("")

    # comparison bars - real substitute for the "growth/demographic" panels,
    # since we don't have real historical or demographic data
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("**vs Tier Average (Engagement Rate)**")
        tier_avg = df[df["tier"] == row["tier"]]["engagement_rate"].mean()
        compare_df = pd.DataFrame({
            "who": ["This Creator", "Tier Average"],
            "engagement_rate": [row["engagement_rate"], tier_avg]
        }).set_index("who")
        st.bar_chart(compare_df)

    with col2:
        st.markdown("**vs Category Average (Engagement Rate)**")
        cat_avg = df[df["niche_query"] == row["niche_query"]]["engagement_rate"].mean()
        compare_df2 = pd.DataFrame({
            "who": ["This Creator", "Category Average"],
            "engagement_rate": [row["engagement_rate"], cat_avg]
        }).set_index("who")
        st.bar_chart(compare_df2)

    st.write("")
    st.markdown("**Recent Video Performance** (average of last 5 videos sampled)")
    perf_col1, perf_col2, perf_col3 = st.columns(3)
    perf_col1.metric("Avg Views", f"{row['avg_recent_views']:.0f}" if pd.notna(row['avg_recent_views']) else "N/A")
    perf_col2.metric("Avg Likes", f"{row['avg_recent_likes']:.0f}" if pd.notna(row['avg_recent_likes']) else "N/A")
    perf_col3.metric("Avg Comments", f"{row['avg_recent_comments']:.0f}" if pd.notna(row['avg_recent_comments']) else "N/A")

    if row["anomaly_flag"] == "unusually_high_engagement":
        st.warning(
            f"⚠️ Flagged for unusually high engagement (z-score: {row['engagement_z_score']:.2f}) "
            "- worth manual review, not confirmed fraud."
        )

def show_chat_section(df):
    """Now behaves like a top search bar - no separate label or button,
    just type and press Enter."""
    question = st.text_input(
        "search",
        placeholder="🔍 Ask anything about your creators...",
        label_visibility="collapsed",
        max_chars=300,
    )

    if question.strip() == "":
        return

    # simple per-session rate limit
    if "question_count" not in st.session_state:
        st.session_state.question_count = 0

    if st.session_state.question_count >= 15:
        st.warning("You've reached the question limit for this session. Refresh the page to continue.")
        return

    with st.spinner("Thinking..."):
        try:
            engine = get_cached_engine()
            answer = ask_question(question, engine, df)
        except Exception as e:
            print(f"[ERROR] Question failed: {e}")
            st.error("Sorry, I couldn't answer that question. Try rephrasing it, or ask something simpler.")
            return

    st.session_state.question_count += 1

    if isinstance(answer, pd.DataFrame):
        if len(answer) == 0:
            st.info("No results found for that question.")
        else:
            st.dataframe(answer, use_container_width=True, hide_index=True)
    else:
        st.write(answer)


def main():
    df = load_data()

    title_col, search_col = st.columns([1, 2])
    with title_col:
        st.title("Creator ROI Intelligence")
    with search_col:
        st.write("")
        show_chat_section(df)

    st.write("")

    tab1, tab2 = st.tabs(["Overview", "Creator Profile"])

    with tab1:
        show_kpi_row(df)
        st.divider()
        show_trend_and_ranking(df)
        st.divider()
        show_fraud_table(df)
        st.divider()
        show_budget_section(df)

    with tab2:
        show_creator_profile(df)


if __name__ == "__main__":
    main()