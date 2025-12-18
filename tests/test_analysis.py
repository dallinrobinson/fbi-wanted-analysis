import pandas as pd

from fbi_wanted_analysis import fetch_current_wanted, clean_wanted
from fbi_wanted_analysis.analysis import (
    run_analysis_pipeline,
    reward_by_crime_type,
    rq4_volume_trend,
    rq4_reward_trend,
    rq4_priority_by_subject,
    rq4_priority_by_program,
    rq4_priority_by_field_office,
)


def test_package_exports_are_callable():
    # smoke test that __init__ exports the intended functions
    assert callable(fetch_current_wanted)
    assert callable(clean_wanted)


def test_run_analysis_pipeline_prints_message(capsys):
    run_analysis_pipeline()
    captured = capsys.readouterr()
    assert "Running analysis pipeline..." in captured.out


def _fake_cleaned_df_for_rewards():
    # Small helper DF used by multiple tests
    return pd.DataFrame(
        {
            "uid": [1, 2, 3],
            "subjects": [
                ["Terrorism", "Bombing"],
                ["Terrorism"],
                ["Kidnapping"],
            ],
            "reward_has_text": [True, True, True],
            "reward_has_amount": [True, True, False],
            "reward_amount_max_usd": [100_000, 50_000, pd.NA],
            "reward_program": ["FBI", "FBI", "Rewards for Justice"],
            "field_offices": [
                ["denver", "albuquerque"],
                ["denver"],
                ["newyork"],
            ],
            "publication": [
                "2024-01-05",
                "2024-01-20",
                "2024-02-01",
            ],
        }
    )


def test_reward_by_crime_type_basic_stats():
    df = _fake_cleaned_df_for_rewards()

    out = reward_by_crime_type(df)

    # Should contain separate rows for each subject tag
    crime_types = set(out["crime_type"])
    assert {"Terrorism", "Bombing", "Kidnapping"}.issubset(crime_types)

    # Terrorism appears on uid 1 and 2 with rewards 100k and 50k
    terrorism_row = out[out["crime_type"] == "Terrorism"].iloc[0]
    assert terrorism_row["median_reward"] == 75_000  # median of [50k, 100k]
    assert terrorism_row["max_reward"] == 100_000
    assert terrorism_row["listings"] == 2


def test_rq4_volume_trend_groups_by_month():
    df = pd.DataFrame(
        {
            "uid": [1, 2, 3],
            "publication": [
                "2024-01-05",
                "2024-01-20",
                "2024-02-01",
            ],
        }
    )

    out = rq4_volume_trend(df, date_col="publication", freq="M")

    # Two months: Jan (2 listings), Feb (1 listing)
    assert len(out) == 2
    # Periods should be normalized to first of month
    jan_row = out.iloc[0]
    feb_row = out.iloc[1]

    assert jan_row["period"].month == 1
    assert jan_row["listings"] == 2

    assert feb_row["period"].month == 2
    assert feb_row["listings"] == 1


def test_rq4_reward_trend_computes_percentages_and_stats():
    df = _fake_cleaned_df_for_rewards().copy()
    # Make sure publication is parseable datetimes
    df["publication"] = pd.to_datetime(df["publication"])

    out = rq4_reward_trend(df, date_col="publication", freq="M")

    # Expect at least one row per month with data
    assert not out.empty

    # Check January row (two entries, both with text and amount)
    jan = out[out["period"].dt.month == 1].iloc[0]
    assert jan["listings"] == 2
    assert jan["pct_with_reward_text"] == 100.0
    assert jan["pct_with_numeric_reward"] == 100.0
    # Rewards for Jan are 100k and 50k
    assert jan["median_reward_max_usd"] == 75_000
    assert jan["max_reward_max_usd"] == 100_000


def test_rq4_priority_by_subject_ranks_subjects():
    df = _fake_cleaned_df_for_rewards()

    out = rq4_priority_by_subject(df, top_n=5)

    # Should include Terrorism and Kidnapping
    subjects = set(out["subject"])
    assert "Terrorism" in subjects
    assert "Kidnapping" in subjects

    # Terrorism should have more listings than Kidnapping
    terrorism_listings = out.loc[out["subject"] == "Terrorism", "listings"].iloc[0]
    kidnapping_listings = out.loc[out["subject"] == "Kidnapping", "listings"].iloc[0]
    assert terrorism_listings > kidnapping_listings


def test_rq4_priority_by_program_counts_text_and_amounts():
    df = _fake_cleaned_df_for_rewards()

    out = rq4_priority_by_program(df)

    programs = set(out["reward_program"])
    assert "FBI" in programs
    assert "Rewards for Justice" in programs

    fbi_row = out[out["reward_program"] == "FBI"].iloc[0]
    # Two FBI rows, both with text and amount
    assert fbi_row["listings_with_text"] == 2
    assert fbi_row["listings_with_amount"] == 2
    assert fbi_row["median_reward_max_usd"] == 75_000
    assert fbi_row["max_reward_max_usd"] == 100_000


def test_rq4_priority_by_field_office_explodes_lists():
    df = _fake_cleaned_df_for_rewards()

    out = rq4_priority_by_field_office(df, top_n=10)

    offices = set(out["field_office"])
    # denver appears on two rows (uid 1 and 2)
    assert "denver" in offices

    denver_row = out[out["field_office"] == "denver"].iloc[0]
    assert denver_row["listings"] == 2

    # newyork appears once
    assert "newyork" in offices
    ny_row = out[out["field_office"] == "newyork"].iloc[0]
    assert ny_row["listings"] == 1
