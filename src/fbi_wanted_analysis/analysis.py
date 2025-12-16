from __future__ import annotations

import requests
import pandas as pd

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
