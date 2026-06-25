"""Reader-facing copy for *why a signal carries no score or no forecast*.

A small reusable set keyed by situation, assigned to indicators in config.py and
rendered near the badge / prediction slot (lens.js, predict.js, staticread.py).
This is reader prose — review it here. See the matrix in
docs/superpowers/specs/2026-06-24-score-explain-order-signals-design.md.
"""

# --- Why it isn't scored (no_severity_reason) ---
NEUTRAL_SCOREBOARD = ("Part of a neutral scoreboard — it shows which way the price is "
                      "moving, not whether that's good or bad.")
NEUTRAL_CRYPTO = ("A structural read on how money is rotating within crypto — not a "
                  "good-or-bad verdict.")
MARKET_PRICE = ("A market price has no inherent good-or-bad level — higher or lower "
                "isn't itself better or worse.")
PHYSICAL = ("A physical supply-and-demand reading, not a household cost — this lens's "
            "verdict comes from the price indicators.")
FED_PLUMBING = ("A descriptive level of the monetary plumbing — this lens's verdict is "
                "carried by M2 money-supply growth.")
RATE_EXPECTATIONS = ("Whether markets expect cuts or hikes isn't itself good or bad — "
                     "it's the bond market's forecast, shown for context.")
TRADE_DEFICIT = ("The U.S. has run a trade deficit every year since 1976 — the level "
                 "isn't good or bad on its own; what matters is the trend shown here.")
INTEREST_DOLLARS = ("The dollar interest bill climbs with the economy; the scored read is "
                    "interest as a share of revenue, alongside debt-to-GDP and the deficit.")
DEMOGRAPHIC_LEVEL = ("This level drifts with demographics — the job-market verdict is "
                     "carried by unemployment, payrolls, and job openings.")
LEVEL_CONTEXT = ("A descriptive level shown for context — neither a high nor a low "
                 "reading is simply good or bad.")
RAW_INVENTORY = ("Months' supply, which adjusts for the sales pace, carries this lens's "
                 "supply verdict; this is the raw count for context.")
CONTEXT_GROWTH = "Shown for context alongside this lens's lead growth reading."
CONTEXT_DEMAND = ("Shown for context — a noisy global-demand pulse the lens's scored "
                  "indicators read more cleanly.")
SMALL_BUSINESS_NOISE = ("Shown for context — proprietors' income (which includes farm "
                        "income) is too volatile to score cleanly.")

# --- Why it isn't forecast (no_prediction_reason) ---
ANNUAL = ("This series updates only once or twice a year — too few data points to build "
          "an honest forecast range. (The IMF's own projection is noted in the read above.)")
COMPUTED_SHARE = ("This is computed from other series at refresh time, so there's no "
                  "single line to forecast directly.")
CRYPTO_HISTORY = ("We've only been recording this since the site launched — not yet enough "
                  "history to forecast honestly.")
