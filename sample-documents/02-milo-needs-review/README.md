# Milo Ledger, 2026 return (needs review)

Single, Los Angeles. One W-2 from Paperclip Observatory LLC, one 1099-INT from Decimal Dreams Bank.

What is wrong on purpose:

- The W-2 PDF shows wages 62,400 and withholding 7,800. `entries.json` has 52,400 and 6,200 (boxes 3 to 6 differ too).
- Avery Ledger is claimed as a dependent and a credit is claimed. Avery was not on the 2025 return.
- The 1099-INT matches the return.

Expected: diagnostics report `PRIOR_DEPENDENTS_CHANGED`. The agent verdict must be `hold` (document mismatch), with a client question about Avery. Wording varies between runs. The verdict does not: a `warn` that misses the W-2 fails. See `expected-results.json`.
