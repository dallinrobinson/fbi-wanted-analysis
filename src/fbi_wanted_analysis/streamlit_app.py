"""Streamlit app for the FBI Wanted Analysis project (STAT 386)."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from fbi_wanted_analysis.analysis import fetch_current_wanted
from fbi_wanted_analysis.cleaning import clean_wanted


def main() -> None:
    st.set_page_config(page_title="FBI Wanted Analysis", layout="wide")
    st.title("FBI Wanted Analysis")
    st.write("This dashboard pulls current listings from the FBI Wanted API and shows basic summaries.")

    with st.sidebar:
        st.header("Controls")

        pages = st.slider("Pages to fetch", min_value=1, max_value=5, value=1)
        page_size = st.selectbox("Page size", [50, 100, 200], index=2)

        st.divider()

        sex_filter = st.selectbox("Sex", ["All", "Male", "Female", "Unknown"])
        office_search = st.text_input("Field office contains", value="")

        refresh = st.button("Refresh data")

    if refresh or "df" not in st.session_state:
        df_raw = fetch_current_wanted(page_size=page_size, pages=pages)
        st.session_state["df"] = clean_wanted(df_raw)

    df: pd.DataFrame = st.session_state["df"]

    if df.empty:
        st.error("No data returned from the FBI API.")
        return

    filtered = df.copy()

    if sex_filter != "All" and "sex" in filtered.columns:
        if sex_filter == "Unknown":
            filtered = filtered[filtered["sex"].isna() | (filtered["sex"] == "")]
        else:
            filtered = filtered[filtered["sex"] == sex_filter]

    if office_search.strip() and "field_offices" in filtered.columns:
        filtered = filtered[
            filtered["field_offices"].str.contains(office_search.strip(), case=False, na=False)
        ]

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
        c for c in ["title", "publication", "field_offices", "sex", "race", "reward_text"] if c in filtered.columns
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
