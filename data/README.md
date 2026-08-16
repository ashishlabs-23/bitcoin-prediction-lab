# data/

Raw and processed data ingestion. Every source module here must attach an
`available_time` alongside each value — see README.md section 2
("Information-availability firewall") before writing any ingestion code.

Planned sources: OHLCV (ccxt), derivatives (funding/OI), on-chain, macro,
sentiment. Start with one exchange, one canonical BTC/USDT feed.
