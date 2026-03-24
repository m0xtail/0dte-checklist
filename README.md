# 0DTE ORB Checklist

Mobile-first daily checklist for the 0DTE Opening Range Breakout strategy.

## What it does
- Pulls live SPY, QQQ, VIX prices automatically (refreshes every 60s)
- Pulls GEX/HVL/Call Wall/Put Wall via FlashAlpha API and classifies regime
- Calculates expected move and OR width check
- IV skew check with directional lean
- No-trade condition checker (auto-flags VIX > 35, Tue/Thu)
- Decision builder (trade/index/size/direction)
- P&L calculator
- Saves every session to Supabase trade log

## Deploy to Render
1. Push this repo to GitHub
2. New Web Service on Render → connect repo
3. Build command: `pip install -r requirements.txt`
4. Start command: `gunicorn app:app`
5. Free tier is fine

## Keep alive with UptimeRobot
Add a monitor pointing to `https://your-app.onrender.com/health`
(same setup as your bolus tracker / dexcom-proxy)

## Local dev
```
pip install -r requirements.txt
python app.py
```
Then open http://localhost:5000

