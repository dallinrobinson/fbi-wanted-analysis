from __future__ import annotations

import requests
from typing import Iterable
import pandas as pd

"""
RESEARCH QUESTIONS
How does the quantity of most wanted cases change over time?

Which U.S regions, states, or FBI field offices have the highest concentration of wanted cases?
How has this distribution shifted historically?

What types of crimes receive the highest reward amounts?

What do trends in rewards and quantity of wanted persons reveal about law enforcement priorities?
"""

FBI_WANTED_URL = "https://api.fbi.gov/wanted/v1/list"


def fetch_current_wanted(page_size: int = 200, pages: int = 1) -> pd.DataFrame:
    rows: list[dict] = []

    for page in range(1, pages + 1):
        params = {"pageSize": page_size, "page": page}
        r = requests.get(FBI_WANTED_URL, params=params, timeout=30)
        r.raise_for_status()
        payload = r.json()
        rows.extend(payload.get("items", []))

    if not rows:
        return pd.DataFrame()

    df = pd.json_normalize(rows)

    keep = [
        c
        for c in df.columns
        if c
        in {
            "uid",
            "title",
            "publication",
            "field_offices",
            "sex",
            "race",
            "subjects",
            "reward_text",
            "caution",
            "details",
        }
    ]
    return df[keep] if keep else df


def run_analysis_pipeline() -> None:
    # Stub kept only so any old scaffold code/tests do not break.
    print("Running analysis pipeline...")


# RESEARCH QUESTION 1: How does the quantity of most wanted cases change over time?
def quantity_over_time(df: pd.DataFrame) -> pd.DataFrame:
    """
    Returns dataFrame with columns:
        snapshot_date
        total_listings
    """

    # Ensure correct types
    df = df.copy()
    df["snapshot_date"] = pd.to_datetime(df["snapshot_date"])

    # Count unique listings per snapshot
    out = (
        df.groupby("snapshot_date")["uid"]
          .nunique()
          .reset_index(name="total_listings")
          .sort_values("snapshot_date")
    )

    return out



# RESEARCH QUESTION 2: Which U.S regions, states, or FBI field offices have the highest concentration of wanted cases?
# How has this distribution shifted historically?
def geographic_concentration_over_time(
    df: pd.DataFrame,
    geography: str,
) -> pd.DataFrame:
    """
    Required columns
        snapshot_date
        uid
        geography

    Returns
    pd.DataFrame with columns:
        snapshot_date
        geography
        listings
        share
    """

    df = df.copy()
    df["snapshot_date"] = pd.to_datetime(df["snapshot_date"])

    # Drop rows without geography info
    df = df.dropna(subset=[geography])

    # Count listings per geography per snapshot
    counts = (
        df.groupby(["snapshot_date", geography])["uid"]
          .nunique()
          .reset_index(name="listings")
    )

    # Compute total listings per snapshot
    totals = (
        counts.groupby("snapshot_date")["listings"]
        .sum()
        .reset_index(name="total")
    )

    # Merge and compute shares
    out = counts.merge(totals, on="snapshot_date")
    out["share"] = out["listings"] / out["total"]

    return out.sort_values(["snapshot_date", "share"], ascending=[True, False])


# RESEARCH QUESTION 3: What types of crimes receive the highest reward amounts?

def reward_by_crime_type(df: pd.DataFrame) -> pd.DataFrame:
    """
    Required columns:
        uid
        subjects
        reward_has_amount
        reward_amount_max_usd

    Returns:
        crime_type
        median_reward
        mean_reward
        max_reward
        listings
    """

    # Keep only listings with numeric rewards
    rewards = df[df["reward_has_amount"].fillna(False)].copy()

    # Drop rows without subjects
    rewards = rewards.dropna(subset=["subjects"])

    # Expand subject lists so each crime type is counted separately
    rewards = rewards.explode("subjects")

    # Clean subject labels
    rewards["subjects"] = rewards["subjects"].astype(str).str.strip()
    rewards = rewards[rewards["subjects"] != ""]

    # Avoid double-counting the same listing within a subject
    rewards = rewards.drop_duplicates(["uid", "subjects"])

    # Aggregate reward statistics by crime type
    out = (
        rewards.groupby("subjects")["reward_amount_max_usd"]
        .agg(
            median_reward="median",
            mean_reward="mean",
            max_reward="max",
            listings="count",
        )
        .sort_values("median_reward", ascending=False)
        .reset_index()
        .rename(columns={"subjects": "crime_type"})
    )

    return out


# RESEARCH QUESTION 4: What do trends in rewards and quantity of wanted persons reveal about law enforcement priorities?


