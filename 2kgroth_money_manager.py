"""
Tiered Milestone Money Management & Discipline Tracker
Fixed: Custom starting capital keeps absolute tier stakes (e.g. $500 account → $100 stake).
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, date
from typing import Dict, List, Optional, Tuple
import copy

# =============================================================================
# PAGE CONFIG & THEME
# =============================================================================
st.set_page_config(
    page_title="Tiered Milestone Tracker",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
    .stApp { background-color: #0E1117; color: #FAFAFA; }
    h1, h2, h3, h4, h5, h6, p, label, span, div { color: #FAFAFA !important; }

    .hero-card {
        background: linear-gradient(135deg, #1a1f2e 0%, #0f1419 100%);
        border: 1px solid #2a3441;
        border-radius: 12px;
        padding: 1.5rem 2rem;
        margin-bottom: 1.5rem;
        box-shadow: 0 4px 20px rgba(0,0,0,0.4);
    }
    .hero-balance {
        font-size: 2.8rem; font-weight: 700;
        color: #00D4AA !important; margin: 0; letter-spacing: -1px;
    }
    .hero-tier { font-size: 1.05rem; color: #8B9CB3 !important; margin-top: 0.25rem; }
    .hero-stake { font-size: 1.6rem; font-weight: 600; color: #FFFFFF !important; }
    .hero-profit { font-size: 1.2rem; color: #00D4AA !important; }

    .banner-lock {
        background: linear-gradient(90deg, #3d2a00 0%, #2a1f00 100%);
        border-left: 5px solid #FFB800; padding: 1rem 1.25rem;
        border-radius: 8px; margin: 1rem 0; font-weight: 600; color: #FFD700 !important;
    }
    .banner-win {
        background: linear-gradient(90deg, #003d2a 0%, #002a1f 100%);
        border-left: 5px solid #00D4AA; padding: 1rem 1.25rem;
        border-radius: 8px; margin: 1rem 0; font-weight: 600; color: #00D4AA !important;
    }
    .banner-loss {
        background: linear-gradient(90deg, #3d0000 0%, #2a0000 100%);
        border-left: 5px solid #FF4B4B; padding: 1rem 1.25rem;
        border-radius: 8px; margin: 1rem 0; font-weight: 600; color: #FF6B6B !important;
    }
    .banner-warning {
        background: linear-gradient(90deg, #3d2a00 0%, #2a1f00 100%);
        border-left: 5px solid #FFB800; padding: 0.85rem 1.25rem;
        border-radius: 8px; margin: 1rem 0; color: #FFD700 !important; font-size: 0.95rem;
    }
    .banner-stepdown {
        background: linear-gradient(90deg, #3d0000 0%, #2a0000 100%);
        border-left: 5px solid #FF4B4B; padding: 1rem 1.25rem;
        border-radius: 8px; margin: 1rem 0; font-weight: 600; color: #FF6B6B !important;
    }
    .banner-levelup {
        background: linear-gradient(90deg, #003d2a 0%, #002a1f 100%);
        border-left: 5px solid #00D4AA; padding: 1rem 1.25rem;
        border-radius: 8px; margin: 1rem 0; font-weight: 600; color: #00D4AA !important;
    }
    .banner-house {
        background: linear-gradient(90deg, #2a1f00 0%, #1f1700 100%);
        border-left: 5px solid #FFB800; padding: 1rem 1.25rem;
        border-radius: 8px; margin: 1rem 0; font-weight: 600; color: #FFD700 !important;
    }

    div[data-testid="stMetric"] {
        background-color: #1a1f2e; border: 1px solid #2a3441;
        border-radius: 10px; padding: 1rem;
    }
    div[data-testid="stMetric"] label { color: #8B9CB3 !important; }

    .stButton > button { border-radius: 8px; font-weight: 600; }
    section[data-testid="stSidebar"] { background-color: #0b0e14; border-right: 1px solid #1e2530; }
    hr { border-color: #2a3441 !important; }
</style>
""", unsafe_allow_html=True)

