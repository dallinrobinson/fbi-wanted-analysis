# fbi-wanted-analysis

A Python package for retrieving, cleaning, and analyzing data from the FBI Wanted API. This package streamlines FBI dataset exploration into a simple workflow: download → clean → analyze.

## Features

- Live retrieval from the official FBI Wanted API
- Automated cleaning of publication dates, field office data, and reward text
- Reward parsing into consistent numeric values (USD)
- Analysis functions for exploring:
  - reward trends
  - geographic patterns
  - crime subject comparisons
  - time-series volume patterns

## Installation

```bash
pip install fbi-wanted-analysis
```

## Quick Start

```python
from fbi_wanted_analysis import fetch_current_wanted, clean_wanted

# Pull current FBI wanted data (up to 200 items per page)
df = fetch_current_wanted(pages=2)

# Clean and parse
cleaned = clean_wanted(df)

print(cleaned.head())
```

## Example: Reward amounts by crime type

```python
from fbi_wanted_analysis import fetch_current_wanted, clean_wanted
from fbi_wanted_analysis.analysis import reward_by_crime_type

df = clean_wanted(fetch_current_wanted(pages=4))
summary = reward_by_crime_type(df)

print(summary.head())
```

### Run the Streamlit App

To launch the interactive visualization dashboard:

```bash
streamlit run src/fbi_wanted_analysis/streamlit_app.py
```

This dashboard provides:
- Volume over time
- Reward intensity trends
- Subject‑level reward patterns
- Field office comparisons

## Project Purpose

This package supports statistical exploration, reproducible reporting, and real-world data analysis. It is also used in a Streamlit dashboard that visualizes reward intensity, volume patterns over time, crime subject distribution, and field-office concentration.

## Contents

Main modules:

- `analysis.py` — analytical methods for research questions
- `cleaning.py` — parses and normalizes raw FBI data
- `rewards.py` — extracts numeric dollar values from reward text

The package exposes:

```python
from fbi_wanted_analysis import fetch_current_wanted, clean_wanted
```

## Requirements

Python 3.11+

Dependencies:
- pandas
- numpy
- streamlit
- requests

## Authors

Created by Dallin Robinson and Michael Stutzman

## License

This project is licensed under the MIT License. See the `LICENSE` file for details.
