# Worker pool

A fixed set of non-daemon threads takes jobs from a bounded blocking queue.
Each future uses an event to signal a value, an exception, or cancellation.
`map()` preserves input order, including `None` results.

Normal shutdown closes the queue and lets workers drain it. With
`cancel_pending=True`, closing and removing queued jobs happen under the
queue's lock; their futures are cancelled while jobs already taken by workers
finish. `wait=True` joins every worker.

Run from the repository root:

```sh
PYTHONDONTWRITEBYTECODE=1 python3 -m pytest builds/w03-worker-pool/test_pool.py -q -p no:cacheprovider
```

Validation: **5 tests passed, repeated 20 consecutive times**, with no hang,
lost task, or duplicate execution observed. Tests cover 1,000 task results,
exception propagation and worker reuse, results collected in input order,
both shutdown modes, cancellation, waking a blocked submitter, repeated
shutdown, and worker cleanup.
