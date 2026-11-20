import pandas as pd
import numpy as np

df = pd.read_csv('research/reports/offline_mvp/20261031_330320_v33_03b_htf_closure/v33_3b_excluded_trade_classification.csv')
df['entry_dt'] = pd.to_datetime(df['entry_time'])
df['net_vip0_26'] = df['gross_return_bps'] - 26.0
df['net_vip0_24'] = df['gross_return_bps'] - 24.0

# 1. V33.3A index-based 60/40 split
train_60 = df.iloc[:116]
test_40 = df.iloc[116:]

print('--- V33.3A Index 60/40 Split (under 26 bps cost) ---')
train_filt = train_60[train_60['action_v33_3a'] == 'KEEP']
test_filt = test_40[test_40['action_v33_3a'] == 'KEEP']
print(f"Train (N={len(train_60)}): Base Net = {train_60['net_vip0_26'].mean():.2f} bps, Filtered Net = {train_filt['net_vip0_26'].mean():.2f} bps (N={len(train_filt)})")
print(f"Test (N={len(test_40)}): Base Net = {test_40['net_vip0_26'].mean():.2f} bps, Filtered Net = {test_filt['net_vip0_26'].mean():.2f} bps (N={len(test_filt)})")

print('\n--- V33.3B Calendar Split (2022-2023 vs 2024-2026) under 26 bps ---')
cal_is = df[df['entry_dt'] < '2024-01-01']
cal_oos = df[df['entry_dt'] >= '2024-01-01']
is_filt = cal_is[cal_is['action_v33_3a'] == 'KEEP']
oos_filt = cal_oos[cal_oos['action_v33_3a'] == 'KEEP']
print(f"IS 2022-2023 (N={len(cal_is)}): Base Net = {cal_is['net_vip0_26'].mean():.2f} bps, Filtered Net = {is_filt['net_vip0_26'].mean():.2f} bps (N={len(is_filt)})")
print(f"OOS 2024-2026 (N={len(cal_oos)}): Base Net = {cal_oos['net_vip0_26'].mean():.2f} bps, Filtered Net = {oos_filt['net_vip0_26'].mean():.2f} bps (N={len(oos_filt)})")

# 3. The 41 transition trades
trans_41 = df.iloc[75:116]
print('\n--- The 41 Transition Trades (Trades 75 to 115) ---')
print(f"Count: {len(trans_41)}")
print(f"Entry Range: {trans_41['entry_time'].min()} to {trans_41['entry_time'].max()}")
print(f"Base Net (26 bps): {trans_41['net_vip0_26'].mean():.2f} bps")
filt_trans = trans_41[trans_41['action_v33_3a'] == 'KEEP']
print(f"Filtered Net (26 bps): {filt_trans['net_vip0_26'].mean():.2f} bps (N={len(filt_trans)})")
excl_trans = trans_41[trans_41['action_v33_3a'] == 'EXCLUDE']
print(f"Excluded Net (26 bps): {excl_trans['net_vip0_26'].mean():.2f} bps (N={len(excl_trans)})")

