"""Streamlit app for the FBI Wanted Analysis project (STAT 386)."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from fbi_wanted_analysis.analysis import (
    fetch_current_wanted,
    reward_by_crime_type,
    rq4_priority_by_field_office,
    rq4_priority_by_program,
    rq4_priority_by_subject,
    rq4_reward_trend,
    rq4_volume_trend,
)
from fbi_wanted_analysis.cleaning import clean_wanted


# -----------------------------
# Small helpers (UI safe)
# -----------------------------
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


def _safe_contains(series: pd.Series, needle: str) -> pd.Series:
    return series.fillna("").astype(str).str.contains(needle, case=False, na=False)


def _first_subject(x) -> str:
    if isinstance(x, list) and len(x) > 0 and isinstance(x[0], str) and x[0].strip():
        return x[0].strip()
    if isinstance(x, str) and x.strip():
        return x.strip()
    return "Unknown"


def _normalize_field_offices_for_filter(col: pd.Series) -> pd.Series:
    # field_offices is often list[str]; convert to a single string for contains filtering
    def to_text(x) -> str:
        if isinstance(x, list):
            return " ".join([str(i) for i in x if i is not None])
        if x is None:
            return ""
        return str(x)

    return col.apply(to_text)


# -----------------------------
# Main app
# -----------------------------
def main() -> None:
    st.set_page_config(page_title="FBI Wanted Analysis", layout="wide")
    st.title("FBI Wanted Analysis (STAT 386)")
    st.write(
        "This dashboard pulls current listings from the FBI Wanted API, cleans the data, "
        "parses reward text into numeric values, and visualizes trends tied to our four research questions."
    )

    # -----------------------------
    # Sidebar controls
    # -----------------------------
    with st.sidebar:
        st.header("Controls")

        pages = st.slider("Pages to fetch (live API)", min_value=1, max_value=22, value=2)
        refresh = st.button("Refresh data")

        st.divider()
        st.subheader("Filters")

        title_keyword = st.text_input("Title contains", value="")
        office_search = st.text_input("Field office contains", value="")

        sex_filter = st.selectbox("Sex", ["All", "Male", "Female", "Unknown"])

        reward_filter = st.selectbox(
            "Reward filter",
            ["Any", "Has reward text", "No reward text", "Has numeric amount", "No numeric amount"],
        )

        race_filter = st.selectbox("Race", ["All", "black", "white", "hispanic", "native", "asian", "Unknown"])

    # -----------------------------
    # Fetch + cache
    # -----------------------------
    if refresh or "df" not in st.session_state:
        df_raw = fetch_current_wanted(page_size=50, pages=pages)
        st.session_state["df"] = clean_wanted(df_raw)

    df: pd.DataFrame = st.session_state["df"]

    if df.empty:
        st.error("No data returned from the FBI API.")
        return

    # Normalize publication datetime once (prevents .dt errors)
    df = df.copy()
    if "publication" in df.columns:
        df["publication_dt"] = pd.to_datetime(df["publication"], errors="coerce")
    else:
        df["publication_dt"] = pd.NaT

    # -----------------------------
    # Date range + subjects selector (sidebar)
    # -----------------------------
    min_date, max_date = None, None
    if df["publication_dt"].notna().any():
        min_date = df["publication_dt"].min().date()
        max_date = df["publication_dt"].max().date()

    with st.sidebar:
        if min_date and max_date:
            st.caption("Publication date range (based on current pull)")
            start_date, end_date = st.date_input(
                "Publication dates",
                value=(min_date, max_date),
                min_value=min_date,
                max_value=max_date,
            )
        else:
            start_date, end_date = None, None

        subjects_selected: list[str] = []
        if "subjects" in df.columns:
            all_subjects = _get_unique_subjects(df["subjects"])
            if all_subjects:
                subjects_selected = st.multiselect("Subjects", all_subjects, default=[])

    # -----------------------------
    # Apply filters (live)
    # -----------------------------
    filtered = df.copy()

    if title_keyword.strip() and "title" in filtered.columns:
        filtered = filtered[_safe_contains(filtered["title"], title_keyword.strip())]

    if office_search.strip() and "field_offices" in filtered.columns:
        fo_text = _normalize_field_offices_for_filter(filtered["field_offices"])
        filtered = filtered[_safe_contains(fo_text, office_search.strip())]

    if sex_filter != "All" and "sex" in filtered.columns:
        if sex_filter == "Unknown":
            filtered = filtered[filtered["sex"].isna() | (filtered["sex"] == "")]
        else:
            filtered = filtered[filtered["sex"] == sex_filter]

    if reward_filter != "Any":
        has_text = (
            filtered["reward_text"].notna() & (filtered["reward_text"].astype(str).str.strip() != "")
            if "reward_text" in filtered.columns
            else pd.Series(False, index=filtered.index)
        )
        has_amount = (
            filtered["reward_has_amount"].fillna(False)
            if "reward_has_amount" in filtered.columns
            else pd.Series(False, index=filtered.index)
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

    if start_date and end_date:
        pub = filtered["publication_dt"]
        filtered = filtered[pub.notna() & (pub.dt.date >= start_date) & (pub.dt.date <= end_date)]

    if subjects_selected and "subjects" in filtered.columns:

        def _has_any_subject(x) -> bool:
            if isinstance(x, list):
                return any(s in x for s in subjects_selected)
            return False

        filtered = filtered[filtered["subjects"].apply(_has_any_subject)]

    # -----------------------------
    # Overview section
    # -----------------------------
    st.subheader("Overview")
    st.write(
        "Use filters in the sidebar to narrow the listings. All charts below update using the filtered dataset, "
        "so you can explore patterns by field office, crime type, time period, and rewards."
    )

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Listings (filtered)", len(filtered))
    c2.metric("Listings (total fetched)", len(df))

    earliest = filtered["publication_dt"].min()
    latest = filtered["publication_dt"].max()
    c3.metric("Earliest publication", str(earliest.date()) if pd.notna(earliest) else "N/A")
    c4.metric("Latest publication", str(latest.date()) if pd.notna(latest) else "N/A")

    st.subheader("Data Preview (Filtered)")
    preview_cols = [c for c in ["title", "publication_dt", "field_offices", "subjects", "sex", "race", "reward_text"] if c in filtered.columns]
    st.dataframe(filtered[preview_cols].head(50), use_container_width=True)

    # =========================================================
    # RQ1
    # =========================================================
    st.divider()
    st.header("Research Question 1")
    st.subheader("How does the quantity of wanted cases change over time?")
    st.write(
        "We plot counts of listings by month using the publication date. "
        "This answers whether postings cluster in certain time windows."
    )

    # FIX: avoid renaming publication_dt -> publication (creates duplicate publication columns)
    rq1_input = filtered.copy()
    rq1_input["pub_for_trend"] = rq1_input["publication_dt"]

    rq1 = rq4_volume_trend(rq1_input, date_col="pub_for_trend", freq="M")

    if rq1.empty:
        st.info("Not enough publication dates available after filtering to plot RQ1.")
    else:
        rq1_chart = rq1.set_index("period")["listings"]
        st.line_chart(rq1_chart)
        st.caption("Counts are based on publication dates in the current pull. This is not full historical coverage.")

    # =========================================================
    # RQ2
    # =========================================================
    st.divider()
    st.header("Research Question 2")
    st.subheader("Which FBI field offices have the highest concentration of cases?")
    st.write(
        "We summarize the filtered listings by field office. Field offices often appear as a list, "
        "so we explode the list to count each field office tag."
    )

    if "field_offices" not in filtered.columns:
        st.info("field_offices column not available in the current pull.")
    else:
        tmp = filtered.copy()
        tmp["field_offices"] = tmp["field_offices"].apply(
            lambda x: x if isinstance(x, list) else ([] if x is None else [str(x)])
        )
        tmp = tmp.explode("field_offices")
        tmp["field_offices"] = tmp["field_offices"].fillna("").astype(str).str.strip()
        tmp = tmp[tmp["field_offices"] != ""]

        top_offices = tmp["field_offices"].value_counts().head(20)
        st.bar_chart(top_offices)
        st.caption("This shows concentration, not causality. A field office tag can reflect jurisdiction or investigation ownership.")

    # =========================================================
    # RQ3
    # =========================================================
    st.divider()
    st.header("Research Question 3")
    st.subheader("What types of crimes receive the highest reward amounts?")
    st.write(
        "We use the parsed numeric reward amounts (from rewards.py) and group by subject tags "
        "to estimate which crime types tend to have higher rewards."
    )

    if "reward_has_amount" not in filtered.columns or "reward_amount_max_usd" not in filtered.columns:
        st.info("Reward parsing columns not found. Confirm rewards.py is applied inside clean_wanted().")
    else:
        rq3 = reward_by_crime_type(filtered)
        if rq3.empty:
            st.info("No numeric rewards available after filtering.")
        else:
            show = rq3.head(20).copy()
            for col in ["median_reward", "mean_reward", "max_reward"]:
                if col in show.columns:
                    show[col] = pd.to_numeric(show[col], errors="coerce").round(0)

            st.dataframe(show, use_container_width=True)
            st.caption("Subjects come from FBI tags. A listing can have multiple subjects. We de-duplicate by (uid, subject).")

    # =========================================================
    # RQ4
    # =========================================================
    st.divider()
    st.header("Research Question 4")
    st.subheader("What do trends in rewards and quantity reveal about law enforcement priorities?")
    st.write(
        "We treat two signals as proxies for priority:\n"
        "1) volume of listings over time, and\n"
        "2) reward intensity (how often rewards appear, and how large they are).\n"
        "This does not prove intent. It shows patterns consistent with higher urgency or higher-stakes cases."
    )

    with st.expander("RQ4 settings", expanded=False):
        freq_label = st.selectbox("Time grain", ["Monthly", "Weekly", "Quarterly"], index=0)
        freq = {"Weekly": "W", "Monthly": "M", "Quarterly": "Q"}[freq_label]

    # FIX: avoid renaming publication_dt -> publication
    rq4_input = filtered.copy()
    rq4_input["pub_for_trend"] = rq4_input["publication_dt"]

    try:
        rq4_trend = rq4_reward_trend(rq4_input, date_col="pub_for_trend", freq=freq)
    except Exception as e:
        rq4_trend = pd.DataFrame()
        st.warning(f"RQ4 trend failed: {e}")

    if rq4_trend.empty:
        st.info("Not enough reward + publication data available after filtering to plot RQ4 trends.")
    else:
        left, right = st.columns(2)

        with left:
            st.subheader("Reward prevalence over time")
            chart = rq4_trend.set_index("period")[["pct_with_reward_text", "pct_with_numeric_reward"]]
            st.line_chart(chart)
            st.caption("Percent of listings in each period that mention a reward or include a numeric amount.")

        with right:
            st.subheader("Reward size over time")
            chart = rq4_trend.set_index("period")[["median_reward_max_usd", "p90_reward_max_usd", "max_reward_max_usd"]]
            st.line_chart(chart)
            st.caption("Median, 90th percentile, and max of stated reward max amounts (USD).")

    st.subheader("Where do higher rewards cluster?")
    cA, cB, cC = st.columns(3)

    with cA:
        st.markdown("**By subject (primary tag)**")
        try:
            subj = rq4_priority_by_subject(filtered, top_n=15)
            st.dataframe(subj, use_container_width=True)
        except Exception as e:
            st.info(f"Not available: {e}")

    with cB:
        st.markdown("**By reward program**")
        try:
            prog = rq4_priority_by_program(filtered)
            st.dataframe(prog, use_container_width=True)
        except Exception as e:
            st.info(f"Not available: {e}")

    with cC:
        st.markdown("**By field office**")
        try:
            fo = rq4_priority_by_field_office(filtered, top_n=15)
            st.dataframe(fo, use_container_width=True)
        except Exception as e:
            st.info(f"Not available: {e}")

    st.caption(
        "Interpretation idea: if certain subjects or offices have both high volume and high reward intensity, "
        "those categories may reflect more urgent or higher-stakes enforcement attention in the dataset you pulled."
    )


if __name__ == "__main__":
    main()
