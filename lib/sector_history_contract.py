"""Import-light wire constants owned by the Sector cycle history producer.

Both the producer and its native projection use these declarations. No loader,
clock, calculation, publication state, or authorization belongs in this module.
"""

RS_HISTORY_SCHEMA = "sector_cycles.rs_history.v1"
RS_HISTORY_MODE = "reconstructed_price_history"
RS_HISTORY_HORIZONS = (21, 63)
RS_HISTORY_MAX_POINTS = 252
