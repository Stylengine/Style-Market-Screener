import yfinance as ticker_engine
from googlesearch import search as live_web_search
from openai import OpenAI
import requests
import os
import time
import pandas as pd
import numpy as np
from datetime import datetime

OPENAI_KEY = os.environ.get("OPENAI_API_KEY")
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

ai_engine = OpenAI(api_key=OPENAI_KEY)

def push_telegram_notification(message):
    """Transmits priority operational alerts or summaries to the device telegram tunnel."""
    url = f"https://telegram.org{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": message, "parse_mode": "Markdown"}
    try:
        requests.post(url, json=payload, timeout=15)
    except Exception as e:
        print(f"⚠️ Notification error: {e}")

def calculate_technical_boundaries(ticker_symbol):
    """Computes basic technical support and resistance lines using a 20-day window."""
    try:
        stock = ticker_engine.Ticker(ticker_symbol)
        df = stock.history(period="6m")
        if df.empty or len(df) < 20:
            return "N/A", "N/A"
        recent = df.tail(20)
        entry_floor = round(recent['Low'].min(), 1)
        exit_ceiling = round(recent['High'].max(), 1)
        return entry_floor, exit_ceiling
    except Exception:
        return "N/A", "N/A"

def clean_history_for_corporate_actions(csv_path, portfolio_list):
    """
    Scans for stock splits and bonus distributions occurring today,
    and scales past database lines to keep the tracking history clean.
    """
    if not os.path.exists(csv_path):
        return
    
    try:
        df_hist = pd.read_csv(csv_path)
        today_str = datetime.now().strftime("%Y-%m-%d")
        history_altered = False
        
        for asset in portfolio_list:
            ticker = asset["ticker"]
            ns_ticker = ticker + '.NS' if not ticker.endswith('.NS') else ticker
            stock = ticker_engine.Ticker(ns_ticker)
            
            # Pull historical action matrices from the asset engine
            actions = stock.actions
            if actions.empty:
                continue
                
            # Filter for events occurring on the current trading calendar date
            todays_actions = actions[actions.index.strftime('%Y-%m-%d') == today_str]
            
            for index, row in todays_actions.iterrows():
                split_factor = 1.0
                
                # Case A: Stock Split Detected (Recorded as a ratio multiplier value, e.g., 0.1 for 10:1)
                if row["Stock Splits"] > 0:
                    split_factor = float(row["Stock Splits"])
                    print(f"✂️ Corporate Action Alert: Split detected for {ticker} (Factor: {split_factor})")
                
                # Case B: Bonus Issue Distribution Detected (Expressed as raw multiplier addition)
                elif row["Dividends"] == 0 and "Bonus" in actions.columns and row["Bonus"] > 0:
                    # An alternative tracking structure for clean scaling calculation setup
                    split_factor = 1.0 / (1.0 + float(row["Bonus"]))
                    print(f"🎁 Corporate Action Alert: Bonus issue detected for {ticker}")
                
                if split_factor != 1.0:
                    # Update all matching rows in the history file
                    ticker_mask = df_hist["ticker"] == ticker
                    df_hist.loc[ticker_mask, "price"] = np.round(df_hist.loc[ticker_mask, "price"] * split_factor, 1)
                    df_hist.loc[ticker_mask, "floor"] = np.round(df_hist.loc[ticker_mask, "floor"] * split_factor, 1)
                    df_hist.loc[ticker_mask, "ceiling"] = np.round(df_hist.loc[ticker_mask, "ceiling"] * split_factor, 1)
                    history_altered = True
                    
        if history_altered:
            df_hist.to_csv(csv_path, index=False)
            print("💾 Historical database records successfully recalculated and saved.")
            push_telegram_notification(f"🔄 *CORPORATE ACTION REBALANCE EVENT*\nHistorical data for modified assets scaled to prevent dashboard distortions.")
            
    except Exception as err:
        print(f"⚠️ Corporate action adjustment system anomaly: {err}")

