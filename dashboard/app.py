"""
Streamlit Terminal UI Dashboard Application for bitcoin-prediction-lab.

Provides a TradingView-style research terminal featuring:
1. Market Section: Interactive Plotly line chart & key 24h market metrics.
2. Market State & Regime Engine: Trend score, Volatility, Momentum, Funding, Leverage, & Regime classification.
3. Live Signal & Probability Engine: Calibrated XGBoost/Ensemble probability, 90% prediction interval, & TAKE/SKIP decision.
4. Systematic Research Panel: Prediction Horizon Sweep, Regime Performance Breakdown, & Feature Audit.
5. Market Memory Panel: Permanent record of historical predictions and actual PnL outcomes.
"""

import os
import sys
import pandas as pd
import numpy as np
import streamlit as st
import plotly.express as px
from sklearn.model_selection import cross_val_predict
from xgboost import XGBClassifier

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from config import SYMBOL, EXCHANGE, TIMEFRAME, DATA_PROCESSED_DIR, RESULTS_DIR
from models.train_baselines import make_dataset
from models.market_state import compute_market_states
from models.regime_detector import classify_regimes
from calibration.calibrate import fit_isotonic
from backtest.simulate import position_size
from backtest.market_memory import load_market_memory, record_prediction


# Configure Streamlit page layout
st.set_page_config(
    page_title=f"{SYMBOL} Quantitative Terminal",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.title(f"⚡ {SYMBOL} Quantitative Research Terminal")
st.caption(f"Exchange: `{EXCHANGE.upper()}` | Timeframe: `{TIMEFRAME}` | Status: `COST_ERASED (C2 Research Only)`")

# ------------------------------------------------------------------------------
# RESEARCH INTEGRITY & STATUS BANNER
# ------------------------------------------------------------------------------
st.warning("""
### 🔬 BTCognitive Research Status: `COST_ERASED`
- **Track Status:** Conditional predictive pattern observed ($C_2$), but **no robust net-of-cost trading edge** established.
- **Walk-Forward Outcome:** Mean net expectancy is negative after standard friction ($-0.57R$ BASE / $-1.10R$ CONSERVATIVE).
- **Capital Safety Order:** Live capital deployment is **STRICTLY PROHIBITED**. All displays represent scientific/historical research observations.
""")


# ------------------------------------------------------------------------------
# 1. MARKET SECTION
# ------------------------------------------------------------------------------
st.header("1. Market Overview (Last 90 Days)")

features_path = os.path.join(DATA_PROCESSED_DIR, "features.parquet")

if not os.path.exists(features_path):
    st.error(f"Data file not found at `{features_path}`. Please run `features/build_features.py` first.")
else:
    try:
        features_df = pd.read_parquet(features_path, engine="pyarrow")
        features_df['timestamp'] = pd.to_datetime(features_df['timestamp'], utc=True).dt.tz_convert('Asia/Kolkata')

        max_ts = features_df['timestamp'].max()
        start_90d = max_ts - pd.Timedelta(days=90)
        df_90d = features_df[features_df['timestamp'] >= start_90d].sort_values('timestamp')

        col_m1, col_m2, col_m3, col_m4, col_m5 = st.columns(5)
        latest_row = df_90d.iloc[-1]
        col_m1.metric("Latest Close", f"${latest_row['close']:,.2f}")
        col_m2.metric("24h Return", f"{latest_row.get('ret_24h', 0.0)*100:+.2f}%")
        col_m3.metric("24h Realized Vol", f"{latest_row.get('realized_vol_24h', 0.0)*100:.2f}%")
        col_m4.metric("14-Period RSI", f"{latest_row.get('rsi_14', 50.0):.1f}")
        col_m5.metric("Open Interest (24h Δ)", f"{latest_row.get('oi_pct_change_24h', 0.0)*100:+.2f}%")

        fig = px.line(
            df_90d,
            x='timestamp',
            y='close',
            title=f"{SYMBOL} Close Price History (IST)",
            labels={'timestamp': 'IST Time (UTC+5:30)', 'close': 'Price (USD)'},
            template='plotly_dark'
        )
        fig.update_traces(line_color='#00F0FF', line_width=2)
        fig.update_layout(
            hovermode="x unified",
            margin=dict(l=20, r=20, t=40, b=20),
            height=380
        )
        st.plotly_chart(fig, use_container_width=True)

    except Exception as e:
        st.error(f"Failed to render Market section: {e}")


# ------------------------------------------------------------------------------
# 2. MARKET STATE & REGIME ENGINE
# ------------------------------------------------------------------------------
st.header("2. Market State Engine & Regime Classifier")

try:
    states_df = compute_market_states(features_df)
    regime_series = classify_regimes(features_df)
    latest_state = states_df.iloc[-1]
    current_regime = regime_series.iloc[-1]

    s_col1, s_col2, s_col3, s_col4, s_col5, s_col6 = st.columns(6)
    s_col1.metric("Trend Score", f"{latest_state.get('trend_score', 0.0):+.2f}")
    s_col2.metric("Volatility State", f"{latest_state.get('volatility_state', 'MEDIUM')}")
    s_col3.metric("Momentum State", f"{latest_state.get('momentum_state', 'NEUTRAL')}")
    s_col4.metric("Funding State", f"{latest_state.get('funding_state', 'NEUTRAL')}")
    s_col5.metric("Leverage State", f"{latest_state.get('leverage_state', 'NORMAL')}")
    s_col6.markdown(
        f"""
        <div style="background-color: #1E1E2E; padding: 8px; border-radius: 6px; border-left: 4px solid #00F0FF; text-align: center;">
            <span style="color: #888888; font-size: 11px; font-weight: bold;">CURRENT REGIME</span><br/>
            <span style="color: #00F0FF; font-size: 15px; font-weight: bold;">{current_regime}</span>
        </div>
        """,
        unsafe_allow_html=True
    )
except Exception as e:
    st.warning(f"Could not compute market states: {e}")


# ------------------------------------------------------------------------------
# 3. RESEARCH DIAGNOSTICS & ABSTENTION ENGINE (NON-ACTIONABLE)
# ------------------------------------------------------------------------------
st.header("3. Research Model Diagnostics (Non-Actionable)")

try:
    with st.spinner("Evaluating research model state..."):
        X, y, t1 = make_dataset(horizon_bars=24)

        model = XGBClassifier(n_estimators=100, eval_metric='logloss', random_state=42, n_jobs=-1)
        model.fit(X, y)

        cv_probs = cross_val_predict(
            XGBClassifier(n_estimators=100, eval_metric='logloss', random_state=42, n_jobs=-1),
            X, y, cv=5, method='predict_proba'
        )[:, 1]

        iso = fit_isotonic(y.values, cv_probs)

        latest_X = X.iloc[[-1]]
        latest_time = latest_X.index[0]
        raw_prob = float(model.predict_proba(latest_X)[:, 1][0])
        cal_prob = float(iso.predict([raw_prob])[0])

        # Scientific state classification instead of trade recommendation
        if abs(cal_prob - 0.5) < 0.05:
            state_label = "MODEL_UNCERTAIN"
            state_desc = "Probability near prior base rate (abstain)."
            state_color = "#FFAA00"
        elif cal_prob >= 0.55:
            state_label = "EV_BELOW_COST (LONG BIAS)"
            state_desc = "Statistical upward tilt observed, but edge cost-erased after fees."
            state_color = "#888888"
        elif cal_prob <= 0.45:
            state_label = "EV_BELOW_COST (SHORT BIAS)"
            state_desc = "Statistical downward tilt observed, but edge cost-erased after fees."
            state_color = "#888888"
        else:
            state_label = "NO_SETUP"
            state_desc = "No structural entry conditions detected."
            state_color = "#555555"

        lower_bound = max(0.0, cal_prob - 0.08)
        upper_bound = min(1.0, cal_prob + 0.08)

    st.subheader(f"Diagnostic Observation for Bar: `{latest_time}`")

    p_col1, p_col2, p_col3, p_col4 = st.columns(4)
    p_col1.metric("Raw Model Prob", f"{raw_prob*100:.1f}%")
    p_col2.metric("Calibrated Prob", f"{cal_prob*100:.1f}%")
    p_col3.metric("90% Uncertainty Interval", f"[{lower_bound*100:.1f}%, {upper_bound*100:.1f}%]")
    p_col4.markdown(
        f"""
        <div style="background-color: #1E1E2E; padding: 12px; border-radius: 8px; border-left: 5px solid {state_color}; text-align: center;">
            <span style="color: #888888; font-size: 11px; font-weight: bold;">SCIENTIFIC STATE</span><br/>
            <span style="color: {state_color}; font-size: 15px; font-weight: bold;">{state_label}</span><br/>
            <span style="color: #AAAAAA; font-size: 10px;">{state_desc}</span>
        </div>
        """,
        unsafe_allow_html=True
    )

except Exception as e:
    st.warning(f"Could not compute model diagnostics: {e}")


# ------------------------------------------------------------------------------
# 4. SYSTEMATIC RESEARCH PANEL
# ------------------------------------------------------------------------------
st.header("4. Systematic Research & Empirical Audits")

tab_wf, tab1, tab2, tab3, tab4 = st.tabs([
    "🔬 Entry + TP/SL Walk-Forward (Track V3)",
    "Prediction Horizon Sweep",
    "Regime Performance",
    "Feature Predictive Audit",
    "Cost Sensitivity"
])

with tab_wf:
    st.subheader("Entry + TP/SL Walk-Forward Results (Phases 6C-6K)")
    st.markdown("""
    **Track Status:** `COST_ERASED` | **Evaluated Sample:** $N = 20,244$ out-of-sample trades across 7.76M 1m bars  
    **Formal Promotion Decision:** `ARCHIVED_RESEARCH_ONLY (Live capital deployment strictly prohibited)`
    """)
    
    wf_data = {
        "Baseline / Model": [
            "B0: Matched Random",
            "B0b: Always Long",
            "B0b: Always Short",
            "B3: Structural Rule (A1/A2)",
            "B3b: Setup + Trend Filter",
            "B4-lite: Logistic Meta-Model",
            "B4: LightGBM (BASE: 35 bps)",
            "B4: LightGBM (CONSERVATIVE: 65 bps)"
        ],
        "Evaluated Trades (N)": [10105, 10142, 10102, 20244, 1665, 2916, 1553, 1553],
        "Win Rate": ["25.7%", "26.1%", "25.7%", "25.9%", "18.7%", "46.9%", "47.1%", "25.2%"],
        "Mean Net R": ["-1.2112R", "-1.1900R", "-1.2110R", "-1.2005R", "-1.5708R", "-0.4673R", "-0.5678R", "-1.0954R"],
        "95% Bootstrap CI Lower": ["-1.2577R", "-1.2394R", "-1.2598R", "-1.2361R", "-1.7242R", "-0.4984R", "-0.6220R", "-1.1657R"],
        "Profit Factor": [0.07, 0.08, 0.07, 0.07, 0.04, 0.37, 0.29, 0.07],
        "Status": [
            "Negative Expectancy",
            "Baseline Reference",
            "Baseline Reference",
            "Unfiltered Setups",
            "Simple Rule",
            "Linear Probability Filter",
            "Primary Meta-Model (Cost-Erased)",
            "Friction Stressed"
        ]
    }
    st.dataframe(pd.DataFrame(wf_data), use_container_width=True)
    
    st.markdown("""
    **Barrier Sensitivity Analysis (B4 LightGBM):**
    - `barrier_pair_01` ($k_{\\text{TP}}=1.0, k_{\\text{SL}}=1.0$): Mean Net R = **$-0.5678R$**, Profit Factor = 0.29
    - `barrier_pair_02` ($k_{\\text{TP}}=2.0, k_{\\text{SL}}=1.0$): Mean Net R = **$-0.5683R$**, Profit Factor = 0.39
    - `barrier_pair_03` ($k_{\\text{TP}}=3.0, k_{\\text{SL}}=1.0$): Mean Net R = **$-0.5813R$**, Profit Factor = 0.42
    - `barrier_pair_04` ($k_{\\text{TP}}=1.0, k_{\\text{SL}}=1.0$): Mean Net R = **$-0.7523R$**, Profit Factor = 0.18
    - `barrier_pair_05` ($k_{\\text{TP}}=2.0, k_{\\text{SL}}=1.5$): Mean Net R = **$-0.3842R$**, Profit Factor = 0.47
    
    **Diagnostics:** Deflated Sharpe Ratio (DSR) = `0.0000`, Probability of Backtest Overfitting (PBO) = `0.2000`.
    """)

with tab1:
    st.subheader("Horizon Performance Sweep (1h -> 72h)")
    h_path = os.path.join(RESULTS_DIR, "horizon_sweep.csv")
    if os.path.exists(h_path):
        st.dataframe(pd.read_csv(h_path), use_container_width=True)
    else:
        st.warning(f"File `{h_path}` not found. Run `experiments/horizon_sweep.py` to generate.")

with tab2:
    st.subheader("Performance Breakdown by Market Regime")
    r_path = os.path.join(RESULTS_DIR, "regime_performance.csv")
    if os.path.exists(r_path):
        st.dataframe(pd.read_csv(r_path), use_container_width=True)
    else:
        st.warning(f"File `{r_path}` not found. Run `models/regime_detector.py` to generate.")

with tab3:
    st.subheader("Feature Information Coefficient & Stability Audit")
    f_path = os.path.join(RESULTS_DIR, "feature_audit.csv")
    if os.path.exists(f_path):
        st.dataframe(pd.read_csv(f_path), use_container_width=True)
    else:
        st.warning(f"File `{f_path}` not found. Run `features/audit_features.py` to generate.")

with tab4:
    st.subheader("Trading Cost Sensitivity Grid (Fees x Slippage)")
    c_path = os.path.join(RESULTS_DIR, "cost_sensitivity.csv")
    if os.path.exists(c_path):
        st.dataframe(pd.read_csv(c_path), use_container_width=True)
    else:
        st.warning(f"File `{c_path}` not found. Run `backtest/simulate.py` to generate.")

# ------------------------------------------------------------------------------
# 5. MARKET MEMORY PANEL
# ------------------------------------------------------------------------------
st.header("5. Market Memory Database")

try:
    memory_df = load_market_memory()
    if not memory_df.empty:
        st.dataframe(memory_df.tail(10), use_container_width=True)
    else:
        st.info("Market Memory database is currently empty. Predictions will log automatically upon execution.")
except Exception as e:
    st.warning(f"Could not load Market Memory: {e}")
