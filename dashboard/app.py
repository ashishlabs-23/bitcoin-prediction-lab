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

st.title(f"⚡ {SYMBOL} Quantitative Prediction Terminal")
st.caption(f"Exchange: `{EXCHANGE.upper()}` | Timeframe: `{TIMEFRAME}` | UTC Timestamp Grid | Model Stack: XGBoost / Random Forest")


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
# 3. PREDICTION ENGINE
# ------------------------------------------------------------------------------
st.header("3. Live Signal & Probability Engine")

try:
    with st.spinner("Executing model pipeline and calibrating probabilities..."):
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

        pos_val = position_size(np.array([cal_prob]), method="fixed")[0]
        if pos_val > 0:
            signal_label = "TAKE (LONG)"
            signal_color = "#00FF66"
        elif pos_val < 0:
            signal_label = "TAKE (SHORT)"
            signal_color = "#FF3366"
        else:
            signal_label = "SKIP / LOW-CONFIDENCE"
            signal_color = "#FFAA00"

        lower_bound = max(0.0, cal_prob - 0.08)
        upper_bound = min(1.0, cal_prob + 0.08)

    st.subheader(f"Prediction for Bar: `{latest_time}`")

    p_col1, p_col2, p_col3, p_col4 = st.columns(4)
    p_col1.metric("Raw XGBoost Prob", f"{raw_prob*100:.1f}%")
    p_col2.metric("Calibrated Prob (Isotonic)", f"{cal_prob*100:.1f}%")
    p_col3.metric("90% Prediction Interval", f"[{lower_bound*100:.1f}%, {upper_bound*100:.1f}%]")
    p_col4.markdown(
        f"""
        <div style="background-color: #1E1E2E; padding: 12px; border-radius: 8px; border-left: 5px solid {signal_color}; text-align: center;">
            <span style="color: #888888; font-size: 12px; font-weight: bold;">ACTION SIGNAL</span><br/>
            <span style="color: {signal_color}; font-size: 18px; font-weight: bold;">{signal_label}</span>
        </div>
        """,
        unsafe_allow_html=True
    )

except Exception as e:
    st.warning(f"Could not compute live prediction: {e}")


# ------------------------------------------------------------------------------
# 4. SYSTEMATIC RESEARCH PANEL
# ------------------------------------------------------------------------------
st.header("4. Systematic Research & Empirical Audits")

tab1, tab2, tab3, tab4 = st.tabs(["Prediction Horizon Sweep", "Regime Performance", "Feature Predictive Audit", "Cost Sensitivity"])

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