if __name__ == "__main__":
    print("🚀 Initiating Cloud Portfolio Multi-Agent Operations with Corporate Action Safeguards...")
    
    my_portfolio = [
        {"ticker": "HDFCBANK", "sector": "Banks"},
        {"ticker": "TATASTEEL", "sector": "Iron, Steel & Metals"},
        {"ticker": "INFY", "sector": "IT Software & Services"},
        {"ticker": "ONGC", "sector": "Oil, Gas & Consumable Fuels"},
        {"ticker": "ASIANPAINT", "sector": "FMCG"}
    ]
    
    csv_file = "docs/history.csv"
    
    # Run the Corporate Action Safeguard to clean the database before evaluating prices
    clean_history_for_corporate_actions(csv_file, my_portfolio)
    
    raw_scores = []
    processed_assets = []
    previous_weights = {}
    historical_peaks = {}
    
    if os.path.exists(csv_file):
        try:
            df_hist = pd.read_csv(csv_file)
            if not df_hist.empty:
                latest_date = df_hist["date"].max()
                df_yesterday = df_hist[df_hist["date"] == latest_date]
                for _, row in df_yesterday.iterrows():
                    previous_weights[row["ticker"]] = float(row["weight"])
                
                for t in df_hist["ticker"].unique():
                    df_ticker = df_hist[df_hist["ticker"] == t]
                    historical_peaks[t] = float(df_ticker["price"].max())
        except Exception as csv_err:
            print(f"⚠️ Historical lookback skip: {csv_err}")

    trailing_sl_alerts = []
    variance_alerts = []

    # Gather Data and Evaluate Brackets
    for asset in my_portfolio:
        ticker = asset["ticker"]
        ns_ticker = ticker + '.NS' if not ticker.endswith('.NS') else ticker
        
        stock = ticker_engine.Ticker(ns_ticker)
        cmp = stock.info.get("currentPrice")
        if not cmp:
            continue
            
        floor, ceiling = calculate_technical_boundaries(ns_ticker)
        
        prev_peak = historical_peaks.get(ticker, cmp)
        current_peak = max(prev_peak, cmp)
        trailing_stop_loss = round(current_peak * 0.97, 1)
        
        if cmp <= trailing_stop_loss:
            trailing_sl_alerts.append(
                f"🛑 *TRAILING STOP-LOSS BREACHED: {ticker}*\n"
                f"⚠️ *Current Market Price:* ₹{cmp}\n"
                f"🛡️ *Locked Trailing Stop Threshold:* ₹{trailing_stop_loss}\n"
                f"🔥 *Action Plan:* **LOCK PROFITS / EXIT POSITION**."
            )
        
        if floor != "N/A" and ceiling != "N/A" and ceiling > floor:
            closeness_score = (ceiling - cmp) / (ceiling - floor)
            closeness_score = max(0.0, min(1.0, closeness_score))
        else:
            closeness_score = 0.5
            
        raw_scores.append(closeness_score)
        processed_assets.append({
            "ticker": ticker, "price": cmp, "floor": floor, "ceiling": ceiling, 
            "peak": current_peak, "tsl": trailing_stop_loss, "score": closeness_score
        })
        time.sleep(1)
        
    # Compute Percentage Allocations
    total_pool_score = sum(raw_scores) if sum(raw_scores) > 0 else 1
    for asset in processed_assets:
        asset["weight"] = round((asset["score"] / total_pool_score) * 100, 1)

    # Detect Weight Shifts
    for asset in processed_assets:
        t = asset["ticker"]
        old_w = previous_weights.get(t, asset["weight"])
        new_w = asset["weight"]
        shift = round(new_w - old_w, 1)
        
        if abs(shift) >= 5.0 and t not in [alert.split() for alert in trailing_sl_alerts]:
            action = f"📥 Deploy allocation +{shift}%." if shift > 0 else f"📤 Trim position by {shift}%."
            variance_alerts.append(f"⚖️ *STAKE SHIFT FOR {t}:* {old_w}% ➡️ {new_w}%\n💡 *Action:* {action}")

    # Push Telegram Notifications
    if trailing_sl_alerts:
        push_telegram_notification("🚨⚠️ *PROFIT PROTECTION ALERT* ⚠️🚨\n\n" + "\n\n=============\n\n".join(trailing_sl_alerts))
    if variance_alerts and not trailing_sl_alerts:
        push_telegram_notification("🔄 *PORTFOLIO REBALANCER UPDATE*\n\n" + "\n\n=============\n\n".join(variance_alerts))

    # Append Clean Logs to the Persistent CSV Database File
    os.makedirs("docs", exist_ok=True)
    today_str = datetime.now().strftime("%Y-%m-%d")
    
    new_rows = []
    for asset in processed_assets:
        new_rows.append({
            "date": today_str, "ticker": asset["ticker"], "price": asset["price"],
            "floor": asset["floor"], "ceiling": asset["ceiling"], "weight": asset["weight"]
        })
    
    df_new = pd.DataFrame(new_rows)
    if os.path.exists(csv_file):
        df_combined = pd.concat([pd.read_csv(csv_file), df_new], ignore_index=True).drop_duplicates(subset=["date", "ticker"], keep="last")
    else:
        df_combined = df_new
    df_combined.to_csv(csv_file, index=False)
    
    # Push Standard Daily Table Summary
    summary_rows = [f"`{a['ticker']:<10} | ₹{str(a['price']):<6} | ₹{str(a['peak']):<6} | ₹{str(a['tsl']):<5} | {str(a['weight'])+'%':<5}`" for a in processed_assets]
    telegram_payload = f"📋 *DAILY PORTFOLIO RISK CONTROL REPORT*\n\n`TICKER     | CMP    | PEAK   | TR-STOP | WEIGHT`\n`--------------------------------------------------`\n" + "\n".join(summary_rows)
    push_telegram_notification(telegram_payload)
    print("🏁 Execution complete.")
