# TradingView Data Pipeline

## Overview
Python project that extracts market data from TradingView, transforms it, and outputs structured datasets for analysis or integration.

## Features
- Connects to TradingView API
- Fetches historical and live data
- Data cleaning and transformation
- Outputs CSV or JSON for downstream use

## Tools & Libraries
- Python 3.x
- requests
- pandas
- datetime

## Usage
1. Install requirements: `pip install -r requirements.txt`
2. Configure API parameters in `fetch_data.py`
3. Run `python fetch_data.py` to pull and save data

## Outcome
Demonstrates ability to work with APIs, transform data, and build automation-ready workflows for technical and analytics purposes.

## Sample Output
The script generates structured CSV files stored in the `/sample_data` folder. Example:

| timestamp           | symbol | price |
|--------------------|--------|-------|
| 2025-12-16 09:00:00 | AAPL  | 178.5 |
| 2025-12-16 09:01:00 | GOOG  | 135.2 |
| 2025-12-16 09:02:00 | TSLA  | 420.1 |

