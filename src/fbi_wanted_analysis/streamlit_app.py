"""Streamlit app for the FBI Wanted Analysis project (STAT 386)."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from fbi_wanted_analysis.analysis import fetch_current_wanted
from fbi_wanted_analysis.cleaning import clean_wanted


def _get_unique_subjects(series: pd.Series) -> list[str]:
    vals: set[str] = set()
    for x in series.dropna():
        if isinstance(x, list):
            for item in x:
                if isinstance(item, str) and item.strip():
                    vals.add(item.strip())
        elif isinstance(x, str) and x.strip():
            vals.add(x.strip())
    return sorted(vals)


def main() -> None:
    st.set_page_config(page_title="FBI Wanted Analysis", layout="wide")
    st.title("FBI Wanted Analysis")
    st.write("This dashboard pulls current listings from the FBI Wanted API and shows basic summaries.")

    with st.sidebar:
        st.header("Controls")

        pages = st.slider("Pages to fetch", min_value=1, max_value=22, value=1)

        refresh = st.button("Refresh data")

        st.divider()
        st.subheader("Filters")

        # Safer, high-value filters
        title_keyword = st.text_input("Title keyword contains", value="")
        office_search = st.text_input("Field office contains", value="")

        sex_filter = st.selectbox("Sex", ["All", "Male", "Female", "Unknown"])

        # Optional filters (still useful)
        reward_filter = st.selectbox(
            "Reward filter",
            ["Any", "Has reward text", "No reward text", "Has numeric amount", "No numeric amount"],
)

        race_filter = st.selectbox("Race", ["All", "black", "white", "hispanic", "native", "asian", "Unknown"])

    if refresh or "df" not in st.session_state:
        df_raw = fetch_current_wanted(page_size=50, pages=pages)
        st.session_state["df"] = clean_wanted(df_raw)

    df: pd.DataFrame = st.session_state["df"]

    if df.empty:
        st.error("No data returned from the FBI API.")
        return

    # Date range filter (uses min/max from current pull)
    min_date = None
    max_date = None
    if "publication" in df.columns:
        s = df["publication"].dropna()
        if not s.empty:
            min_date = s.min().date()
            max_date = s.max().date()

    with st.sidebar:
        if min_date and max_date:
            st.caption("Publication date range")
            start_date, end_date = st.date_input(
                "Publication dates",
                value=(min_date, max_date),
                min_value=min_date,
                max_value=max_date,
            )
        else:
            start_date, end_date = None, None

        # Subjects multi-select, only if present
        subjects_selected: list[str] = []
        if "subjects" in df.columns:
            all_subjects = _get_unique_subjects(df["subjects"])
            if all_subjects:
                subjects_selected = st.multiselect("Subjects", all_subjects, default=[])

    filtered = df.copy()

    # Apply filters
    if title_keyword.strip() and "title" in filtered.columns:
        filtered = filtered[
            filtered["title"].fillna("").str.contains(title_keyword.strip(), case=False, na=False)
        ]

    if office_search.strip() and "field_offices" in filtered.columns:
        filtered = filtered[
            filtered["field_offices"].fillna("").str.contains(office_search.strip(), case=False, na=False)
        ]

    if sex_filter != "All" and "sex" in filtered.columns:
        if sex_filter == "Unknown":
            filtered = filtered[filtered["sex"].isna() | (filtered["sex"] == "")]
        else:
            filtered = filtered[filtered["sex"] == sex_filter]

    if reward_filter != "Any":
        # Fallback logic if parsed columns are missing for any reason
        has_text = (
            filtered["reward_text"].notna() & (filtered["reward_text"].astype(str).str.strip() != "")
            if "reward_text" in filtered.columns else pd.Series(False, index=filtered.index)
        )
        has_amount = (
            filtered["reward_has_amount"].fillna(False)
            if "reward_has_amount" in filtered.columns else pd.Series(False, index=filtered.index)
        )

        if reward_filter == "Has reward text":
            filtered = filtered[has_text]
        elif reward_filter == "No reward text":
            filtered = filtered[~has_text]
        elif reward_filter == "Has numeric amount":
            filtered = filtered[has_amount]
        elif reward_filter == "No numeric amount":
            filtered = filtered[~has_amount]

    if race_filter != "All" and "race" in filtered.columns:
        if race_filter == "Unknown":
            filtered = filtered[filtered["race"].isna() | (filtered["race"] == "")]
        else:
            filtered = filtered[filtered["race"] == race_filter]

    if start_date and end_date and "publication" in filtered.columns:
        pub = filtered["publication"]
        filtered = filtered[
            pub.notna()
            & (pub.dt.date >= start_date)
            & (pub.dt.date <= end_date)
        ]

    if subjects_selected and "subjects" in filtered.columns:
        def _has_any_subject(x) -> bool:
            if isinstance(x, list):
                return any(s in x for s in subjects_selected)
            return False

        filtered = filtered[filtered["subjects"].apply(_has_any_subject)]

    # Metrics
    c1, c2, c3 = st.columns(3)
    c1.metric("Listings (filtered)", len(filtered))
    c2.metric("Listings (total fetched)", len(df))

    if "publication" in filtered.columns:
        earliest = filtered["publication"].min()
        c3.metric("Earliest publication", str(earliest.date()) if pd.notna(earliest) else "N/A")
    else:
        c3.metric("Earliest publication", "N/A")

    st.subheader("Data Preview")
    preview_cols = [
        c
        for c in ["title", "publication", "field_offices", "subjects", "sex", "race", "reward_text"]
        if c in filtered.columns
    ]
    st.dataframe(filtered[preview_cols].head(50), use_container_width=True)

    st.divider()

    left, right = st.columns(2)

    with left:
        st.subheader("Top Field Offices")
        if "field_offices" in filtered.columns:
            top_offices = (
                filtered["field_offices"]
                .fillna("")
                .replace("", "Unknown")
                .value_counts()
                .head(15)
            )
            st.bar_chart(top_offices)
        else:
            st.info("field_offices column not available in the current pull.")

    with right:
        st.subheader("Listings Over Time")
        if "publication" in filtered.columns:
            tmp = filtered.dropna(subset=["publication"]).copy()
            if not tmp.empty:
                tmp["month"] = tmp["publication"].dt.to_period("M").dt.to_timestamp()
                by_month = tmp.groupby("month").size().sort_index()
                st.line_chart(by_month)
            else:
                st.info("No rows with publication dates after filtering.")
        else:
            st.info("publication column not available in the current pull.")

    st.divider()
    st.header("Rewards Analysis")

    # Work off the filtered dataset so the user can explore with filters
    has_reward_cols = "reward_has_amount" in filtered.columns and "reward_amount_max_usd" in filtered.columns

    if not has_reward_cols:
        st.info("Reward parsing columns not found. Confirm rewards.py is applied inside clean_wanted().")
    else:
        rewards_df = filtered[filtered["reward_has_amount"].fillna(False)].copy()

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Listings with reward text", int(filtered.get("reward_has_text", pd.Series(False, index=filtered.index)).sum()) if "reward_has_text" in filtered.columns else "N/A")
        c2.metric("Listings with numeric reward", len(rewards_df))
        c3.metric("Max stated reward", f"${int(rewards_df['reward_amount_max_usd'].max()):,}" if not rewards_df.empty and pd.notna(rewards_df["reward_amount_max_usd"].max()) else "N/A")
        c4.metric("Median stated reward", f"${int(rewards_df['reward_amount_max_usd'].median()):,}" if not rewards_df.empty and pd.notna(rewards_df["reward_amount_max_usd"].median()) else "N/A")

        left2, right2 = st.columns(2)

        with left2:
            st.subheader("Top Rewards (Max Amount)")
            if rewards_df.empty:
                st.info("No numeric rewards after filtering.")
            else:
                top_rewards = rewards_df[["title", "reward_amount_max_usd", "reward_program", "subjects", "field_offices"]].sort_values(
                    "reward_amount_max_usd", ascending=False
                ).head(15)
                show_cols = [c for c in ["title", "reward_amount_max_usd", "reward_program", "field_offices"] if c in top_rewards.columns]
                st.dataframe(top_rewards[show_cols], use_container_width=True)

        with right2:
            st.subheader("Reward Amount Distribution")
            if rewards_df.empty:
                st.info("No numeric rewards to chart.")
            else:
                # Bucket rewards to make a readable chart
                bins = [0, 1_000, 5_000, 10_000, 25_000, 50_000, 100_000, 250_000, 500_000, 1_000_000, 5_000_000, 10_000_000, 50_000_000]
                labels = [
                    "≤1k", "1k–5k", "5k–10k", "10k–25k", "25k–50k", "50k–100k",
                    "100k–250k", "250k–500k", "500k–1M", "1M–5M", "5M–10M", "10M+"
                ]
                rewards_df["reward_bucket"] = pd.cut(
                    rewards_df["reward_amount_max_usd"].astype(float),
                    bins=bins,
                    labels=labels,
                    include_lowest=True,
                    right=True,
                )
                bucket_counts = rewards_df["reward_bucket"].value_counts().sort_index()
                st.bar_chart(bucket_counts)

    st.subheader("Median Reward by Subject (First Subject Only)")

    if rewards_df.empty or "subjects" not in rewards_df.columns:
        st.info("No numeric rewards or no subjects available.")
    else:
        def _first_subject(x):
            if isinstance(x, list) and len(x) > 0:
                return str(x[0])
            return "Unknown"

        tmp = rewards_df.copy()
        tmp["subject_primary"] = tmp["subjects"].apply(_first_subject)
        by_subject = (
            tmp.groupby("subject_primary")["reward_amount_max_usd"]
            .median()
            .sort_values(ascending=False)
            .head(15)
        )
        st.bar_chart(by_subject)
        st.caption("Uses the first subject tag only to avoid double-counting listings with multiple tags.")

if __name__ == "__main__":
    main()
