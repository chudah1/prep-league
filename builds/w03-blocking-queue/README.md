# Bounded Blocking Queue

Python implementation using exactly one `threading.Lock` shared by two
`threading.Condition` objects, `not_full` and `not_empty`. Items are stored in a
`deque`; `queue.Queue` is not used. Built incrementally with guided review and
tests added along the way.

## Behavior

- Capacity below 1 raises `ValueError`.
- `put` waits while full and `get` waits while empty, rechecking their predicates
  in `while` loops. Timed operations use a single `time.monotonic()` deadline and
  wait only for the remaining time.
- Successful insertion wakes waiting consumers; removal wakes waiting producers.
- `close` is idempotent and notifies all waiters on both conditions.
- Closed queues reject all puts. Gets drain existing items in FIFO order, then
  raise `Closed` once the queue is empty.
- `size` reads the item count while holding the shared lock.

## Run the tests

From the repository root:

```bash
python3 -m pytest -q builds/w03-blocking-queue/test_bbq.py
```

The repeated verification was run with:

```bash
for run in $(seq 1 20); do
  python3 -B -m pytest -q -x -p no:cacheprovider builds/w03-blocking-queue/test_bbq.py || exit 1
done
```

## Verified results

Verified on 2026-10-30:

- **25 tests passed per run, for 20 consecutive complete suite runs.**
- **No hang, lost item, or duplicate occurred in those runs.**
- Each stress test starts **8 producers and 8 consumers**, with each producer
  sending 10,000 unique items and each consumer receiving 10,000 items. A
  `Counter` comparison checks that all **80,000 items** arrive exactly once.
- The 20-run batch delivered **1,600,000 stress-test items** in total.
- Closure tests start 8 blocked getters or 8 blocked putters, confirm that every
  worker has reached its wait, then close the queue. Every worker raises `Closed`
  and terminates within `join(timeout=2)`.
- Additional checks cover FIFO order (including `None` as a valid item), zero and
  positive put/get timeouts, repeated wake-ups without resetting deadlines,
  notifications after insertion/removal, idempotent closure, and draining after
  closure.

Stress workers synchronize their start with a barrier. Worker exceptions are
captured and asserted in the main test thread; cleanup closes the queue and
joins outstanding workers.
