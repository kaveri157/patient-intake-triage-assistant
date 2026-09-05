# Fraud Desk — Transaction Risk Rules (v1)

These are the bank's current risk rules for reviewing a single customer's
transaction history. Each rule has an ID; every finding the system produces
must cite one of these IDs. This file is the ground truth — the rule engine
in `src/rules.py` implements exactly these thresholds, and the narrative
layer is only allowed to reference a rule if it fired here.

---

### R1 — Unusually Large Transfer
A transaction is unusually large for this customer if either:
- it exceeds a flat backstop of ₹50,000, regardless of history, or
- it is 3 or more standard deviations above this customer's own average
  transaction amount (z-score ≥ 3.0).

Rationale: large one-off transfers are one of the most common precursors to
account-takeover fraud, but a flat threshold alone misses customers whose
normal spend is already high — so we combine an absolute and a relative test.

### R2 — New Payee Burst
Three or more payments to a payee the customer has never paid before,
occurring within 24 hours of the first payment to that payee.

Rationale: legitimate new relationships (a new landlord, a new vendor)
usually start with one payment, not a rapid burst. A burst immediately
after first contact is a classic signature of a compromised account being
drained to a mule account.

### R3 — Odd-Hours Activity
Any transaction between 00:00 and 05:00 local time.

Rationale: this window is outside normal customer activity for the large
majority of retail banking customers. It is a weak signal on its own but
meaningful in combination with other rules.

### R4 — Pattern Break
A transaction whose category makes up less than 3% of the customer's
transaction history, where the amount is more than double the customer's
average transaction size.

Rationale: a customer who has never made large travel or online purchases
suddenly doing so is a meaningful deviation from their established
behaviour, independent of the absolute amount involved.

### R5 — Structuring / Below-Threshold Splitting
Four or more transfers to the same payee within a 48-hour window, each
individually below ₹50,000 (so none trip R1 alone), summing to more than
₹150,000.

Rationale: splitting a large transfer into several smaller ones to stay
under a reporting threshold is a well-known evasion pattern ("smurfing").
No single transaction looks unusual — the pattern is only visible in
aggregate.

### R6 — Dormant Payee Reactivation
A payee with no transactions in the most recent 60 days of history,
followed by a transaction to that payee for more than 4x the average of
the customer's transactions with that payee historically.

Rationale: a long-dormant relationship abruptly reactivating at an
elevated amount is inconsistent with the account being used normally by
its owner in the interim.

---

## Escalation policy
- If a customer history matches **no rule**, the report states this
  plainly. The system does not manufacture findings.
- If **one or more rules** fire, every finding must cite the rule ID, the
  specific transaction ID(s) involved, and how it differs from this
  customer's own baseline — never a generic statement.
- The system **never concludes that fraud has occurred**. It ranks
  findings by likely financial exposure and hands the case to a human
  investigator with the evidence assembled.