# -----------------------------
# Helpers
# -----------------------------
def _to_datetime_series(s: pd.Series) -> pd.Series:
    return pd.to_datetime(s, errors="coerce", utc=True)


def _add_time_grain(df: pd.DataFrame, date_col: str, freq: str = "M") -> pd.DataFrame:
    """
    Adds a 'period' column based on date_col. freq: "D", "W", "M", "Q", "Y".
    Returns a copy with:
      - period (timestamp at start of period)
    """
    out = df.copy()
    if date_col not in out.columns:
        out["period"] = pd.NaT
        return out

    dt = _to_datetime_series(out[date_col])
    out["period"] = dt.dt.to_period(freq).dt.to_timestamp()
    return out


def _safe_first_subject(x) -> str:
    if isinstance(x, list) and len(x) > 0 and isinstance(x[0], str) and x[0].strip():
        return x[0].strip()
    if isinstance(x, str) and x.strip():
        return x.strip()
    return "Unknown"


def _ensure_reward_cols(df: pd.DataFrame) -> None:
    """
    Raises a helpful error if reward parsing columns are missing.
    """
    needed = {"reward_has_text", "reward_has_amount", "reward_amount_max_usd", "reward_program"}
    missing = sorted(list(needed - set(df.columns)))
    if missing:
        raise ValueError(
            "Missing reward parsing columns. Confirm clean_wanted() applies rewards.parse_reward(). "
            f"Missing: {missing}"
        )


# -----------------------------
# Main analysis functions
# -----------------------------
def rq4_volume_trend(
    df: pd.DataFrame,
    date_col: str = "publication",
    freq: str = "M",
) -> pd.DataFrame:
    """
    Trend in number of listings over time.

    Returns columns:
      period, listings
    """
    tmp = _add_time_grain(df, date_col=date_col, freq=freq)
    tmp = tmp.dropna(subset=["period"])
    if tmp.empty:
        return pd.DataFrame(columns=["period", "listings"])

    out = tmp.groupby("period").size().reset_index(name="listings").sort_values("period")
    return out


def rq4_reward_trend(
    df: pd.DataFrame,
    date_col: str = "publication",
    freq: str = "M",
) -> pd.DataFrame:
    """
    Trend in reward presence + reward amounts over time.

    Returns columns:
      period,
      listings,
      pct_with_reward_text,
      pct_with_numeric_reward,
      median_reward_max_usd,
      p90_reward_max_usd,
      max_reward_max_usd
    """
    _ensure_reward_cols(df)

    tmp = _add_time_grain(df, date_col=date_col, freq=freq)
    tmp = tmp.dropna(subset=["period"])
    if tmp.empty:
        return pd.DataFrame(
            columns=[
                "period",
                "listings",
                "pct_with_reward_text",
                "pct_with_numeric_reward",
                "median_reward_max_usd",
                "p90_reward_max_usd",
                "max_reward_max_usd",
            ]
        )

    # Ensure numeric
    reward_max = pd.to_numeric(tmp["reward_amount_max_usd"], errors="coerce")

    def p90(x: pd.Series) -> float | None:
        x = pd.to_numeric(x, errors="coerce").dropna()
        if x.empty:
            return None
        return float(x.quantile(0.90))

    g = tmp.groupby("period", dropna=False)

    out = pd.DataFrame(
        {
            "period": g.size().index,
            "listings": g.size().values,
            "pct_with_reward_text": (g["reward_has_text"].mean().values * 100.0),
            "pct_with_numeric_reward": (g["reward_has_amount"].mean().values * 100.0),
        }
    )

    # Reward stats computed only on numeric rewards
    tmp_numeric = tmp[tmp["reward_has_amount"].fillna(False)].copy()
    if tmp_numeric.empty:
        out["median_reward_max_usd"] = pd.NA
        out["p90_reward_max_usd"] = pd.NA
        out["max_reward_max_usd"] = pd.NA
        return out.sort_values("period")

    tmp_numeric["reward_amount_max_usd"] = pd.to_numeric(tmp_numeric["reward_amount_max_usd"], errors="coerce")
    gn = tmp_numeric.groupby("period")

    med = gn["reward_amount_max_usd"].median()
    mx = gn["reward_amount_max_usd"].max()
    p90s = gn["reward_amount_max_usd"].apply(p90)

    out = out.merge(med.rename("median_reward_max_usd"), on="period", how="left")
    out = out.merge(p90s.rename("p90_reward_max_usd"), on="period", how="left")
    out = out.merge(mx.rename("max_reward_max_usd"), on="period", how="left")

    return out.sort_values("period")


