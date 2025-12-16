from __future__ import annotations

import requests
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

