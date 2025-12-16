from __future__ import annotations
from fbi_wanted_analysis.rewards import parse_reward

import pandas as pd


def clean_wanted(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    if "publication" in df.columns:
        df["publication"] = pd.to_datetime(df["publication"], errors="coerce")

    if "field_offices" in df.columns:
        df["field_offices"] = df["field_offices"].apply(
            lambda x: ", ".join(x) if isinstance(x, list) else (x if pd.notna(x) else "")
        )

    if "reward_text" in df.columns:
        parsed = df["reward_text"].apply(parse_reward).apply(pd.Series)
        df = pd.concat([df, parsed], axis=1)

    return df


def run_cleaning_pipeline() -> None:
    # Stub kept only so any old scaffold code/tests do not break.
    print("Running cleaning pipeline...")