def rq4_priority_by_subject(
    df: pd.DataFrame,
    top_n: int = 15,
) -> pd.DataFrame:
    """
    Ranks subjects by a simple "priority signal":
      - how often they appear
      - how often they have numeric rewards
      - typical reward size

    Returns columns:
      subject, listings, pct_numeric_reward, median_reward_max_usd
    """
    _ensure_reward_cols(df)

    tmp = df.copy()
    if "subjects" in tmp.columns:
        tmp["subject_primary"] = tmp["subjects"].apply(_safe_first_subject)
    else:
        tmp["subject_primary"] = "Unknown"

    # numeric reward subset for median stats
    tmp["reward_amount_max_usd"] = pd.to_numeric(tmp.get("reward_amount_max_usd", pd.NA), errors="coerce")

    g = tmp.groupby("subject_primary")

    listings = g.size().rename("listings")
    pct_numeric = (g["reward_has_amount"].mean() * 100.0).rename("pct_numeric_reward")

    numeric = tmp[tmp["reward_has_amount"].fillna(False)].copy()
    if numeric.empty:
        med = pd.Series(dtype="float64", name="median_reward_max_usd")
    else:
        med = numeric.groupby("subject_primary")["reward_amount_max_usd"].median().rename("median_reward_max_usd")

    out = pd.concat([listings, pct_numeric, med], axis=1).reset_index().rename(columns={"subject_primary": "subject"})

    # Sort by a practical priority view: more listings, then higher median reward
    out = out.sort_values(["listings", "median_reward_max_usd"], ascending=[False, False]).head(top_n)
    return out


def rq4_priority_by_program(
    df: pd.DataFrame,
) -> pd.DataFrame:
    """
    Shows which reward programs are driving high rewards.
    Useful for interpreting priorities (FBI vs Rewards for Justice, etc).

    Returns columns:
      reward_program, listings_with_text, listings_with_amount, median_reward_max_usd, max_reward_max_usd
    """
    _ensure_reward_cols(df)

    tmp = df.copy()
    tmp["reward_amount_max_usd"] = pd.to_numeric(tmp["reward_amount_max_usd"], errors="coerce")

    g = tmp.groupby("reward_program", dropna=False)

    out = pd.DataFrame(
        {
            "reward_program": g.size().index.astype(str),
            "listings_with_text": g["reward_has_text"].sum().values,
            "listings_with_amount": g["reward_has_amount"].sum().values,
        }
    )

    numeric = tmp[tmp["reward_has_amount"].fillna(False)].copy()
    if numeric.empty:
        out["median_reward_max_usd"] = pd.NA
        out["max_reward_max_usd"] = pd.NA
        return out.sort_values("listings_with_amount", ascending=False)

    gn = numeric.groupby("reward_program")
    out = out.merge(gn["reward_amount_max_usd"].median().rename("median_reward_max_usd"), on="reward_program", how="left")
    out = out.merge(gn["reward_amount_max_usd"].max().rename("max_reward_max_usd"), on="reward_program", how="left")

    return out.sort_values("listings_with_amount", ascending=False)


def rq4_priority_by_field_office(
    df: pd.DataFrame,
    top_n: int = 15,
) -> pd.DataFrame:
    """
    Field office concentration + reward intensity.

    Note: field_offices sometimes comes as a list. This function explodes it.

    Returns columns:
      field_office, listings, pct_numeric_reward, median_reward_max_usd
    """
    _ensure_reward_cols(df)

    tmp = df.copy()
    if "field_offices" not in tmp.columns:
        return pd.DataFrame(columns=["field_office", "listings", "pct_numeric_reward", "median_reward_max_usd"])

    # Normalize to list then explode
    def to_list(x):
        if isinstance(x, list):
            return x
        if isinstance(x, str) and x.strip():
            return [x.strip()]
        return ["Unknown"]

    tmp["field_office"] = tmp["field_offices"].apply(to_list)
    tmp = tmp.explode("field_office")

    tmp["reward_amount_max_usd"] = pd.to_numeric(tmp["reward_amount_max_usd"], errors="coerce")

    g = tmp.groupby("field_office")

    listings = g.size().rename("listings")
    pct_numeric = (g["reward_has_amount"].mean() * 100.0).rename("pct_numeric_reward")

    numeric = tmp[tmp["reward_has_amount"].fillna(False)].copy()
    if numeric.empty:
        med = pd.Series(dtype="float64", name="median_reward_max_usd")
    else:
        med = numeric.groupby("field_office")["reward_amount_max_usd"].median().rename("median_reward_max_usd")

    out = pd.concat([listings, pct_numeric, med], axis=1).reset_index()
    out = out.sort_values(["listings", "median_reward_max_usd"], ascending=[False, False]).head(top_n)

    return out
