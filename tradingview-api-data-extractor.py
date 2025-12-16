import time
import csv
import os
from datetime import datetime, timedelta
import pytz
from collections import deque
from tradingview_ta import TA_Handler, Interval

# === CONFIGURATION ===
TICKERS = ["TSLA", "MSFT", "NVDA", "PLTR"]
SHORT_MA = 5
LONG_MA = 15
LOG_FILE = "tradingview_signals.csv"

# Monitoring intervals
HIGH_FREQ_INTERVAL = 60    # 1 minute
HIGH_FREQ_DURATION = 30    # minutes from market open
LOW_FREQ_INTERVAL_MINUTES = 10

# === HELPER FUNCTIONS ===
def get_tradingview_price(ticker, interval=Interval.INTERVAL_1_MINUTE, retries=3, delay=5):
    """Fetch last close price from TradingView with retry-on-429"""
    attempt = 0
    while attempt < retries:
        try:
            handler = TA_Handler(symbol=ticker, screener="america", exchange="NASDAQ", interval=interval)
            analysis = handler.get_analysis()
            return analysis.indicators["close"]
        except Exception as e:
            err_msg = str(e)
            if "429" in err_msg:
                attempt += 1
                print(f"{ticker}: Rate limit hit (429). Retrying in {delay}s... ({attempt}/{retries})")
                time.sleep(delay)
            else:
                print(f"Error fetching price for {ticker}: {e}")
                return None
    print(f"{ticker}: Failed after {retries} retries due to rate limits.")
    return None

def get_swing_signal(price_history, current_price):
    """Simple MA crossover strategy"""
    price_history.append(current_price)
    if len(price_history) < LONG_MA:
        return "HOLD", 0, 0
    short_ma = sum(list(price_history)[-SHORT_MA:]) / SHORT_MA
    long_ma = sum(price_history) / LONG_MA
    if short_ma > long_ma:
        signal = "BUY"
    elif short_ma < long_ma:
        signal = "SELL"
    else:
        signal = "HOLD"
    return signal, short_ma, long_ma

def log_signal(timestamp, ticker, price, short_ma, long_ma, signal):
    with open(LOG_FILE, "a", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([timestamp, ticker, f"{price:.2f}", f"{short_ma:.2f}", f"{long_ma:.2f}", signal])

def get_next_10min_run(now):
    next_minute = ((now.minute // 10) + 1) * 10
    next_hour = now.hour
    if next_minute >= 60:
        next_minute -= 60
        next_hour += 1
    next_run = now.replace(hour=next_hour % 24, minute=next_minute, second=0, microsecond=0)
    if next_run <= now:
        next_run += timedelta(minutes=10)
    return next_run

def preload_price_history(ticker, history_deque, interval):
    """Preload deque with last LONG_MA prices safely, skipping on 429"""
    try:
        handler = TA_Handler(symbol=ticker, screener="america", exchange="NASDAQ", interval=interval)
        analysis = handler.get_analysis()
        last_price = analysis.indicators["close"]
        for _ in range(LONG_MA):
            history_deque.append(last_price)
        print(f"{ticker}: Preloaded MA history with {last_price}")
    except Exception as e:
        err_msg = str(e)
        if "429" in err_msg:
            print(f"{ticker}: Skipped preload due to rate limit (429). MA will build over time.")
        else:
            print(f"{ticker}: Error preloading history: {e}")

# === MAIN SCRIPT ===
def main():
    eastern = pytz.timezone("US/Eastern")
    price_history_1min = {ticker: deque(maxlen=LONG_MA) for ticker in TICKERS}
    price_history_15min = {ticker: deque(maxlen=LONG_MA) for ticker in TICKERS}
    last_signal = {ticker: None for ticker in TICKERS}

    # Preload MA history with stagger and 429-safe
    for ticker in TICKERS:
        preload_price_history(ticker, price_history_1min[ticker], Interval.INTERVAL_1_MINUTE)
        time.sleep(1.5)
        preload_price_history(ticker, price_history_15min[ticker], Interval.INTERVAL_15_MINUTES)
        time.sleep(1.5)

    now = datetime.now(eastern)
    market_open = now.replace(hour=9, minute=30, second=0, microsecond=0)
    market_close = now.replace(hour=16, minute=0, second=0, microsecond=0)
    high_freq_end = market_open + timedelta(minutes=HIGH_FREQ_DURATION)

    print("Monitoring TradingView signals from 9:30 AM to 4:00 PM EST...\n")

    while True:
        now = datetime.now(eastern)
        if market_open <= now <= market_close:
            if now < high_freq_end:
                sleep_interval = HIGH_FREQ_INTERVAL
                tv_interval = Interval.INTERVAL_1_MINUTE
                history = price_history_1min
            else:
                tv_interval = Interval.INTERVAL_15_MINUTES
                history = price_history_15min
                next_run = get_next_10min_run(now)
                sleep_interval = max(5, (next_run - datetime.now(eastern)).total_seconds())

            # Fetch prices and calculate signals
            for ticker in TICKERS:
                current_price = get_tradingview_price(ticker, interval=tv_interval)
                if current_price is None:
                    continue
                signal, short_ma, long_ma = get_swing_signal(history[ticker], current_price)

                if signal != last_signal[ticker]:
                    timestamp = datetime.now(eastern).strftime('%Y-%m-%d %H:%M:%S')
                    print(f"{timestamp} | {ticker} | {current_price:.2f} | Short MA: {short_ma:.2f} | Long MA: {long_ma:.2f} | {signal}")
                    log_signal(timestamp, ticker, current_price, short_ma, long_ma, signal)
                    last_signal[ticker] = signal

                time.sleep(1)  # stagger to reduce 429

            time.sleep(sleep_interval)

        elif now > market_close:
            print("Market closed. Monitoring ended.")
            break
        else:
            sleep_seconds = max(30, (market_open - now).seconds)
            print(f"Waiting for market open ({sleep_seconds} seconds)...")
            time.sleep(sleep_seconds)

# === INIT CSV FILE ===
if __name__ == "__main__":
    if not os.path.exists(LOG_FILE):
        with open(LOG_FILE, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["Timestamp", "Ticker", "Price", "Short_MA", "Long_MA", "Signal"])
    main()
