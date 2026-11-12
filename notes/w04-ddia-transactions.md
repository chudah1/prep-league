# DDIA Chapter 7: Transactions

## Write-skew example

**Example: double-booking a meeting room**

The rule is that room R can have at most one booking for a particular fixed
one-hour slot. Each booking has its own ID, but initially there is no database
constraint preventing two bookings for the same room and slot.

T1 and T2 both use snapshot isolation. The slot starts empty:

| Step | T1 | T2 |
| --- | --- | --- |
| 1 | Begin transaction. | |
| 2 | Check availability; snapshot shows no bookings. | |
| 3 | | Begin transaction. |
| 4 | | Check availability; snapshot also shows no bookings. |
| 5 | Insert booking B1 for R and this slot. | |
| 6 | | Insert booking B2 for R and this slot. |
| 7 | Commit. | |
| 8 | | Commit. |

Both checked the rule, but they checked before seeing the other booking. They
inserted different rows, so there was no direct write-write conflict. Both can
commit and the room ends up double-booked. If they had run one after another,
the second transaction would have seen the first booking and rejected the
request.

This is write skew: the writes affect different rows, but the decisions depend
on a shared premise. Snapshot isolation keeps a stable view; it does not make
every concurrent result equivalent to running transactions one at a time.
[Isolation reference](https://www.postgresql.org/docs/current/transaction-iso.html)

**Fix: materialize the conflict**

Create a `room_slots` row for each room/slot, with a unique `(room_id, slot_id)`
key and `booked=false`. This row exists even when there are no bookings.

Every booking transaction must first claim that same row:

```sql
UPDATE room_slots
SET booked = TRUE
WHERE room_id = 'R' AND slot_id = 'slot_1' AND booked = FALSE
RETURNING room_id;
```

Insert the booking only if the claim returns a row. Both changes must be in the
same transaction. Now competing requests update the same row. Under PostgreSQL
snapshot isolation, a concurrent update can abort the transaction; retry the
whole transaction with a fresh snapshot. If the slot is now booked, reject the
request. Every booking path must follow this protocol.
[Concurrent-update reference](https://www.postgresql.org/docs/current/transaction-iso.html#XACT-REPEATABLE-READ)

Simply locking matching booking rows is not enough when the query finds no
rows. For this exact fixed-slot rule, a `UNIQUE(room_id, slot_id)` constraint on
bookings is an even simpler alternative.
[Locking](https://www.postgresql.org/docs/current/explicit-locking.html#LOCKING-ROWS),
[unique constraints](https://www.postgresql.org/docs/current/ddl-constraints.html#DDL-CONSTRAINTS-UNIQUE-CONSTRAINTS)

**Cost of the shared-row fix**

Hundreds of requests for the same slot now contend on one row. Waiting increases
latency, and aborted work plus immediate retries can amplify load into a retry
storm. Keep transactions short and use bounded retries with backoff and jitter
for transient failures. Finding an already-booked slot is a normal rejection,
not a reason to keep retrying. Different room-slot rows can still be claimed
independently.

## Other chapter notes

**ACID: what each part means**

- **Atomicity:** if I debit A and credit B in one transaction, either both
  happen or neither happens. If the transaction fails before committing, A
  should get its money back and B should remain as it was.
- **Consistency:** the application has to preserve its business rules. The
  database can enforce rules I declare, like unique constraints, but it does
  not automatically know that debiting 100 and crediting only 90 is wrong.
- **Isolation:** controls what concurrent transactions can see and how they
  affect each other. The guarantees depend on the isolation level.
- **Durability:** once the database acknowledges a durable commit, the changes
  should survive a database crash. On recovery, I should see A debited and B
  credited.

Atomicity for one key does not automatically cover two keys. Two individually
atomic balance updates can still leave half a transfer if the process crashes
between them. The whole transfer needs one atomic transaction.
[Transactions reference](https://www.postgresql.org/docs/current/tutorial-transactions.html)

**Read committed: committed does not mean unchanged**

I cannot read another transaction's uncommitted changes: that would be a dirty
read. If the committed balance is 100 and T1 has an uncommitted change to 50,
my normal read still sees 100.

However, if T1 commits before my next read, that next read can return 50. Seeing
different values in two reads of the same row is a non-repeatable read. In
PostgreSQL read committed, each statement gets a new snapshot.

Databases commonly prevent dirty writes with write locks too. If T1 has updated
a row without finishing its transaction, T2 cannot just overwrite that
uncommitted update; it waits for T1 to finish.
[Read committed](https://www.postgresql.org/docs/current/transaction-iso.html#XACT-READ-COMMITTED)

**Read skew: mixing two different points in time**

Start with A = 500 and B = 500. My transaction reads A and gets 500. Another
transaction then transfers 100 from A to B and commits, leaving A = 400 and
B = 600. If my next read sees the new B = 600, I calculate a total of 1,100.

The transfer did not create money. I combined the old A with the new B, so I
counted the transferred 100 twice. Both reads saw committed data, but their
combination was inconsistent. Read committed allows this.

**Snapshot isolation and MVCC**

Snapshot isolation gives me a stable view for the transaction. If my snapshot
was established before that transfer, I see A = 500 and B = 500, even if I only
read B after the transfer commits. It covers rows I have not read yet, not
just values I have already looked up. I can still see my own transaction's
writes.

It does not mean the database aborts every transaction that overlaps mine.
Their changes can commit; their new versions simply are not visible in my
older snapshot. Snapshot isolation can still allow write skew, as in the
booking example above.
[Snapshot isolation in PostgreSQL](https://www.postgresql.org/docs/current/transaction-iso.html#XACT-REPEATABLE-READ)

MVCC makes this possible by keeping versions of rows. An update creates a new
version, and transaction metadata determines which version a reader can see.
The database does not copy the whole database for every transaction.

Old versions cannot be reclaimed while a transaction might still need them.
A long-lived snapshot can therefore delay cleanup and cause old versions to
accumulate, increasing storage use and work during reads.
[Row versions](https://www.postgresql.org/docs/current/ddl-system-columns.html),
[cleanup](https://www.postgresql.org/docs/current/routine-vacuuming.html#VACUUM-FOR-SPACE-RECOVERY)

**Lost updates: two increments become one**

T1 and T2 both read a counter at 10. Each calculates 11 in application code,
then writes 11. The final value is 11 instead of 12: the later write clobbered
the earlier increment. Preventing dirty writes alone does not prevent this;
the writes can happen one after another using stale calculations.

For a simple increment, let the database do the operation:

```sql
UPDATE counters SET value = value + 1 WHERE id = 1;
```

If I need to calculate in the application, I can lock the row with
`SELECT ... FOR UPDATE` before reading and calculating. The read, calculation,
and write must belong to the same transaction.
[Row locking](https://www.postgresql.org/docs/current/explicit-locking.html#LOCKING-ROWS)

**Compare-and-set: only update the version I actually read**

Another approach is a version column. Both transactions read value 10 and
version 3, then attempt:

```sql
UPDATE counters
SET value = 11, version = 4
WHERE id = 1 AND version = 3;
```

The first succeeds and affects one row. Once it commits, the second no longer
matches version 3 and affects zero rows under read committed. At stronger
isolation levels, it may instead receive a transaction error that needs a
retry.

The loser must read the current value and version again, recalculate, and try
the conditional update again. If it now reads 11 and version 4, it should
attempt 12 and version 5. Replaying the same stale calculation is not enough.

**A lost commit response and idempotency**

If I send `COMMIT` and lose the connection before receiving the response, I do
not know whether it committed. The database might have committed successfully
and only the reply was lost. Retrying the transfer as a new operation could
charge the customer twice.

Use the same idempotency key when retrying that operation. The server records
the key and result so it can return the previous result instead of performing
the transfer again. The debit, credit, and idempotency record must be saved in
the same transaction; otherwise there is another gap where only some of them
could commit. A unique constraint on the key prevents concurrent requests
from processing the same operation twice.
[Idempotency and retries](https://stripe.com/blog/idempotency)

**Phantoms: the matching set changes**

I query bookings for room R and get two rows. Another transaction inserts a
matching booking and commits. Under read committed, my repeated query can now
return three rows. No existing row had to change: a new row appeared in the
set matching my condition. That is a phantom. With the same snapshot under
snapshot isolation, I would still see the original two.

Locking only existing rows does not protect an empty result. A lock-based
serializable implementation can protect the predicate or an index range,
including the gaps where matching rows could be inserted. A matching insert
then conflicts with that protection. SQL Server uses key-range locks for
this purpose.
[Key-range locks](https://learn.microsoft.com/en-us/sql/relational-databases/sql-server-transaction-locking-and-row-versioning-guide#key-range-locks)

**Serializability: equivalent to some one-at-a-time order**

Transactions may physically run concurrently, but their committed results
must be equivalent to some order in which they ran one at a time. It does not
mean there can never be an application bug or a duplicate operation: two
duplicate transfers could execute perfectly serially and still charge twice.
I still need correct transaction boundaries and idempotency.

**Actual serial execution**

One approach is to actually execute transactions one at a time. The problem
is that a slow transaction holds up the queue. If it waits five seconds for
the client, other transactions on that execution worker wait too: head-of-line
blocking.

This works better with short transactions and server-side procedures that
avoid pauses for client input. Independent partitions can execute in parallel;
transactions spanning partitions need coordination.
[Serial execution per partition](https://docs.voltdb.com/UsingVoltDB/IntroHowVoltDBWorks.php)

**Two-phase locking: acquire, then release**

A shared lock lets readers share a row. An exclusive lock conflicts with both
readers and writers. If a reader holds a shared lock, a writer requesting an
exclusive lock has to wait: requesting the lock does not mean it has been
granted.

In the growing phase, I acquire locks without releasing them. Once I release
a lock, I enter the shrinking phase and cannot acquire new ones. So locking
A and B, releasing A, then requesting C breaks the rule. I would need to
acquire C before starting to release locks. Many implementations hold locks
until the transaction ends.

Deadlock example: T1 holds A and waits for B; T2 holds B and waits for A.
Neither can proceed. The database can abort one transaction, releasing its
locks so the other can finish. The victim can retry the whole transaction.
Acquiring locks in the same order helps avoid this kind of deadlock.

The costs are waiting, lock contention, and work lost when a deadlock victim
is aborted.
[Two-phase locking](https://cs186berkeley.net/fa22/resources/static/notes/n12-Xact2.pdf)

**Serializable snapshot isolation: detect unsafe dependencies**

SSI starts with snapshot isolation and tracks dependencies between reads and
writes. It is not just checking whether two transactions write the same row.
In the booking example, each transaction's decision depends on not seeing
the other's booking. Both succeeding would not fit any serial order.

SSI detects dangerous dependency patterns and aborts a transaction when
needed to preserve serializability. I then retry the whole transaction with
a fresh snapshot. PostgreSQL's predicate-read tracking does not block
matching writes, unlike blocking range locks. Ordinary conflicting writes
can still wait on locks.

The trade-off is tracking overhead and potentially wasted work: a transaction
can do a lot of work only to abort near the end. Lots of aborts and immediate
retries can reduce throughput and amplify load, so transactions should stay
short and transient retries should use bounded backoff and jitter.
[Serializable isolation](https://www.postgresql.org/docs/current/transaction-iso.html#XACT-SERIALIZABLE)
