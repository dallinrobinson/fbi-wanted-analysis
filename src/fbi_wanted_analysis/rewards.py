from __future__ import annotations

import html
import re
from typing import Any

import pandas as pd


_AMOUNT_RE = re.compile(
    r"""
    \$\s*                                  # dollar sign
    (?P<num>
        (?:\d{1,3}(?:,\d{3})+|\d+)         # 1,000 or 1000 or 5000000
        (?:\.\d+)?                         # optional decimal
    )
    \s*
    (?P<mult>million|billion|thousand|k|m|bn)?  # optional multiplier words/abbr
    """,
    re.IGNORECASE | re.VERBOSE,
)

_TAG_RE = re.compile(r"<[^>]+>")  # strip simple HTML tags


def _normalize_reward_text(x: Any) -> str:
    if x is None or (isinstance(x, float) and pd.isna(x)):
        return ""
    s = str(x).strip()
    if not s:
        return ""
    s = html.unescape(s)
    s = _TAG_RE.sub(" ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def _amount_to_usd(num_str: str, mult: str | None) -> int | None:
    # remove commas
    num_str = num_str.replace(",", "")
    try:
        val = float(num_str)
    except ValueError:
        return None

    mult_norm = (mult or "").lower().strip()

    if mult_norm in {"million", "m"}:
        val *= 1_000_000
    elif mult_norm in {"billion", "bn"}:
        val *= 1_000_000_000
    elif mult_norm in {"thousand", "k"}:
        val *= 1_000

    # dollars as int
    return int(round(val))


def parse_reward(reward_text: Any) -> dict[str, Any]:
    txt = _normalize_reward_text(reward_text)

    has_text = bool(txt)
    is_up_to = "up to" in txt.lower()
    low = txt.lower()
    is_up_to = "up to" in low
    mentions_additional = "additional reward" in low or "additional " in low


    amounts: list[int] = []
    for m in _AMOUNT_RE.finditer(txt):
        usd = _amount_to_usd(m.group("num"), m.group("mult"))
        if usd is not None:
            amounts.append(usd)

    has_amount = len(amounts) > 0

    program = "Other/Unknown"
    low = txt.lower()
    if "rewards for justice" in low:
        program = "Rewards for Justice"
    elif "department of state" in low or "united states department of state" in low:
        program = "State Department"
    elif "department of defense" in low:
        program = "DoD"
    elif "the fbi is offering" in low or low.startswith("the fbi"):
        program = "FBI"

    return {
        "reward_text_clean": txt,
        "reward_has_text": has_text,
        "reward_has_amount": has_amount,
        "reward_amounts_usd": amounts,
        "reward_amount_min_usd": min(amounts) if has_amount else pd.NA,
        "reward_amount_max_usd": max(amounts) if has_amount else pd.NA,
        "reward_is_up_to": is_up_to,
        "reward_mentions_additional": mentions_additional,
        "reward_program": program,
    }
