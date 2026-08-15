import yfinance as ticker_engine
from googlesearch import search as live_web_search
from openai import OpenAI
import requests
import os
import time
import pandas as pd
import numpy as np
from datetime import datetime

OPENAI_KEY = os.environ.get("OPENAI_API_KEY") or os.environ.get("OPENAI_KEY")
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

ai_engine = OpenAI(api_key=OPENAI_KEY)

def gather_macro_index_telemetry():
    """Extracts structural volatility benchmarks to define the macro risk environment."""
    try:
        nifty = ticker_engine.Ticker("^NSEI")
        vix = ticker_engine.Ticker("^INDIAVIX")
        nifty_df = nifty.history(period="2mo")
        vix_df = vix.history(period="1d")
        
        if nifty_df.empty or vix_df.empty:
            return 0.0, 15.0, "⚖️ NOMINAL"
            
        nifty_cmp = nifty_df['Close'].iloc[-1]
        vix_level = vix_df['Close'].iloc[-1]
        nifty_df['MA20'] = nifty_df['Close'].rolling(window=20).mean()
        ma_twenty = nifty_df['MA20'].iloc[-1]
        
        trend = "🟢 BULLISH" if nifty_cmp >= ma_twenty else "🔴 BEARISH"
        vix_state = "⚠️ HIGH RISK" if vix_level > 22.0 else "🟢 STABLE"
        return round(nifty_cmp, 1), round(vix_level, 1), f"Trend: {trend} | VIX: {vix_state} ({round(vix_level,1)})"
    except Exception:
        return 0.0, 15.0, "⚖️ OPERATIONAL DATA PIPELINE"

def calculate_technical_boundaries(ticker_symbol):
    """Computes technical support, resistance lines, and stop-loss levels."""
    try:
        stock = ticker_engine.Ticker(ticker_symbol)
        df = stock.history(period="6mo")
        if df.empty or len(df) < 20:
            return "N/A", "N/A", "N/A"
        recent = df.tail(20)
        entry_floor = round(recent['Low'].min(), 1)
        exit_ceiling = round(recent['High'].max(), 1)
        stop_loss_level = round(entry_floor * 0.97, 1)
        return entry_floor, exit_ceiling, stop_loss_level
    except Exception:
        return "N/A", "N/A", "N/A"

def push_telegram_notification(message):
    """Transmits priority operational alerts or summaries to the device telegram tunnel."""
    url = f"https://telegram.org{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": message, "parse_mode": "Markdown"}
    try:
        requests.post(url, json=payload, timeout=15)
    except Exception as e:
        print(f"⚠️ Notification error: {e}")