# =============================================================================
# TIER DEFINITIONS – absolute values from your screenshots
# These NEVER scale. Custom capital only changes the starting balance.
# =============================================================================
TIERS = [
    {
        "key": "emergency",
        "name": "Emergency",
        "min_balance": 0.0,
        "max_balance": 4.99,
        "stake": 1.0,
        "allows_house_money": False,
        "description": "Below $5 → $1 stake until recover to $10",
    },
    {
        "key": "startup",
        "name": "Start-up ($10)",
        "min_balance": 5.0,
        "max_balance": 29.99,
        "stake": 5.0,
        "allows_house_money": False,
        "description": "$10 capital · $5 / trade · 1 trade/day only",
    },
    {
        "key": "m30",
        "name": "Milestone $30",
        "min_balance": 30.0,
        "max_balance": 59.99,
        "stake": 10.0,
        "allows_house_money": False,
        "description": "$10 / trade · 1 trade/day only",
    },
    {
        "key": "m60",
        "name": "Milestone $60",
        "min_balance": 60.0,
        "max_balance": 99.99,
        "stake": 20.0,
        "allows_house_money": False,
        "description": "$20 / trade · 1 trade/day only",
    },
    {
        "key": "m100",
        "name": "Milestone $100",
        "min_balance": 100.0,
        "max_balance": 199.99,
        "stake": 25.0,
        "allows_house_money": True,
        "description": "$25 / trade · optional house-money chain",
    },
    {
        "key": "m200",
        "name": "Milestone $200",
        "min_balance": 200.0,
        "max_balance": 499.99,
        "stake": 30.0,
        "allows_house_money": True,
        "description": "$30 / trade · optional house-money chain",
    },
    {
        "key": "m500",
        "name": "Milestone $500",
        "min_balance": 500.0,
        "max_balance": float("inf"),
        "stake": 100.0,
        "allows_house_money": True,
        "description": "$100 / trade · optional house-money chain",
    },
]

MILESTONE_THRESHOLDS = [30.0, 60.0, 100.0, 200.0, 500.0]


def get_current_tier(balance: float) -> Dict:
    for t in TIERS:
        if t["min_balance"] <= balance <= t["max_balance"]:
            return t
    return TIERS[-1]


def potential_profit(stake: float, payout_rate: float) -> float:
    return round(stake * (payout_rate / 100.0), 2)


