# BTCognitive — Prospective Coinbase Level-2 (L2) Microstructure Specification & Architectural Design (V32.30)

**Date:** 2026-10-25  
**Version:** V32.30  
**Operating Posture:** `OFFLINE_RESEARCH_ONLY`  
**Live Execution Authorization:** `DISABLED` (Permanently fail-closed)  
**Lead Quantitative Architect:** Agent 3  
**Status:** DORMANT ARCHITECTURAL DESIGN (No active collector started; opt-in design only)  

---

## 1. Literature & Theoretical Foundation

Recent market microstructure literature demonstrates that order book dynamics contain high-frequency information regarding quote changes, trade arrival toxicity, and immediate price impact:
1. **Cont, Kukanov & Stoikov (2014):** *"The Price Impact of Order Book Events"*, Journal of Financial Econometrics. Demonstrates that Order Flow Imbalance (OFI)—the net accumulation of limit orders, cancellations, and market fills at the best quotes—exhibits a contemporaneous linear relationship with price changes.
2. **Journal of Financial Markets (2026):** *"Order flow and cryptocurrency returns"*, DOI: 10.1016/j.finmar.2026.101047. Cross-sectional multi-currency study confirming that net order flow explains short-horizon crypto returns.
3. **SSRN Working Paper (July/August 2026):** *"The Fading Alpha of Crypto Order Flow Imbalance"*. Demonstrates that the predictive efficacy of OFI decays rapidly over extended out-of-sample windows and fails to predict multi-day directional trends once transaction costs are deducted.

### Key Conceptual Separation: Entry Timing vs. Macro Direction
> [!IMPORTANT]
> **Microstructure Horizon Boundary:**
> Level-2 order flow imbalance and bid/ask volume toxicity operate on millisecond-to-minute horizons (half-life $< 5$ minutes). They are mathematically suited for **entry timing, execution slippage reduction, and toxic breakout rejection**, but **MUST NEVER be assumed to forecast 72h–168h macro directional drift**.

---

## 2. Official Coinbase Exchange WebSocket Protocol Specification

