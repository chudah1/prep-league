# Banking System — Levels 1–4

- Levels completed: **4/4**, after guided review and corrections.
- Minutes used: **not recorded**; the original duration is not remembered.
- Implementation: `bank.py`; examples and regression tests: `test_bank.py`.

## Run the tests

From the repository root:

```bash
python3 -m pytest -q builds/w02-banking/test_bank.py
```

Verified result: **76 passed** — 30 example-row tests and 46 additional regression
cases.

Each of the 30 example rows is a separate parametrized test. Each test starts with
a fresh bank and replays earlier rows because the example tables share state.
Additional tests cover failed operations, exact-balance transfers, integer
precision, zero spenders, payment IDs and cancellation, skipped payments, numeric
payment ordering, merges, and balance history across account lifetimes.

## Top 3 strict-interviewer reviewer points

1. **Test each level before extending it.** Missing tests let basic bugs survive:
   balances were initially calculated without being saved, and account creation
   used a literal dictionary key. Add example tests and failure-path checks as
   each level is built. These implementation bugs were corrected during review.
2. **Define state and timing rules explicitly.** Due payments must run before
   every public operation, including operations that fail. History must record
   payment due times and distinguish current account existence from historical
   existence. Payment ordering, skipped-payment cleanup, numbering, and merge
   history also required corrections during review.
3. **Avoid rebuilding the payment heap on every call.** The implementation still
   scans all pending payments and rebuilds the heap for every public operation:
   `O(P)` work even when nothing is due. A persistent heap would make inspecting
   the next due time `O(1)`, with `O(log P)` insertion/removal. The dictionary can
   track pending status and current ownership, allowing cancelled heap entries
   to be skipped when popped. This remains an efficiency improvement.
