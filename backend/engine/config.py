"""Tunable parameters for the forecast/cohort/anomaly engine (spec section 6).

All thresholds here are assumptions -- the spec gives the qualitative rule
(6.1, 6.2) but not exact numbers. The anomaly-pattern thresholds (6.4) are the
only ones actually calibrated against labeled data; see anomaly.py.
"""

# Liquidity forecast (6.1). Safety threshold is relative (fraction of each
# agent's own rolling peak balance so far), not a flat BDT figure -- opening
# balances vary a lot per agent, and a flat number either never triggers for
# well-funded agents or false-positives on modestly-funded ones. assumption:
# no source given for the exact fractions.
EWMA_SPAN_HOURS = 6
CASH_SAFETY_FRACTION = 0.80
PROVIDER_SAFETY_FRACTION = 0.70
TIME_TO_SHORTAGE_CAP_MINUTES = 999_999
STALENESS_PENALTY_START_HOURS = 4.0

# Peer-cohort layer (6.2)
Z_THRESHOLD = 2.0
MIN_COHORT_PEERS = 3
MIN_SHARED_PEERS_FOR_WIDE = 2

# Anomaly pattern (6.4) -- starting point for calibration grid search, not the
# locked values. Section 5's own injection definition is the seed candidate.
ANOMALY_GRID = {
    "min_txns": [3, 4, 5],
    "window_minutes": [10, 15, 20],
    "pct_variation": [0.02, 0.03, 0.05],
    "max_accounts": [2, 3, 4],
}
