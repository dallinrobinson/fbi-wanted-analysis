import pandas as pd
from fbi_wanted_analysis.cleaning import clean_wanted, run_cleaning_pipeline


def test_run_cleaning_pipeline_prints_message(capsys):
    run_cleaning_pipeline()
    captured = capsys.readouterr()
    assert "Running cleaning pipeline..." in captured.out


def test_clean_wanted_parses_publication_and_field_offices_and_rewards():
    raw = pd.DataFrame(
        {
            "uid": [1, 2],
            "publication": ["2024-01-15T00:00:00", "not-a-date"],
            "field_offices": [["denver", "saltlakecity"], None],
            "reward_text": [
                "The FBI is offering a reward of up to $10,000.",
                None,
            ],
        }
    )

    cleaned = clean_wanted(raw)

    # publication -> datetime
    assert pd.api.types.is_datetime64_any_dtype(cleaned["publication"])
    assert cleaned.loc[0, "publication"].year == 2024
    # second row invalid becomes NaT
    assert pd.isna(cleaned.loc[1, "publication"])

    # field_offices list -> comma-separated string
    assert cleaned.loc[0, "field_offices"] == "denver, saltlakecity"
    assert cleaned.loc[1, "field_offices"] == ""

    # reward parsing columns added
    assert "reward_has_text" in cleaned.columns
    assert "reward_has_amount" in cleaned.columns
    assert "reward_amount_max_usd" in cleaned.columns

    # first row: has text and numeric amount
    assert bool(cleaned.loc[0, "reward_has_text"])
    assert bool(cleaned.loc[0, "reward_has_amount"])
    assert cleaned.loc[0, "reward_amount_max_usd"] == 10_000

    # second row: no text, no amount
    assert not bool(cleaned.loc[1, "reward_has_text"])
    assert not bool(cleaned.loc[1, "reward_has_amount"])

