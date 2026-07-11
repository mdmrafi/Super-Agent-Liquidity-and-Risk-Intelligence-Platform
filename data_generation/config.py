"""World parameters for the synthetic data generator (spec section 4.1 / 5).

Values marked "assumption" are not sourced from the Bangladesh Bank MFS
statistics cited in the spec and should be called out in the data/simulation
note (spec section 12).
"""
import numpy as np

RANDOM_SEED = 42

AREAS = ["Zindabazar", "Ambarkhana", "Bandarbazar", "Shibganj", "Chowhatta"]
PROVIDERS = ["bKash", "Nagad", "Rocket"]

# assumption: provider market-share split, not sourced
PROVIDER_WEIGHTS = {"bKash": 0.50, "Nagad": 0.33, "Rocket": 0.17}

NUM_AGENTS = 20
AGENTS = [f"agent_{i:02d}" for i in range(1, NUM_AGENTS + 1)]
# 4 agents per area, round-robin
AGENT_AREA = {AGENTS[i]: AREAS[i % len(AREAS)] for i in range(NUM_AGENTS)}

START_DATE = "2026-01-01"
NUM_DAYS = 30
CALIBRATION_DAYS = 21
HOLDOUT_DAYS = 9

# Mix of day types across both splits (spec 4.1): calibration days 1-21,
# holdout days 22-30. Same ~70/20/10 (calibration) and ~55/22/22 (holdout)
# proportions as the original 10+4 day split, scaled up. Assigned
# deterministically so the mix is documented, not left to chance.
DAY_TYPES = (
    ["normal"] * 15 + ["salary_day"] * 4 + ["eid"] * 2       # calibration
    + ["normal"] * 5 + ["salary_day"] * 2 + ["eid"] * 2      # holdout
)
assert len(DAY_TYPES) == NUM_DAYS

# Calibrated from Bangladesh Bank MFS stats (Oct 2023): ~18.5M daily
# transactions / ~1.68M agents =~ 11/agent/day. Spec range is 10-15/agent/day.
BASE_TXNS_PER_AGENT_PER_DAY = 13
# assumption: no source given for the exact multiplier within the 3-5x range
DAY_TYPE_MULTIPLIER_RANGE = (3.0, 5.0)

# Hourly demand-shape weights (assumption): lunch peak ~12-13, evening peak ~18-19.
_HOUR_WEIGHTS_RAW = np.array([
    0.010, 0.005, 0.005, 0.005, 0.005, 0.010,  # 0-5   night
    0.020, 0.030, 0.040, 0.050, 0.050, 0.060,  # 6-11  morning ramp
    0.090, 0.080, 0.050, 0.040, 0.050, 0.070,  # 12-17 lunch peak
    0.090, 0.080, 0.060, 0.040, 0.020, 0.010,  # 18-23 evening peak
])
HOUR_WEIGHTS = _HOUR_WEIGHTS_RAW / _HOUR_WEIGHTS_RAW.sum()

# cash_in:cash_out ~= 1.12:1 per Bangladesh Bank MFS stats
CASH_IN_PROB = 1.12 / (1.12 + 1)

# assumption: lognormal amount distribution, median calibrated to spec's 2,100 BDT;
# sigma is not sourced.
AMOUNT_MEDIAN_BDT = 2100
AMOUNT_SIGMA = 0.7

# assumption: no source given in spec for transaction failure rate
FAILURE_RATE = 0.03

# assumption: opening balances, sized generously so the unconstrained baseline
# random walk stays positive over 14 days for non-scenario agents; the
# injected liquidity scenarios deliberately threaten this buffer for specific
# agents. Not sourced from the spec.
OPENING_CASH_RANGE = (200_000, 400_000)
OPENING_PROVIDER_BALANCE_RANGE = (100_000, 250_000)

# assumption: size of each agent's rotating synthetic customer pool
CUSTOMER_POOL_SIZE = 400
