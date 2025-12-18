import pandas as pd
from fbi_wanted_analysis.rewards import parse_reward


def test_parse_reward_extracts_amounts_and_multipliers():
    text = "Reward of up to $2 million and an additional $200,000."
    d = parse_reward(text)

    assert d["reward_has_text"] is True
    assert d["reward_has_amount"] is True
    # max should be 2M (not 200k)
    assert d["reward_amount_max_usd"] == 2_000_000
    assert d["reward_amount_min_usd"] == 200_000
    assert d["reward_is_up_to"] is True
    assert d["reward_mentions_additional"] is True


def test_parse_reward_handles_plain_dollar_amount():
    text = "The FBI is offering a reward of $50,000 for information."
    d = parse_reward(text)

    assert d["reward_has_text"] is True
    assert d["reward_has_amount"] is True
    assert d["reward_amount_max_usd"] == 50_000
    assert d["reward_program"] == "FBI"


def test_parse_reward_handles_no_amount_and_none_input():
    # No dollar sign, should not detect amounts
    text = "Information leading to arrest may be eligible for a reward."
    d = parse_reward(text)
    assert d["reward_has_text"] is True
    assert d["reward_has_amount"] is False
    assert pd.isna(d["reward_amount_max_usd"])

    # None input
    d_none = parse_reward(None)
    assert d_none["reward_has_text"] is False
    assert d_none["reward_has_amount"] is False
    assert pd.isna(d_none["reward_amount_max_usd"])
