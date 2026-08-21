# 👥 Hawkes Microstructure Shadow Mode Evaluation Report

## 1. Dual-Track Shadow Telemetry Snapshot

| step | current_price | production_24h_upper | production_24h_lower | hawkes_5m_mfe_p50_bps | hawkes_5m_mae_p50_bps | hawkes_direction | status |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 64800.0 | 66501.0 | 62661.6 | 13.7 | 13.6 | BEARISH | SHADOW_RECORDED |
| 2 | 64866.67 | 66569.42 | 62726.07 | 14.1 | 14.0 | NEUTRAL | SHADOW_RECORDED |
| 3 | 64933.33 | 66637.83 | 62790.53 | 13.9 | 14.2 | BEARISH | SHADOW_RECORDED |
| 4 | 65000.0 | 66706.25 | 62855.0 | 13.1 | 13.8 | NEUTRAL | SHADOW_RECORDED |
| 5 | 65066.67 | 66774.67 | 62919.47 | 12.9 | 14.2 | NEUTRAL | SHADOW_RECORDED |
| 6 | 65133.33 | 66843.08 | 62983.93 | 12.3 | 13.6 | BEARISH | SHADOW_RECORDED |
| 7 | 65200.0 | 66911.5 | 63048.4 | 13.8 | 14.4 | NEUTRAL | SHADOW_RECORDED |
| 8 | 65266.67 | 66979.92 | 63112.87 | 12.8 | 13.4 | BEARISH | SHADOW_RECORDED |
| 9 | 65333.33 | 67048.33 | 63177.33 | 12.9 | 13.0 | BEARISH | SHADOW_RECORDED |
| 10 | 65400.0 | 67116.75 | 63241.8 | 13.6 | 13.8 | BEARISH | SHADOW_RECORDED |

## 2. Shadow Safety Invariants

- **Zero Production Interference:** Hawkes short-horizon telemetry is logged strictly in shadow isolation and does not alter production 24h Ridge forecasts or API states.