Derived directly from official Coinbase Exchange Developer Documentation ([Coinbase WebSocket Reference](https://docs.cdp.coinbase.com/exchange/docs/websocket-channels)):

### 2.1 Connection & Subscription Endpoint
- **WebSocket URL:** `wss://ws-feed.exchange.coinbase.com`
- **Authorized Product:** `BTC-USD` (Spot only)
- **Subscription Channels:**
  1. `level2_batch`: Throttled Level-2 order book updates published every 50ms (or `level2` for raw deltas).
  2. `heartbeat`: Periodic heartbeat messages confirming socket liveness and current sequence numbers.
  3. `matches`: Real-time stream of executed trades with buyer/seller aggressor side tags.

### 2.2 Subscription Payload (Strict JSON)
```json
{
  "type": "subscribe",
  "product_ids": ["BTC-USD"],
  "channels": [
    "level2_batch",
    "heartbeat",
    "matches"
  ]
}
```

### 2.3 Message Ingestion & State Reconstruction
1. **Initial Full Snapshot (`snapshot` message):**
   ```json
   {
     "type": "snapshot",
     "product_id": "BTC-USD",
     "bids": [["80000.00", "1.520"], ["79999.50", "0.450"]],
     "asks": [["80000.50", "0.850"], ["80001.00", "2.100"]]
   }
   ```
   The local book initializes with sorted bids (descending) and asks (ascending).
2. **Delta Updates (`l2update` message):**
   ```json
   {
     "type": "l2update",
     "product_id": "BTC-USD",
     "changes": [
       ["buy", "80000.00", "3.200"],
       ["sell", "80000.50", "0.000"]
     ],
     "time": "2026-10-25T12:00:00.123456Z"
   }
   ```
   - If size $> 0$: insert or update the level.
   - If size $== 0$: remove the price level entirely.
3. **Trade Fills (`match` message):**
   ```json
   {
     "type": "match",
     "trade_id": 987654321,
     "sequence": 12345678,
     "maker_order_id": "...",
     "taker_order_id": "...",
     "time": "2026-10-25T12:00:00.150000Z",
     "product_id": "BTC-USD",
     "size": "0.250",
     "price": "80000.50",
     "side": "buy"
   }
   ```

---

## 3. Resilient Fault-Tolerance & Gap Invalidation Rules

To guarantee epistemic data integrity without synthetic interpolation:
1. **Sequence & Heartbeat Monitoring:**  
   The client must verify continuous incrementing message sequences and heartbeats received at least once every 5 seconds.
2. **Reconnect & Desynchronization Invalidation:**  
   If a WebSocket drop, sequence gap, or network desynchronization occurs:
   - The current book state is marked `CORRUPTED_DISCONNECTED`.
   - All microstructure feature calculations are immediately flagged `FEATURE_UNAVAILABLE`.
   - The socket reconnects, issues a fresh `subscribe` message, and waits for a new authoritative `snapshot`.
   - Zero interpolation or synthetic reconstruction is permitted during the outage interval.
3. **Clock Alignment & Availability Semantics:**  
   Every captured L2 update and trade match records two distinct timestamps:
   - `exchange_time_utc`: ISO-8601 timestamp issued by Coinbase Exchange matching engine.
   - `local_received_at_utc`: High-resolution local clock time when the packet was read from the TCP socket buffer.
   - `available_time_utc` for feature extraction is strictly $\ge \text{local\_received\_at\_utc}$. Zero lookahead.

---

## 4. Causal Feature Engineering Specification

At any decision timestamp $t$ (e.g. closed hourly candle boundary), microstructure features are computed strictly over the preceding aggregation interval $[t - \Delta, t]$:

### 4.1 Order Book Imbalance ($\text{OBI}_K$)
Computed at fixed depth horizons ($K \in \{5, 10, 25\}$ levels):
$$\text{OBI}_K(t) = \frac{\sum_{i=1}^K V_{\text{bid}, i}(t) - \sum_{i=1}^K V_{\text{ask}, i}(t)}{\sum_{i=1}^K V_{\text{bid}, i}(t) + \sum_{i=1}^K V_{\text{ask}, i}(t)} \in [-1.0, +1.0]$$

### 4.2 Order Flow Imbalance ($\text{OFI}$)
Following Cont et al. (2014), across successive top-of-book updates $k = 1, \dots, N$:
$$\Delta Q_B(k) = \begin{cases} q_B(k) & \text{if } P_B(k) > P_B(k-1) \\ q_B(k) - q_B(k-1) & \text{if } P_B(k) = P_B(k-1) \\ -q_B(k-1) & \text{if } P_B(k) < P_B(k-1) \end{cases}$$
$$\Delta Q_A(k) = \begin{cases} -q_A(k) & \text{if } P_A(k) > P_A(k-1) \\ q_A(k) - q_A(k-1) & \text{if } P_A(k) = P_A(k-1) \\ q_A(k-1) & \text{if } P_A(k) < P_A(k-1) \end{cases}$$
$$\text{OFI}_{\Delta}(t) = \sum_{k \in [t-\Delta, t]} \left( \Delta Q_B(k) - \Delta Q_A(k) \right)$$

### 4.3 Aggressor Trade Volume Delta ($\text{CVD}$)
Cumulative Volume Delta from executed matches:
$$\text{CVD}_{\Delta}(t) = \sum_{j \in [t-\Delta, t]} V_{\text{buy}, j} - \sum_{j \in [t-\Delta, t]} V_{\text{sell}, j}$$

### 4.4 Top-of-Book Spread Friction
$$\text{Spread}_{\text{bps}}(t) = \frac{P_{\text{ask}}(t) - P_{\text{bid}}(t)}{\frac{1}{2}(P_{\text{ask}}(t) + P_{\text{bid}}(t))} \times 10{,}000$$

---

## 5. Storage Schema & Non-Execution Contract

- **Storage Location (Prospective):** `data/prospective_l2/coinbase_btc_usd/YYYY-MM-DD/`
- **Format:** Snappy-compressed Apache Parquet partitioned by UTC date.
- **Dormant Status:** No collector process is launched in V32.30. Implementation is strictly opt-in and requires explicit future authorization.
- **Fail-Closed Runtime Integration:** In the current runtime, requests for L2 features in `DataContractValidator` continue to fail closed with `FEATURE_UNAVAILABLE` until an authenticated prospective collection has run for $\ge 30$ days.
