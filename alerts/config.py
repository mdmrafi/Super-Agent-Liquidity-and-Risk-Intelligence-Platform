"""Thresholds for Stage 3 alert triggering and severity (spec section 7).

The spec gives severity bands for time_to_shortage (<1hr high, 1-4hr medium)
but not the overall trigger threshold itself. Widened the trigger to 8 hours
so there's a genuine third "low" band (4-8hr) -- otherwise every
liquidity-triggered case would land in either high or medium and the low band
in the spec's own table ("everything else that still crossed a trigger") would
never be reachable for this alert_type.
"""

LIQUIDITY_TRIGGER_MINUTES = 480  # 8 hours -- below this, a liquidity_shortage alert fires
LIQUIDITY_HIGH_MINUTES = 60
LIQUIDITY_MEDIUM_MINUTES = 240