if __name__ == "__main__":
    print("🚀 Initiating Cloud Portfolio Multi-Agent Operations with Corporate Action Safeguards...")
    nifty_spot, india_vix, macro_environment = gather_macro_index_telemetry()
    
    my_portfolio = [
        {"ticker": "HDFCBANK", "sector": "Banks"},
        {"ticker": "TATASTEEL", "sector": "Iron, Steel & Metals"},
        {"ticker": "INFY", "sector": "IT Software & Services"},
        {"ticker": "ONGC", "sector": "Oil, Gas & Consumable Fuels"},
        {"ticker": "ASIANPAINT", "sector": "FMCG"}
    ]
    
    raw_scores = []
    processed_assets = []
    csv_file = "docs/history.csv"
    
    previous_weights = {}
    if os.path.exists(csv_file):
        try:
            df_hist = pd.read_csv(csv_file)
            if not df_hist.empty:
                latest_recorded_date = df_hist["date"].max()
                df_yesterday = df_hist[df_hist["date"] == latest_recorded_date]
                for _, row in df_yesterday.iterrows():
                    previous_weights[row["ticker"]] = float(row["weight"])
        except Exception:
            pass

    stop_loss_alerts = []
    variance_alerts = []

    for asset in my_portfolio:
        ticker = asset["ticker"]
        ns_ticker = ticker + '.NS' if not ticker.endswith('.NS') else ticker
        
        stock = ticker_engine.Ticker(ns_ticker)
        cmp = stock.info.get("currentPrice")
        if not cmp:
            continue
            
        floor, ceiling, stop_loss = calculate_technical_boundaries(ns_ticker)
        
        if stop_loss != "N/A" and cmp <= stop_loss:
            stop_loss_alerts.append(
                f"🚨 *CRITICAL BREAKDOWN ALERT: {ticker}*\n"
                f"⚠️ *Current Price:* ₹{cmp} | *Stop Floor Threshold:* ₹{stop_loss}\n"
                f"🔥 *Action:* Prioritise capital preservation."
            )
        
        if floor != "N/A" and ceiling != "N/A" and ceiling > floor:
            closeness_score = (ceiling - cmp) / (ceiling - floor)
            closeness_score = max(0.0, min(1.0, closeness_score))
        else:
            closeness_score = 0.5
            
        raw_scores.append(closeness_score)
        processed_assets.append({
            "ticker": ticker, "price": cmp, "floor": floor, "ceiling": ceiling, "stop_loss": stop_loss, "score": closeness_score
        })
        time.sleep(1)
        
    total_pool_score = sum(raw_scores) if sum(raw_scores) > 0 else 1
    cash_cushion = 20.0 if india_vix > 22.0 else 0.0
    equity_multiplier = (100.0 - cash_cushion) / 100.0
    
    for asset in processed_assets:
        base_weight = (asset["score"] / total_pool_score) * 100
        asset["weight"] = round(base_weight * equity_multiplier, 1)

    for asset in processed_assets:
        t = asset["ticker"]
        old_w = previous_weights.get(t, asset["weight"])
        new_w = asset["weight"]
        shift = round(new_w - old_w, 1)
        
        if abs(shift) >= 5.0:
            if shift > 0:
                action = f"📥 Price near Support (₹{asset['floor']}). Allocation +{shift}%."
            else:
                action = f"📤 Rally near Resistance (₹{asset['ceiling']}). Trim position by {shift}%."
            variance_alerts.append(f"⚖️ *STAKE SHIFT FOR {t}:* {old_w}% ➡️ {new_w}%\n💡 *Action:* {action}")

    # Force a structured text summary message on every run
    summary_rows = [f"`{a['ticker']:<10} | ₹{str(a['price']):<6} | ₹{str(a['floor']):<5} | ₹{str(a['stop_loss']):<5} | {str(a['weight'])+'%':<5}`" for a in processed_assets]
    telegram_payload = f"📋 *DAILY RISK CONTROL HEALTH REPORT*\n" \
                       f"🌐 *Nifty 50:* {nifty_spot} | *Macro:* {macro_environment}\n\n" \
                       f"`TICKER     | CMP    | FLOOR | STOP  | WEIGHT`\n`------------------------------------------------`\n" + "\n".join(summary_rows)
    
    if stop_loss_alerts:
        emergency_payload = "🚨🔴 *PORTFOLIO CRISIS ALERT* 🔴🚨\n\n" + "\n\n=============\n\n".join(stop_loss_alerts)
        push_telegram_notification(emergency_payload)
    else:
        push_telegram_notification(telegram_payload)

    os.makedirs("docs", exist_ok=True)
    today_str = datetime.now().strftime("%Y-%m-%d")
    new_rows = [{"date": today_str, "ticker": a["ticker"], "price": a["price"], "floor": a["floor"], "ceiling": a["ceiling"], "weight": a["weight"]} for a in processed_assets]
    
    df_new = pd.DataFrame(new_rows)
    if os.path.exists(csv_file):
        df_combined = pd.concat([pd.read_csv(csv_file), df_new], ignore_index=True).drop_duplicates(subset=["date", "ticker"], keep="last")
    else:
        df_combined = df_new
    df_combined.to_csv(csv_file, index=False)
    print("🏁 Execution complete.")
