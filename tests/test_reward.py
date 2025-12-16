from fbi_wanted_analysis.rewards import parse_reward

def test_parse_reward_extracts_amounts_and_multipliers():
    d = parse_reward("Reward of up to $2 million and an additional $200,000.")
    assert d["reward_has_amount"] is True
    assert d["reward_amount_max_usd"] == 2_000_000
