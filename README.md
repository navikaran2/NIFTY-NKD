# 📈 Angel One Intraday Trading System

> **Python-based automated intraday trading bot using Angel One SmartAPI**  
> Strategy: 9:15 AM candle high breakout → 1% profit target → Trailing Stop Loss → Delivery conversion at 3:00 PM

---

## 📋 Table of Contents

1. [System Requirements](#1-system-requirements)
2. [Angel One SmartAPI Setup](#2-angel-one-smartapi-setup)
3. [Project Installation](#3-project-installation)
4. [Configuration (config.py)](#4-configuration-configpy)
5. [Daily Symbol List (symbols.csv)](#5-daily-symbol-list-symbolscsv)
6. [How the Strategy Works](#6-how-the-strategy-works)
7. [Late Login Handling](#7-late-login-handling)
8. [Running the Bot](#8-running-the-bot)
9. [Crash Recovery — Restart Safety](#9-crash-recovery--restart-safety)
10. [Market Closed — What Happens?](#10-market-closed--what-happens)
11. [Live Terminal Dashboard](#11-live-terminal-dashboard)
12. [Telegram Notifications (Optional)](#12-telegram-notifications-optional)
13. [Trade Logs](#13-trade-logs)
14. [Important Warnings](#14-important-warnings)
15. [File Structure](#15-file-structure)
16. [FAQ](#16-faq)

---

## 1. System Requirements

| Requirement | Minimum Version |
|-------------|----------------|
| Windows     | 10 / 11        |
| Python      | 3.10 or above  |
| Internet    | Stable broadband (required during market hours) |
| Angel One Account | Active trading account with SmartAPI enabled |

### Install Python (if not installed)
1. Go to → https://www.python.org/downloads/
2. Download **Python 3.11** (recommended)
3. During installation → ✅ **Check "Add Python to PATH"**
4. Verify: Open Command Prompt → type `python --version`

---

## 2. Angel One SmartAPI Setup

> You must complete this ONE TIME before using the bot.

### Step 1: Create SmartAPI App
1. Login to Angel One → https://smartapi.angelbroking.com/
2. Click **"Create New App"**
3. Fill in App Name (e.g. `MyTradingBot`)
4. Select **"Personal"** type
5. Click **Create** → Copy your **API Key**

### Step 2: Enable TOTP (2FA)
1. Open the Angel One mobile app
2. Go to **My Profile → Security Settings → Enable TOTP**
3. A QR code will be displayed
4. **Important:** Before scanning the QR code, note down the **Secret Key** shown below it  
   *(It looks like: `JBSWY3DPEHPK3PXP` — a 16–32 character string)*
5. This secret key is your **TOTP_TOKEN** value in `config.py`
6. Scan the QR code with Google Authenticator or Authy to finish setup

> ⚠️ If you do not save the secret key now, you will need to reset TOTP to get it again.

---

## 3. Project Installation

### Step 1: Download / Clone the project
Place the `trading_system` folder anywhere on your PC.  
Example: `C:\Angel one\trading_system\`

### Step 2: Install dependencies
**Option A — Double-click** `run_trading.bat` (it installs automatically)

**Option B — Manual install:**
```bash
pip install -r requirements.txt
```

This installs:
- `smartapi-python` — Angel One API library
- `pyotp` — For TOTP generation
- `rich` — Beautiful live terminal dashboard
- `websocket-client` — WebSocket support
- `pycryptodome` — Encryption
- `logzero` — Logging

---

## 4. Configuration (config.py)

> ⚠️ **Fill this file ONCE before first use. Never share this file with anyone.**

Open `config.py` in Notepad or VS Code and fill in:

```python
API_KEY      = "abc123xyz"          # From SmartAPI developer portal
CLIENT_CODE  = "A123456"            # Your Angel One login ID
PASSWORD     = "1234"               # Your 4-digit MPIN (not your full password)
TOTP_TOKEN   = "JBSWY3DPEHPK3PXP"  # Secret key from TOTP setup (Step 2 above)
```

### Strategy Parameters (change if needed)

```python
TARGET_PERCENT        = 1.00    # Sell when 1% profit reached
TRAILING_ACTIVATE_PCT = 0.90    # Start trailing SL at 0.90% profit
TRAILING_TRAIL_PCT    = 0.10    # Trail SL 0.10% below highest price
STOP_LOSS_PERCENT     = 0.50    # Hard stop loss at 0.50% below entry
LATE_ENTRY_MAX_MOVE   = 0.50    # Max % move from open allowed on late login
ENTRY_CUTOFF_TIME     = "09:20" # Stop taking new entries after 9:20 AM
SQUARE_OFF_TIME       = "15:00" # Convert/square-off all trades at 3 PM
MAX_TRADES_PER_DAY    = 10      # Maximum positions at once
TOKEN_REFRESH_HOURS   = 3       # Re-login every 3 hours to keep JWT alive
```

> 💡 **Quantity per trade** is now set per-symbol in `symbols.csv` (QUANTITY column) — not in `config.py`.

---

## 5. Daily Symbol List (symbols.csv)

> 📅 **Edit this file EVERY MORNING before 9:10 AM**

Open `symbols.csv` and add the stocks you want to trade today:

```csv
SYMBOL,TOKEN,QUANTITY
RELIANCE-EQ,2885,1
HDFCBANK-EQ,1333,2
INFY-EQ,1594,5
TCS-EQ,11536,1
```

> ⚠️ **Do not add the same symbol twice** — the bot will detect and skip duplicates with a warning.

### How to find the TOKEN (Symbol Token)?
1. Go to → https://smartapi.angelbroking.com/
2. Download the **Master Script / Instrument List** (JSON/CSV)
3. Search your stock name → copy its `token` value

> 💡 Common tokens:
> | Stock | Token |
> |-------|-------|
> | RELIANCE-EQ | 2885 |
> | HDFCBANK-EQ | 1333 |
> | INFY-EQ | 1594 |
> | TCS-EQ | 11536 |
> | WIPRO-EQ | 3787 |
> | SBIN-EQ | 3045 |
> | ICICIBANK-EQ | 4963 |

---

## 6. How the Strategy Works

```
9:15 AM ──────────────────────────────────────────────────────────────
  The bot fetches the 9:15–9:16 one-minute candle for each symbol.
  It records:  Open, High, Low, Close of that candle.
  The 9:15 candle Open = Today's Market Open price (used for chase check).

9:16 AM → 9:20 AM ────────────────────────────────────────────────────
  Bot watches Live Traded Price (LTP) every second (batch fetch — 1 API call for all symbols).

  Before placing BUY:
    1. Margin check  → confirms funds are available
    2. LTP > 9:15 High → breakout confirmed
    3. BUY order placed
    4. Fill price confirmed via orderBook() (actual average price, not just LTP)

After Entry ──────────────────────────────────────────────────────────
  Bot monitors price every second:

  ┌─ At 0.90% profit → Trailing SL activates
  │    SL moves up with price (locks in profit)
  │
  ├─ At 1.00% profit → SELL immediately (target hit)
  │
  └─ If price falls to SL → SELL immediately (stop loss hit)

  ⚡ All exit orders have 3 automatic retries (5s gap each).
  🚨 If all retries fail → CRITICAL log + Telegram alert (if enabled).

3:00 PM ──────────────────────────────────────────────────────────────
  If trade still open:
    → In Profit?  → Convert to DELIVERY (carry overnight)
    → In Loss?    → Square off (SELL intraday) with 3 retries
```

### Trailing Stop Loss Example

```
Entry Price  = ₹100.00
Hard SL      = ₹99.50   (0.5% below entry)

Price rises to ₹100.90  → Trailing SL activates at ₹100.79
Price rises to ₹101.20  → Trailing SL moves to ₹101.09
Price rises to ₹101.00  → Trailing SL stays at ₹101.09 (only goes UP)
Price falls to ₹101.09  → SELL triggered (still ~1% profit!)
Price rises to ₹101.00+ → SELL at 1% target
```

---

## 7. Late Login Handling

If you start the bot **after 9:16 AM**, the system handles it intelligently:

```
Login Time: 9:17 AM (example)
  → Bot skips the 65-second candle wait
  → Immediately fetches the 9:15 candle via getCandleData API
  → Shows remaining entry window: "⚠ Entry window closes in ~3 min (cutoff: 09:20)"
```

### 3 Cases — What happens when LTP > Signal High on late login:

| Case | Condition | Action |
|------|-----------|--------|
| **Case A** | LTP < Signal High | Wait normally for breakout |
| **Case B** | LTP > High AND moved < 0.5% from open | Fresh breakout — BUY immediately |
| **Case C** | LTP > High AND moved ≥ 0.5% from open | Chase protection — wait for price to pull back and break again |

> 💡 `LATE_ENTRY_MAX_MOVE = 0.50` in `config.py` controls the chase protection threshold.

### Entry window already closed (login after 9:20 AM):
```
⚠ Entry window already closed (09:20).
Bot will only monitor restored positions.
```
The bot still runs and monitors any positions recovered from a crash/restart.

---

## 8. Running the Bot

### ✅ Pre-flight checklist (every morning)

- [ ] `config.py` — credentials filled correctly
- [ ] `symbols.csv` — today's stocks added (no duplicates)
- [ ] Internet connection — stable
- [ ] PC will not sleep/hibernate during market hours
- [ ] Angel One account has sufficient margin

### ▶️ Start the bot

**Double-click:** `run_trading.bat`

OR in Command Prompt:
```bash
cd "C:\Angel one\trading_system"
python main.py
```

### Timeline after starting

```
~9:14 AM  → Bot starts, logs in
             JWT auto-refresh timer set (refreshes every 3 hours)
~9:15 AM  → Waits for 9:15 candle
~9:16 AM  → Candle validated (confirms 09:15 timestamp), signal levels set
~9:16 AM  → Live dashboard appears, starts monitoring
~9:16-9:20 → Takes trades on breakout (with margin check + fill confirmation)
~3:00 PM  → Converts/squares off all positions (with retry)
~3:30 PM  → Prints daily summary, state file cleared, logout
```

### ⏹️ Stop the bot manually
Press `Ctrl + C` in the terminal at any time.  
> ⚠️ If you stop after a trade is entered, **manually square off positions** in the Angel One app  
> OR simply restart the bot — it will automatically **restore your open position** (see Section 9).

---

## 9. Crash Recovery — Restart Safety

> 🛡️ The bot is designed to safely restart after a crash, power cut, or accidental close.

### How it works:

```
Bot crashes while RELIANCE-EQ position is open
    ↓
Bot restarted (any time during the same day)
    ↓
Reads logs/state.json  →  finds today's trade
    ↓
Calls Angel One positions API  →  confirms RELIANCE-EQ is actually open
    ↓
"✓ Restored 1 trade: RELIANCE-EQ"
    ↓
Continues monitoring SL / Target — no duplicate trade placed
```

### State file: `logs/state.json`

| Scenario | Behaviour |
|----------|-----------|
| Bot restarted same day, position still open on Angel One | ✅ Position restored, monitoring resumes |
| Bot restarted same day, position was closed on Angel One (manually or by broker) | ✅ State ignored, fresh start |
| Bot restarted next day | ✅ State file rejected (stale date), fresh start |
| State file corrupted | ✅ Ignored safely, fresh start |

> 💡 The state file is automatically deleted at end of each session (3:30 PM) for a clean start next day.

---

## 10. Market Closed — What Happens?

If you run the bot **outside trading hours**, on a **weekend**, or on an **NSE holiday**, it will:

1. ✅ Login to Angel One normally
2. 🔴 Detect that the market is closed and display the reason
3. 📋 Show your **Order Book** — all orders placed today
4. 📦 Show your **Holdings** — all delivery stocks with live P&L
5. 🚪 Exit cleanly without starting the trading loop

### Example terminal output:

```
╭──────────────────── Market Status ─────────────────────╮
│  ⚠  MARKET IS CLOSED                                   │
│                                                        │
│  Today is Sunday — NSE is closed on weekends.          │
╰────────────────────────────────────────────────────────╯

━━━  ORDER BOOK  ━━━
╭──────────┬────────────────┬─────┬─────┬────────┬──────────┬────────────╮
│ Time     │ Symbol         │ B/S │ Qty │ Type   │ Avg Fill │ Status     │
├──────────┼────────────────┼─────┼─────┼────────┼──────────┼────────────┤
│ 09:17:23 │ RELIANCE-EQ    │ BUY │  1  │ MARKET │ 2906.10  │ COMPLETE   │
╰──────────┴────────────────┴─────┴─────┴────────┴──────────┴────────────╯

━━━  HOLDINGS (Delivery Stocks)  ━━━
╭────────────────┬─────┬──────────┬─────────┬───────────┬─────────┬────────╮
│ Symbol         │ Qty │ Avg Cost │ LTP (₹) │ Curr Value│  P&L ₹  │  P&L % │
├────────────────┼─────┼──────────┼─────────┼───────────┼─────────┼────────┤
│ TCS-EQ         │  1  │ 3451.00  │ 3520.00 │  3520.00  │  +69.00 │ +2.00% │
╰────────────────┴─────┴──────────┴─────────┴───────────┴─────────┴────────╯
  Portfolio Value: ₹3,520.00  |  Invested: ₹3,451.00  |  Overall P&L: +₹69.00 (+2.00%)
```

### Supported closed-market scenarios:
| Situation | Message shown |
|-----------|---------------|
| Saturday | Today is Saturday — NSE is closed on weekends |
| Sunday | Today is Sunday — NSE is closed on weekends |
| NSE Holiday | Today (15 Aug 2025) is an NSE market holiday |
| Before 9:00 AM | Market opens in ~45 minutes (at 9:00 AM) |
| After 3:30 PM | Market is closed for today |

> 💡 NSE holidays for 2025–2026 are pre-loaded in `market_check.py`. Update this list each year.

---

## 11. Live Terminal Dashboard

When the bot is **running during market hours**, you will see a live table like this:

```
╭──────────────────────────────────────────────────────────────────────╮
│             Angel One Live Tracker   09:23:45                        │
├────────────────┬─────────┬──────────┬─────────┬────────┬────────────┤
│ Symbol         │ LTP (₹) │ Sig High │ Entry   │  P&L % │ State      │
├────────────────┼─────────┼──────────┼─────────┼────────┼────────────┤
│ RELIANCE-EQ    │ 2912.50 │ 2905.00  │ 2906.10 │ +0.22% │ ENTERED    │ ← cyan
│ HDFCBANK-EQ    │   ...   │ 1725.30  │   -     │  0.00% │ WATCHING   │ ← white (loading)
│ TCS-EQ         │ 3460.00 │ 3450.00  │ 3451.00 │ +1.00% │ TARGET_HIT │ ← green
╰────────────────┴─────────┴──────────┴─────────┴────────┴────────────╯
```

### Color coding:
| Color | Meaning |
|-------|---------|
| 🟢 Green | Profit / Target hit |
| 🔴 Red | Loss / SL hit |
| 🟡 Yellow | Trailing SL active |
| 🔵 Cyan | Position entered, monitoring |
| ⚪ White | Waiting for breakout signal |

> 💡 LTP shows `...` until the first tick is received from Angel One.

---

## 12. Telegram Notifications (Optional)

The bot can send real-time alerts to your Telegram when trades happen. This is **disabled by default**.

### Events you will receive:
| Event | Message |
|-------|---------|
| ✅ Entry | Trade entered with price, SL, target |
| 🎯 Target Hit | Exit with P&L |
| 🛑 SL Hit | Exit with P&L |
| ⚡ Trailing SL On | Trailing activated with new SL |
| 📦 Converted to Delivery | Position carried overnight |
| 🚨 Square-off Failed | All 3 retries failed — **manual action needed** |

### Setup Steps:

**Step 1: Create a Telegram Bot**
1. Open Telegram → search for **@BotFather**
2. Send `/newbot`
3. Follow the steps → copy the **Bot Token** (looks like: `123456:ABCdefGhIJKlmNoPQRsTUVwxyZ`)

**Step 2: Get your Chat ID**
1. Open Telegram → search for **@userinfobot**
2. Send `/start`
3. Copy the **ID number** shown (looks like: `987654321`)

**Step 3: Enable in config.py**
```python
TELEGRAM_ENABLED   = True
TELEGRAM_BOT_TOKEN = "123456:ABCdefGhIJKlmNoPQRsTUVwxyZ"
TELEGRAM_CHAT_ID   = "987654321"
```

That's it. The bot will now message you for every trade event.

> 💡 Set `TELEGRAM_ENABLED = False` to turn off notifications at any time.

---

## 13. Trade Logs

After the session, all trades are saved in:

### `logs/trades.csv`
```
date,symbol,quantity,entry_time,entry_price,exit_time,exit_price,exit_reason,pnl_pct,pnl_rs,is_delivery
2024-01-15,RELIANCE-EQ,1,09:17:23,2906.10,10:45:12,2935.16,TARGET_1PCT,+1.00%,₹29.06,False
2024-01-15,TCS-EQ,1,09:18:05,3451.00,15:00:01,3500.00,CONVERTED_DELIVERY,+1.42%,₹49.00,True
```

### `logs/trading.log`
Full detailed log with timestamps — useful for debugging.

### `logs/state.json`
Active trade state saved during the session (auto-deleted at 3:30 PM for crash recovery).

---

## 14. Important Warnings

> ### ⚠️ READ BEFORE USING

1. **Software SL only** — The stop loss is managed by your PC. If internet disconnects or PC shuts down mid-trade, the bot cannot protect you. However, on **restart it will recover the open trade** and resume monitoring. Always keep the Angel One app open on your phone as backup.

2. **Brokerage eats profit** — Angel One charges ₹20/order flat + STT + GST. On small quantities, 1% gross profit may become ~0.5% net. Account for this.

3. **Test with 1 share first** — Set `QUANTITY = 1` in `symbols.csv` and test for a few days before increasing size.

4. **Not SEBI registered advice** — This is a personal automation tool. Use at your own risk.

5. **Market holidays auto-detected** — The bot detects weekends and pre-loaded NSE holidays automatically and will not trade. Update `market_check.py` each year with the new NSE holiday list.

6. **JWT auto-refresh** — The bot automatically refreshes its login token every 3 hours in the background (`TOKEN_REFRESH_HOURS` in `config.py`). No action needed.

7. **Square-off retry** — If a SELL order fails at 3 PM, the bot retries 3 times with 5-second gaps. If all retries fail, a CRITICAL log is written and a Telegram alert (if enabled) is sent. **Manually square off in the Angel One app immediately.**

---

## 15. File Structure

```
trading_system/
│
├── 📄 config.py          ← YOUR CREDENTIALS + strategy settings (edit once)
├── 📄 symbols.csv        ← TODAY'S watchlist (edit every morning)
│
├── 🤖 main.py            ← Main bot (runs the full day loop)
├── 🔌 angel_api.py       ← Talks to Angel One SmartAPI (batch LTP, fill confirm, margin check)
├── 📊 trade_manager.py   ← Entry / SL / target / delivery logic + retries
├── 🖥️  dashboard.py      ← Live terminal display (tick-by-tick)
├── 🔒 market_check.py    ← Market status + order book + holdings display
├── 💾 state_manager.py   ← Crash recovery — saves/restores open trade state
├── 📣 notifier.py        ← Optional Telegram notifications
├── 📝 logger_setup.py    ← Log file configuration
│
├── ▶️  run_trading.bat   ← Double-click to start (Windows)
├── 📦 requirements.txt   ← Python packages list
│
└── logs/
    ├── 📋 trading.log    ← Full event log
    ├── 📊 trades.csv     ← Daily trade P&L record
    └── 💾 state.json     ← Active trade state (auto-managed, do not edit)
```

---

## 16. FAQ

**Q: I got a Telegram alert that square-off failed — what do I do?**  
A: Open the Angel One mobile app immediately → go to **Positions** → manually sell the open intraday position. Do not wait.

**Q: The bot restarted but didn't restore my trade?**  
A: This means the position was already closed on Angel One (by a manual square-off, broker auto-square-off, or SL/target hit). The bot correctly detected this and started fresh — no action needed.

**Q: A trade was taken but I wasn't notified?**  
A: Enable Telegram notifications (Section 12). All trades are also permanently recorded in `logs/trades.csv`.

**Q: Getting a `Login failed` error?**  
A: Verify the following in `config.py`:
- `CLIENT_CODE` — your Angel One login ID (e.g. A123456)
- `PASSWORD` — your 4-digit MPIN (not your full account password)
- `TOTP_TOKEN` — the secret key from TOTP setup (not the 6-digit OTP)
- `API_KEY` — copied from the SmartAPI developer portal

**Q: Candle data was not fetched?**  
A: This happens if the bot runs before 9:16 AM. The 9:15 candle is only available after it closes at 9:16. The bot already waits 65 seconds automatically. For late logins, it fetches the candle immediately and validates the 09:15 timestamp.

**Q: How do I set different quantities per symbol?**  
A: Edit the `QUANTITY` column in `symbols.csv`:
```csv
RELIANCE-EQ,2885,5
HDFCBANK-EQ,1333,2
```

**Q: Is paper trading (simulation without real money) possible?**  
A: Angel One provides a sandbox environment via SmartAPI. Replace the `API_KEY` in `config.py` with your sandbox key to test without real orders.

**Q: I want to exit a trade before 3:00 PM manually?**  
A: Square off the position directly from the Angel One app. The bot will detect the position is closed and skip the 3 PM processing for that symbol.

**Q: I ran the bot after market hours — what will I see?**  
A: The bot logs in, shows a "Market is Closed" message with the reason, then displays your full **Order Book** and **Holdings** with live P&L. It then exits without placing any trades.

**Q: The NSE holiday list is wrong / outdated?**  
A: Open `market_check.py` and update the `NSE_HOLIDAYS_2026` list at the top of the file. Angel One publishes the official holiday list on their website each year.

**Q: Can I change how often the JWT token refreshes?**  
A: Yes. In `config.py`, change `TOKEN_REFRESH_HOURS = 3` to any value (e.g. `2` for every 2 hours). Do not set it higher than 6 hours.

---

## 📞 Support

- Angel One SmartAPI Docs: https://smartapi.angelbroking.com/docs
- Angel One Support: 1800-102-1111
- Python SmartAPI GitHub: https://github.com/angel-one/smartapi-python

---

*Last Updated: April 2026 — v1.2 (crash recovery, batch LTP, margin check, fill confirmation, Telegram alerts, JWT auto-refresh, retry logic)*
