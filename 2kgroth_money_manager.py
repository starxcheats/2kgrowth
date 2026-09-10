"""
Tiered Milestone Money Management & Discipline Tracker
Production-ready Streamlit app — strict original rules + proportional scaling.
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, date
from typing import Dict, List, Optional, Tuple
import copy

# =============================================================================
# PAGE CONFIG & DARK TRADING TERMINAL THEME
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
        border: 1px solid #2a3441; border-radius: 12px;
        padding: 1.5rem 2rem; margin-bottom: 1.5rem;
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
# BASE TIERS ($10 system) — scaled in Proportional mode
# =============================================================================
BASE_TIERS = [
    {
        "key": "emergency",
        "name": "Emergency Mode",
        "min_balance": 0.0,
        "max_balance": 4.99,
        "stake": 1.0,
        "risk_pct": 25.0,
        "allows_house_money": False,
    },
    {
        "key": "tier1",
        "name": "Tier 1",
        "min_balance": 5.0,
        "max_balance": 29.99,
        "stake": 5.0,
        "risk_pct": 50.0,
        "allows_house_money": False,
    },
    {
        "key": "tier2",
        "name": "Tier 2",
        "min_balance": 30.0,
        "max_balance": 59.99,
        "stake": 10.0,
        "risk_pct": 33.3,
        "allows_house_money": False,
    },
    {
        "key": "tier3",
        "name": "Tier 3",
        "min_balance": 60.0,
        "max_balance": 99.99,
        "stake": 20.0,
        "risk_pct": 33.3,
        "allows_house_money": False,
    },
    {
        "key": "tier4",
        "name": "Tier 4",
        "min_balance": 100.0,
        "max_balance": 199.99,
        "stake": 25.0,
        "risk_pct": 25.0,
        "allows_house_money": True,
    },
    {
        "key": "tier5",
        "name": "Tier 5",
        "min_balance": 200.0,
        "max_balance": 499.99,
        "stake": 30.0,
        "risk_pct": 15.0,
        "allows_house_money": True,
    },
    {
        "key": "tier6",
        "name": "Tier 6",
        "min_balance": 500.0,
        "max_balance": float("inf"),
        "stake": 100.0,
        "risk_pct": 20.0,
        "allows_house_money": True,
    },
]

BASE_MILESTONES = [30.0, 60.0, 100.0, 200.0, 500.0]


def get_scale(mode: str, custom_capital: float) -> float:
    if mode == "Proportional Scaling Mode" and custom_capital > 0:
        return custom_capital / 10.0
    return 1.0


def build_tiers(scale: float) -> List[Dict]:
    tiers = []
    for t in BASE_TIERS:
        nt = copy.deepcopy(t)
        nt["min_balance"] = round(t["min_balance"] * scale, 2)
        nt["max_balance"] = (
            float("inf") if t["max_balance"] == float("inf")
            else round(t["max_balance"] * scale, 2)
        )
        nt["stake"] = round(t["stake"] * scale, 2)

        # Dynamic display names & descriptions
        if t["key"] == "emergency":
            nt["name"] = "Emergency Mode"
            nt["description"] = (
                f"Below ${5*scale:.0f} → stake ${nt['stake']:.0f} "
                f"until recover to ${10*scale:.0f} | Risk ~{t['risk_pct']}%"
            )
        elif t["key"] == "tier1":
            nt["name"] = f"Tier 1 (${10*scale:.0f} Base)"
            nt["description"] = (
                f"${10*scale:.0f} start · ${nt['stake']:.0f}/trade · "
                f"Risk {t['risk_pct']}% · 1 trade/day only"
            )
        elif t["key"] == "tier2":
            nt["name"] = f"Tier 2 (${30*scale:.0f})"
            nt["description"] = f"${nt['stake']:.0f}/trade · Risk {t['risk_pct']}% · 1 trade/day only"
        elif t["key"] == "tier3":
            nt["name"] = f"Tier 3 (${60*scale:.0f})"
            nt["description"] = f"${nt['stake']:.0f}/trade · Risk {t['risk_pct']}% · 1 trade/day only"
        elif t["key"] == "tier4":
            nt["name"] = f"Tier 4 (${100*scale:.0f})"
            nt["description"] = f"${nt['stake']:.0f}/trade · Risk {t['risk_pct']}% · optional house-money"
        elif t["key"] == "tier5":
            nt["name"] = f"Tier 5 (${200*scale:.0f})"
            nt["description"] = f"${nt['stake']:.0f}/trade · Risk {t['risk_pct']}% · optional house-money"
        elif t["key"] == "tier6":
            nt["name"] = f"Tier 6 (${500*scale:.0f}+)"
            nt["description"] = f"${nt['stake']:.0f}/trade · Risk {t['risk_pct']}% · optional house-money"

        tiers.append(nt)
    return tiers


def get_current_tier(balance: float, tiers: List[Dict]) -> Dict:
    for t in tiers:
        if t["min_balance"] <= balance <= t["max_balance"]:
            return t
    return tiers[-1]


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
    scale = get_scale(st.session_state.mode, st.session_state.custom_capital)
    start = round(10.0 * scale, 2)
    st.session_state.balance = start
    st.session_state.trade_history = []
    st.session_state.daily_trades = 0
    st.session_state.last_trade_date = None
    st.session_state.day_locked = False
    st.session_state.house_money_active = False
    st.session_state.next_house_stake = 0.0
    st.session_state.notifications = []
    st.session_state.starting_balance_of_day = start
    st.session_state.equity_curve = [{"date": date.today().isoformat(), "balance": start}]
    st.success("Account & settings reset successfully.")


def check_new_day():
    today = date.today().isoformat()
    if st.session_state.last_trade_date != today:
        st.session_state.daily_trades = 0
        st.session_state.day_locked = False
        st.session_state.house_money_active = False
        st.session_state.next_house_stake = 0.0
        st.session_state.starting_balance_of_day = st.session_state.balance


def get_recommended_stake(balance: float, tiers: List[Dict]) -> Tuple[float, Dict, bool]:
    tier = get_current_tier(balance, tiers)
    if st.session_state.house_money_active and st.session_state.next_house_stake > 0:
        return round(st.session_state.next_house_stake, 2), tier, True
    return tier["stake"], tier, False


def record_trade(result: str, pl_amount: Optional[float] = None):
    check_new_day()
    today = date.today().isoformat()
    scale = get_scale(st.session_state.mode, st.session_state.custom_capital)
    tiers = build_tiers(scale)
    payout = st.session_state.payout_rate

    if st.session_state.day_locked:
        st.session_state.notifications.append({
            "type": "lock",
            "msg": "Trading is locked for today. Return tomorrow.",
        })
        return

    balance_before = st.session_state.balance
    tier_before = get_current_tier(balance_before, tiers)
    stake, active_tier, is_house = get_recommended_stake(balance_before, tiers)

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

    tier_after = get_current_tier(balance_after, tiers)

    # ---- Discipline rules ----
    if result == "WIN":
        if active_tier["allows_house_money"]:
            # ≥ $100 (scaled): optional house-money chain
            next_stake = round(profit * 0.5, 2)
            st.session_state.house_money_active = True
            st.session_state.next_house_stake = next_stake
            st.session_state.day_locked = False
            st.session_state.notifications.append({
                "type": "house",
                "msg": (
                    f"WIN (+${profit:.2f}). "
                    f"Optional next trade available at 50% of this profit → stake ${next_stake:.2f}. "
                    f"Take it or End Trading Day to exit until tomorrow."
                ),
            })
        else:
            # < $100 (scaled): strict 1 trade/day → lock
            st.session_state.day_locked = True
            st.session_state.house_money_active = False
            st.session_state.next_house_stake = 0.0
            st.session_state.notifications.append({
                "type": "win",
                "msg": (
                    f"WIN (+${profit:.2f}). "
                    f"MANDATORY MARKET EXIT: 1 Win per day rule. Return tomorrow."
                ),
            })
    else:
        # Any LOSS → lock day
        st.session_state.day_locked = True
        st.session_state.house_money_active = False
        st.session_state.next_house_stake = 0.0
        st.session_state.notifications.append({
            "type": "loss",
            "msg": (
                f"LOSS (${abs(profit):.2f}). "
                f"MANDATORY MARKET EXIT: No revenge trading. Return tomorrow."
            ),
        })

    # Step-down / Level-up
    if tier_after["name"] != tier_before["name"]:
        if balance_after < balance_before:
            st.session_state.notifications.append({
                "type": "stepdown",
                "msg": (
                    f"STEP-DOWN: {tier_before['name']} → {tier_after['name']}. "
                    f"Next stake = ${tier_after['stake']:.2f}."
                ),
            })
        else:
            st.session_state.notifications.append({
                "type": "levelup",
                "msg": (
                    f"LEVEL-UP: {tier_before['name']} → {tier_after['name']}. "
                    f"Next stake = ${tier_after['stake']:.2f}."
                ),
            })

    if balance_after < 5.0 * scale:
        st.session_state.notifications.append({
            "type": "stepdown",
            "msg": (
                f"Emergency Mode: Balance below ${5*scale:.0f}. "
                f"Stake = ${1*scale:.0f} until recover to ${10*scale:.0f}."
            ),
        })


def end_trading_day():
    st.session_state.day_locked = True
    st.session_state.house_money_active = False
    st.session_state.next_house_stake = 0.0
    st.session_state.notifications.append({
        "type": "lock",
        "msg": "Trading day ended manually. Terminal locked until tomorrow.",
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


def build_equity_chart(equity_curve: List[Dict], scale: float) -> go.Figure:
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
    for i, m in enumerate(BASE_MILESTONES):
        scaled = round(m * scale, 2)
        fig.add_hline(
            y=scaled, line_dash="dot", line_color=colors[i % len(colors)],
            annotation_text=f"${scaled:.0f}", annotation_position="right",
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

    scale = get_scale(st.session_state.mode, st.session_state.custom_capital)
    tiers = build_tiers(scale)
    current_tier = get_current_tier(st.session_state.balance, tiers)
    stake, _, is_house = get_recommended_stake(st.session_state.balance, tiers)
    pot_profit = potential_profit(stake, st.session_state.payout_rate)

    # ------------------------------------------------------------------
    # SIDEBAR
    # ------------------------------------------------------------------
    with st.sidebar:
        st.markdown("## ⚙️ Mode & Settings")
        st.markdown("---")

        mode = st.radio(
            "Operating Mode",
            ["Standard Fixed Tier Mode", "Proportional Scaling Mode"],
            index=0 if st.session_state.mode == "Standard Fixed Tier Mode" else 1,
            key="mode_selector",
        )

        if mode != st.session_state.mode:
            st.session_state.mode = mode
            if mode == "Standard Fixed Tier Mode":
                st.session_state.custom_capital = 10.0
                st.session_state.balance = 10.0
            else:
                new_scale = st.session_state.custom_capital / 10.0
                st.session_state.balance = round(10.0 * new_scale, 2)
            st.session_state.starting_balance_of_day = st.session_state.balance
            st.session_state.equity_curve = [{"date": date.today().isoformat(), "balance": st.session_state.balance}]
            st.session_state.trade_history = []
            st.session_state.daily_trades = 0
            st.session_state.day_locked = False
            st.session_state.house_money_active = False
            st.session_state.next_house_stake = 0.0
            st.rerun()

        if st.session_state.mode == "Proportional Scaling Mode":
            custom = st.number_input(
                "Custom Starting Capital ($)",
                min_value=10.0,
                value=float(st.session_state.custom_capital),
                step=10.0,
                help="Scales ALL milestones and stakes from the $10 base. Example: $1,000 = 100× scale.",
                key="custom_cap_input",
            )
            if abs(custom - st.session_state.custom_capital) > 0.01:
                new_scale = custom / 10.0
                st.session_state.custom_capital = custom
                st.session_state.balance = round(10.0 * new_scale, 2)
                st.session_state.starting_balance_of_day = st.session_state.balance
                st.session_state.equity_curve = [{"date": date.today().isoformat(), "balance": st.session_state.balance}]
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
        st.markdown("### Tier Reference (Current Scale)")
        st.caption(f"**Start** ${10*scale:.0f} → stake **${5*scale:.0f}** (Tier 1)")
        st.caption(f"**${30*scale:.0f}–${60*scale-0.01:.0f}** → stake **${10*scale:.0f}** (Tier 2)")
        st.caption(f"**${60*scale:.0f}–${100*scale-0.01:.0f}** → stake **${20*scale:.0f}** (Tier 3)")
        st.caption(f"**${100*scale:.0f}–${200*scale-0.01:.0f}** → stake **${25*scale:.0f}** + house $")
        st.caption(f"**${200*scale:.0f}–${500*scale-0.01:.0f}** → stake **${30*scale:.0f}** + house $")
        st.caption(f"**${500*scale:.0f}+** → stake **${100*scale:.0f}** + house $")
        st.caption(f"**Below ${5*scale:.0f}** → stake **${1*scale:.0f}** until ${10*scale:.0f}")

        st.markdown("---")
        if st.button("🔄 Reset Account & Settings", use_container_width=True):
            reset_account()
            st.rerun()

        st.markdown("---")
        st.caption("High-risk model (15%–50% per trade). Only use capital you can afford to lose.")

    # ------------------------------------------------------------------
    # HEADER + NOTIFICATIONS
    # ------------------------------------------------------------------
    st.markdown(
        "<h1 style='margin-bottom:0.2rem;'>📈 Tiered Milestone Money Manager</h1>",
        unsafe_allow_html=True,
    )
    st.caption("1 trade/day · Optional house-money chain on Tier 4+ · Automatic step-down / level-up")

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
        allowance = "0/1 – Day Locked"
        allowance_color = "#FFB800"
    elif st.session_state.house_money_active:
        allowance = "Optional House Money Trade Available"
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
            f'<div class="banner-house">💰 Optional house-money trade ready '
            f'(50% of previous profit = ${stake:.2f}). '
            f'Take it or press End Trading Day to stop.</div>',
            unsafe_allow_html=True,
        )

    col1, col2, col3 = st.columns([1, 1, 1])

    with col1:
        pl_input = st.number_input(
            "Actual P/L Amount (optional)",
            value=0.0, step=0.01,
            help="Leave 0 to auto-calc from stake × payout. Positive = win, negative = loss.",
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
        "⚠️ <b>HIGH-RISK WARNING</b>: This model uses 15%–50% single-trade risk. "
        "Designed for high-risk accounts only. Never risk money you cannot afford to lose."
        "</div>",
        unsafe_allow_html=True,
    )

    st.markdown("---")

    # ------------------------------------------------------------------
    # ANALYTICS & HISTORY
    # ------------------------------------------------------------------
    st.markdown("### 📊 Analytics & History")

    original_start = round(10.0 * scale, 2)
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

    st.plotly_chart(
        build_equity_chart(st.session_state.equity_curve, scale),
        use_container_width=True,
    )

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
    st.caption("Tiered Milestone Money Manager · Strict original rules + proportional scaling.")


if __name__ == "__main__":
    main()
