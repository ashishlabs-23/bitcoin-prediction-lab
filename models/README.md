# models/

Baseline ladder: no-skill -> persistence -> LogReg -> RF -> XGBoost/LightGBM
-> LSTM/GRU -> Transformer -> ensemble (README.md section 5). Every tier
must run on the identical feature set, target, and validation scheme for
the comparison to mean anything.
