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
        reward_filter = st.selectbox("Reward text", ["Any", "Has reward text", "No reward text"])

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

    if reward_filter != "Any" and "reward_text" in filtered.columns:
        has_reward = filtered["reward_text"].notna() & (filtered["reward_text"].astype(str).str.strip() != "")
        if reward_filter == "Has reward text":
            filtered = filtered[has_reward]
        elif reward_filter == "No reward text":
            filtered = filtered[~has_reward]

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


if __name__ == "__main__":
    main()