def init_session_state():
    defaults = {
        "balance": 10.0,
        "mode": "Standard Fixed Tier Mode",
        "custom_capital": 10.0,
        "payout_rate": 85.0,
        "trade_history": [],
        "daily_trades": 0,
        "last_trade_date": None,
        "day_locked": False,
        "house_money_active": False,
        "next_house_stake": 0.0,
        "notifications": [],
        "starting_balance_of_day": 10.0,
        "equity_curve": [{"date": date.today().isoformat(), "balance": 10.0}],
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v


def reset_account():
    start_bal = float(st.session_state.custom_capital) if st.session_state.mode == "Custom Starting Capital Mode" else 10.0
    st.session_state.balance = start_bal
    st.session_state.trade_history = []
    st.session_state.daily_trades = 0
    st.session_state.last_trade_date = None
    st.session_state.day_locked = False
    st.session_state.house_money_active = False
    st.session_state.next_house_stake = 0.0
    st.session_state.notifications = []
    st.session_state.starting_balance_of_day = start_bal
    st.session_state.equity_curve = [{"date": date.today().isoformat(), "balance": start_bal}]
    st.success("Account & settings reset successfully.")


def check_new_day():
    today = date.today().isoformat()
    if st.session_state.last_trade_date != today:
        st.session_state.daily_trades = 0
        st.session_state.day_locked = False
        st.session_state.house_money_active = False
        st.session_state.next_house_stake = 0.0
        st.session_state.starting_balance_of_day = st.session_state.balance


def get_recommended_stake(balance: float) -> Tuple[float, Dict, bool]:
    tier = get_current_tier(balance)
    if st.session_state.house_money_active and st.session_state.next_house_stake > 0:
        return round(st.session_state.next_house_stake, 2), tier, True
    return tier["stake"], tier, False


def record_trade(result: str, pl_amount: Optional[float] = None):
    check_new_day()
    today = date.today().isoformat()
    payout = st.session_state.payout_rate

    if st.session_state.day_locked:
        st.session_state.notifications.append({
            "type": "lock",
            "msg": "Trading is locked for today. Return tomorrow.",
        })
        return

    balance_before = st.session_state.balance
    tier_before = get_current_tier(balance_before)
    stake, active_tier, is_house = get_recommended_stake(balance_before)

    if result == "WIN":
        profit = pl_amount if (pl_amount is not None and pl_amount > 0) else potential_profit(stake, payout)
        balance_after = round(balance_before + profit, 2)
    else:
        loss = abs(pl_amount) if (pl_amount is not None and pl_amount < 0) else stake
        balance_after = round(max(0.0, balance_before - loss), 2)
        profit = -loss

    st.session_state.balance = balance_after
    st.session_state.daily_trades += 1
    st.session_state.last_trade_date = today

    st.session_state.trade_history.append({
        "date": today,
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "tier": active_tier["name"],
        "starting_balance": balance_before,
        "stake_used": stake,
        "result": result,
        "pl": profit,
        "house_money": is_house,
        "ending_balance": balance_after,
    })
    st.session_state.equity_curve.append({"date": today, "balance": balance_after})

    tier_after = get_current_tier(balance_after)

    if result == "WIN":
        if active_tier["allows_house_money"]:
            next_stake = round(profit * 0.5, 2)
            st.session_state.house_money_active = True
            st.session_state.next_house_stake = next_stake
            st.session_state.day_locked = False
            st.session_state.notifications.append({
                "type": "house",
                "msg": (
                    f"WIN (+${profit:.2f}). "
                    f"Optional next trade available using 50% of this profit → stake ${next_stake:.2f}. "
                    f"Take it or press End Trading Day to stop."
                ),
            })
        else:
            st.session_state.day_locked = True
            st.session_state.house_money_active = False
            st.session_state.next_house_stake = 0.0
            st.session_state.notifications.append({
                "type": "win",
                "msg": f"WIN (+${profit:.2f}). Rule: 1 Win per day → EXIT THE MARKET. Return tomorrow.",
            })
    else:
        st.session_state.day_locked = True
        st.session_state.house_money_active = False
        st.session_state.next_house_stake = 0.0
        st.session_state.notifications.append({
            "type": "loss",
            "msg": f"LOSS (${abs(profit):.2f}). Rule: 1 Loss per day → EXIT THE MARKET. No revenge trading.",
        })

    if tier_after["name"] != tier_before["name"]:
        if balance_after < balance_before:
            st.session_state.notifications.append({
                "type": "stepdown",
                "msg": (
                    f"STEP-DOWN: Now on {tier_after['name']} (stake ${tier_after['stake']:.2f}). "
                    f"Repeat strategy until you reach the higher milestone again."
                ),
            })
        else:
            st.session_state.notifications.append({
                "type": "levelup",
                "msg": f"LEVEL-UP: Reached {tier_after['name']}! New stake = ${tier_after['stake']:.2f}.",
            })

    if balance_after < 5.0:
        st.session_state.notifications.append({
            "type": "stepdown",
            "msg": "Emergency: Balance below $5. Stake fixed at $1 until you recover to $10.",
        })


def end_trading_day():
    st.session_state.day_locked = True
    st.session_state.house_money_active = False
    st.session_state.next_house_stake = 0.0
    st.session_state.notifications.append({
        "type": "lock",
        "msg": "Trading day ended. Terminal locked until tomorrow.",
    })


def compute_analytics(history: List[Dict], current_balance: float, start_balance: float) -> Dict:
    if not history:
        return {
            "total_days": 0, "net_roi": 0.0, "win_rate": 0.0,
            "current_streak": 0, "max_drawdown": 0.0,
            "total_trades": 0, "wins": 0, "losses": 0,
        }
    df = pd.DataFrame(history)
    total_trades = len(df)
    wins = len(df[df["result"] == "WIN"])
    losses = total_trades - wins
    win_rate = (wins / total_trades * 100) if total_trades else 0.0
    total_days = df["date"].nunique()
    net_roi = ((current_balance - start_balance) / start_balance * 100) if start_balance > 0 else 0.0

    streak, streak_type = 0, None
    for r in reversed(df["result"].tolist()):
        if streak_type is None:
            streak_type, streak = r, 1
        elif r == streak_type:
            streak += 1
        else:
            break
    current_streak = streak if streak_type == "WIN" else -streak

    equity = [e["balance"] for e in st.session_state.equity_curve]
    max_dd = 0.0
    if len(equity) >= 2:
        peak = equity[0]
        for b in equity:
            if b > peak:
                peak = b
            dd = (peak - b) / peak * 100 if peak > 0 else 0
            if dd > max_dd:
                max_dd = dd

    return {
        "total_days": total_days,
        "net_roi": round(net_roi, 2),
        "win_rate": round(win_rate, 1),
        "current_streak": current_streak,
        "max_drawdown": round(max_dd, 2),
        "total_trades": total_trades,
        "wins": wins,
        "losses": losses,
    }


def build_equity_chart(equity_curve: List[Dict]) -> go.Figure:
    if not equity_curve:
        fig = go.Figure()
        fig.update_layout(template="plotly_dark", paper_bgcolor="#0E1117", plot_bgcolor="#0E1117")
        return fig

    df = pd.DataFrame(equity_curve).groupby("date", as_index=False).last()
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df["date"], y=df["balance"],
        mode="lines+markers", name="Balance",
        line=dict(color="#00D4AA", width=2.5),
        marker=dict(size=6, color="#00D4AA"),
        fill="tozeroy", fillcolor="rgba(0, 212, 170, 0.08)",
    ))

    colors = ["#FFB800", "#FF8C00", "#FF6B6B", "#A855F7", "#3B82F6"]
    for i, m in enumerate(MILESTONE_THRESHOLDS):
        fig.add_hline(
            y=m, line_dash="dot", line_color=colors[i % len(colors)],
            annotation_text=f"${m:.0f}", annotation_position="right",
            annotation_font_color=colors[i % len(colors)],
        )

    fig.update_layout(
        template="plotly_dark", paper_bgcolor="#0E1117", plot_bgcolor="#0E1117",
        title=dict(text="Equity Curve with Milestone Thresholds", font=dict(size=16)),
        xaxis_title="Date", yaxis_title="Account Balance ($)",
        hovermode="x unified", margin=dict(l=40, r=40, t=50, b=40), height=420,
    )
    fig.update_xaxes(showgrid=True, gridcolor="#1e2530")
    fig.update_yaxes(showgrid=True, gridcolor="#1e2530")
    return fig


