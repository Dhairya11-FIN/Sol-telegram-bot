import ccxt
import pandas as pd
import ta
import requests
import time
import os

# ==========================
# TELEGRAM CONFIG
# ==========================

TOKEN = os.environ.get("TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")

def send_telegram(message):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": message
    }
    requests.post(url, data=payload)
# ✅ Now you can call it
send_telegram("✅ Bot Connected Successfully")
# ==========================
# MANUAL SUPPORT LEVELS
# ==========================

support_levels = [
    248.81,231.48,223.58,211.48,203.39,195.31,
    183.90,176.45,170.37,152.89,146.34,139.53,
    131.45,123.04,117.77,113.05,106.57,100.55,
    96.98,88.46,83.13,76.87,67.87,54.64
]

support_levels = sorted(support_levels, reverse=True)
tolerance = 0.02

def near_support(price):
    for level in support_levels:
        if abs(price - level) / level < tolerance:
            return level
    return None

# ==========================
# EXCHANGE
# ==========================

exchange = ccxt.binance()

print("🚀 Live Strategy Started...")

last_signal_time = None  # prevent duplicate alerts

while True:

    try:
        bars = exchange.fetch_ohlcv('SOL/USDT', timeframe='1h', limit=300)

        df = pd.DataFrame(
            bars,
            columns=['timestamp','open','high','low','close','volume']
        )

        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        df.set_index('timestamp', inplace=True)

        # Indicators
        stoch = ta.momentum.StochRSIIndicator(
            close=df['close'],
            window=14,
            smooth1=3,
            smooth2=3
        )

        df['stoch_k'] = stoch.stochrsi_k() * 100
        df['stoch_d'] = stoch.stochrsi_d() * 100
        df['prev_k'] = df['stoch_k'].shift(1)
        df['prev_d'] = df['stoch_d'].shift(1)

        df['adx'] = ta.trend.adx(
            df['high'],
            df['low'],
            df['close'],
            window=14
        )

        # Use last CLOSED candle
        latest = df.iloc[-2]

        price = latest['close']
        stoch_k = latest['stoch_k']
        stoch_d = latest['stoch_d']
        prev_k = latest['prev_k']
        prev_d = latest['prev_d']
        adx = latest['adx']
        candle_time = latest.name

        support_hit = near_support(price)

        # LONG CONDITION (same as backtest)
        long_condition = (
            support_hit is not None and
            stoch_k < 20 and
            prev_k < prev_d and
            stoch_k > stoch_d and
            adx < 20
        )

        # SHORT CONDITION (same as backtest)
        short_condition = (
            support_hit is not None and
            stoch_k > 80 and
            prev_k > prev_d and
            stoch_k < stoch_d and
            adx < 20
        )

        # Prevent duplicate alerts
        if candle_time != last_signal_time:

            if long_condition:
                message = (
                    f"🟢 LONG SIGNAL\n"
                    f"Price: {price}\n"
                    f"Support: {support_hit}\n"
                    f"Time: {candle_time}"
                )
                send_telegram(message)
                print("LONG SENT")
                last_signal_time = candle_time

            elif short_condition:
                message = (
                    f"🔴 SHORT SIGNAL\n"
                    f"Price: {price}\n"
                    f"Support: {support_hit}\n"
                    f"Time: {candle_time}"
                )
                send_telegram(message)
                print("SHORT SENT")
                last_signal_time = candle_time

            else:
                print("No Signal")

    except Exception as e:
        print("Error:", e)

    time.sleep(60)   # check every minute