# =============================================================================
# MAIN
# =============================================================================
def main():
    init_session_state()
    check_new_day()

    current_tier = get_current_tier(st.session_state.balance)
    stake, _, is_house = get_recommended_stake(st.session_state.balance)
    pot_profit = potential_profit(stake, st.session_state.payout_rate)

    # ------------------------------------------------------------------
    # SIDEBAR
    # ------------------------------------------------------------------
    with st.sidebar:
        st.markdown("## ⚙️ Mode & Settings")
        st.markdown("---")

        mode = st.radio(
            "Operating Mode",
            ["Standard Fixed Tier Mode", "Custom Starting Capital Mode"],
            index=0 if st.session_state.mode == "Standard Fixed Tier Mode" else 1,
            key="mode_selector",
            help="Custom Starting Capital lets you begin at any balance. Tier stakes stay exactly as in your rules.",
        )

        if mode != st.session_state.mode:
            st.session_state.mode = mode
            if mode == "Standard Fixed Tier Mode":
                st.session_state.custom_capital = 10.0
                st.session_state.balance = 10.0
            else:
                # Keep whatever custom capital is set, apply it as starting balance
                st.session_state.balance = float(st.session_state.custom_capital)
            st.session_state.starting_balance_of_day = st.session_state.balance
            st.session_state.equity_curve = [{"date": date.today().isoformat(), "balance": st.session_state.balance}]
            st.session_state.trade_history = []
            st.session_state.daily_trades = 0
            st.session_state.day_locked = False
            st.session_state.house_money_active = False
            st.session_state.next_house_stake = 0.0
            st.rerun()

        if st.session_state.mode == "Custom Starting Capital Mode":
            custom = st.number_input(
                "Starting Capital ($)",
                min_value=1.0,
                value=float(st.session_state.custom_capital),
                step=10.0,
                help="Set any starting balance. Tier stakes stay fixed (e.g. $500 account → $100 stake).",
                key="custom_cap_input",
            )
            if abs(custom - st.session_state.custom_capital) > 0.01:
                st.session_state.custom_capital = custom
                st.session_state.balance = custom
                st.session_state.starting_balance_of_day = custom
                st.session_state.equity_curve = [{"date": date.today().isoformat(), "balance": custom}]
                st.session_state.trade_history = []
                st.session_state.daily_trades = 0
                st.session_state.day_locked = False
                st.session_state.house_money_active = False
                st.session_state.next_house_stake = 0.0
                st.rerun()

        st.markdown("---")
        payout = st.number_input(
            "Broker Payout Rate (%)",
            min_value=50.0, max_value=100.0,
            value=float(st.session_state.payout_rate), step=1.0,
            key="payout_input",
        )
        st.session_state.payout_rate = payout

        st.markdown("---")
        st.markdown("### Your Rules (Fixed Stakes)")
        st.caption("**Start $10** → stake **$5**")
        st.caption("**Reach $30** → stake **$10**")
        st.caption("**Reach $60** → stake **$20**")
        st.caption("**Reach $100** → stake **$25** + house-money")
        st.caption("**Reach $200** → stake **$30** + house-money")
        st.caption("**Reach $500** → stake **$100** + house-money")
        st.caption("**Below $5** → stake **$1** until $10")

        st.markdown("---")
        if st.button("🔄 Reset Account & Settings", use_container_width=True):
            reset_account()
            st.rerun()

        st.markdown("---")
        st.caption("High-risk model. Only trade with money you can afford to lose.")

    # ------------------------------------------------------------------
    # HEADER
    # ------------------------------------------------------------------
    st.markdown(
        "<h1 style='margin-bottom:0.2rem;'>📈 Tiered Milestone Money Manager</h1>",
        unsafe_allow_html=True,
    )
    st.caption("1 trade/day rule · Optional house-money chain on $100+ · Automatic step-down")

    for note in st.session_state.notifications[-4:]:
        ntype = note["type"]
        css = {
            "win": "banner-win", "loss": "banner-loss", "lock": "banner-lock",
            "stepdown": "banner-stepdown", "levelup": "banner-levelup", "house": "banner-house",
        }.get(ntype, "banner-lock")
        icon = {
            "win": "✅", "loss": "❌", "lock": "🔒",
            "stepdown": "⬇️", "levelup": "⬆️", "house": "💰",
        }.get(ntype, "ℹ️")
        st.markdown(f'<div class="{css}">{icon} {note["msg"]}</div>', unsafe_allow_html=True)

    if len(st.session_state.notifications) > 6:
        st.session_state.notifications = st.session_state.notifications[-6:]

    # ------------------------------------------------------------------
    # HERO CARD
    # ------------------------------------------------------------------
    st.markdown("### 🖥️ Today's Trade Terminal")

    if st.session_state.day_locked:
        allowance = "Day Locked – Return Tomorrow"
        allowance_color = "#FFB800"
    elif st.session_state.house_money_active:
        allowance = f"Optional House-Money Trade · Stake ${stake:.2f}"
        allowance_color = "#FFB800"
    else:
        remaining = max(0, 1 - st.session_state.daily_trades)
        allowance = f"{remaining}/1 Trade Remaining"
        allowance_color = "#00D4AA"

    house_badge = ""
    if is_house:
        house_badge = (
            '<span style="background:#FFB800;color:#000;padding:2px 8px;'
            'border-radius:4px;font-size:0.75rem;margin-left:8px;">HOUSE MONEY</span>'
        )

    hero_html = f"""
    <div class="hero-card">
        <div style="display:flex; flex-wrap:wrap; justify-content:space-between; gap:1.5rem;">
            <div>
                <p style="margin:0; color:#8B9CB3; font-size:0.9rem;">CURRENT BALANCE</p>
                <p class="hero-balance">${st.session_state.balance:,.2f}</p>
                <p class="hero-tier">{current_tier['name']} · {current_tier['description']}</p>
            </div>
            <div style="text-align:right;">
                <p style="margin:0; color:#8B9CB3; font-size:0.9rem;">TODAY'S STAKE {house_badge}</p>
                <p class="hero-stake">${stake:,.2f}</p>
                <p class="hero-profit">Potential Profit ≈ ${pot_profit:,.2f}</p>
                <p style="margin-top:0.6rem; color:{allowance_color}; font-weight:600;">{allowance}</p>
            </div>
        </div>
    </div>
    """
    st.markdown(hero_html, unsafe_allow_html=True)

    # ------------------------------------------------------------------
    # ACTION CONTROLS
    # ------------------------------------------------------------------
    can_trade = not st.session_state.day_locked

    if not can_trade:
        st.markdown(
            '<div class="banner-lock">🔒 MANDATORY MARKET EXIT: Return Tomorrow</div>',
            unsafe_allow_html=True,
        )
    elif st.session_state.house_money_active:
        st.markdown(
            f'<div class="banner-house">💰 Optional next trade ready '
            f'(50% of previous profit = ${stake:.2f}). '
            f'Take it or press “End Trading Day” to stop.</div>',
            unsafe_allow_html=True,
        )

    col1, col2, col3 = st.columns([1, 1, 1])

    with col1:
        pl_input = st.number_input(
            "Actual P/L Amount (optional)",
            value=0.0, step=0.01,
            help="Leave 0 to auto-calculate from stake × payout. Positive = win, negative = loss.",
            disabled=not can_trade,
            key="pl_input",
        )

    with col2:
        st.write("")
        st.write("")
        win_clicked = st.button(
            "✅ RECORD WIN", use_container_width=True, type="primary",
            disabled=not can_trade, key="btn_win",
        )

    with col3:
        st.write("")
        st.write("")
        loss_clicked = st.button(
            "❌ RECORD LOSS", use_container_width=True,
            disabled=not can_trade, key="btn_loss",
        )

    end_col1, end_col2, end_col3 = st.columns([1, 1, 1])
    with end_col2:
        if st.button(
            "⏹️ End Trading Day & Lock Terminal",
            use_container_width=True,
            disabled=st.session_state.day_locked,
            key="btn_end",
        ):
            end_trading_day()
            st.rerun()

    if win_clicked:
        pl = pl_input if pl_input != 0 else None
        if pl is not None and pl < 0:
            st.error("For a WIN, P/L must be positive (or leave at 0).")
        else:
            record_trade("WIN", pl if pl and pl > 0 else None)
            st.rerun()

    if loss_clicked:
        pl = pl_input if pl_input != 0 else None
        if pl is not None and pl > 0:
            st.error("For a LOSS, P/L must be negative (or leave at 0).")
        else:
            record_trade("LOSS", pl if pl and pl < 0 else None)
            st.rerun()

    st.markdown(
        '<div class="banner-warning">'
        "⚠️ <b>HIGH-RISK WARNING</b>: This system uses large single-trade risk (especially early tiers). "
        "Only use capital you can afford to lose. Strict 1-trade-per-day discipline is mandatory on smaller accounts."
        "</div>",
        unsafe_allow_html=True,
    )

    st.markdown("---")

    # ------------------------------------------------------------------
    # ANALYTICS
    # ------------------------------------------------------------------
    st.markdown("### 📊 Analytics & History")

    original_start = 10.0
    if st.session_state.mode == "Custom Starting Capital Mode":
        original_start = float(st.session_state.custom_capital)
    if st.session_state.trade_history:
        original_start = st.session_state.trade_history[0]["starting_balance"]

    metrics = compute_analytics(
        st.session_state.trade_history, st.session_state.balance, original_start
    )

    m1, m2, m3, m4, m5 = st.columns(5)
    m1.metric("Days Traded", metrics["total_days"])
    m2.metric("Net ROI", f"{metrics['net_roi']}%")
    m3.metric("Win Rate", f"{metrics['win_rate']}%")
    streak_val = metrics["current_streak"]
    m4.metric("Current Streak", f"{abs(streak_val)} {'W' if streak_val >= 0 else 'L'}")
    m5.metric("Max Drawdown", f"{metrics['max_drawdown']}%")

    st.plotly_chart(build_equity_chart(st.session_state.equity_curve), use_container_width=True)

    st.markdown("#### Complete Trade History")
    if st.session_state.trade_history:
        hist_df = pd.DataFrame(st.session_state.trade_history)
        display_df = hist_df[[
            "date", "tier", "starting_balance", "stake_used",
            "result", "pl", "house_money", "ending_balance"
        ]].copy()
        display_df.columns = [
            "Date", "Tier", "Start Bal", "Stake", "Result", "P/L", "House $", "End Bal"
        ]
        display_df = display_df.sort_values("Date", ascending=False).reset_index(drop=True)
        st.dataframe(
            display_df.style.format({
                "Start Bal": "${:.2f}", "Stake": "${:.2f}",
                "P/L": "${:.2f}", "End Bal": "${:.2f}",
            }),
            use_container_width=True, height=320,
        )
        csv = display_df.to_csv(index=False).encode("utf-8")
        st.download_button(
            label="📥 Export History to CSV",
            data=csv,
            file_name=f"trade_history_{date.today().isoformat()}.csv",
            mime="text/csv",
        )
    else:
        st.info("No trades recorded yet. Execute your first trade above.")

    st.markdown("---")
    st.caption("Tiered Milestone Money Manager · Matches your exact rules.")


if __name__ == "__main__":
    main()
