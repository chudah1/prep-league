# DDIA Chapter 5: Replication (1st edition)

**What can be lost on leader failover with asynchronous replication, and how would you limit it?**

With asynchronous replication, a leader may acknowledge a write before followers persist it. If that leader is permanently lost and a lagging follower is promoted, acknowledged writes absent from that follower can disappear. This is data loss, not just a temporary stale read.

Monitor replication lag and choose the most advanced eligible follower to reduce exposure, but asynchronous acknowledgement alone cannot promise zero loss. For stronger durability, acknowledge only after required failover replicas persist the write, and promote a replica containing those acknowledged writes. This adds latency and can block writes when those replicas are unavailable. Persistence and visibility differ: a follower may still need to replay its durable log before serving the new value. [PostgreSQL replication](https://www.postgresql.org/docs/current/warm-standby.html)

**How does a new follower catch up (snapshot plus log position)?**

Take a consistent snapshot with an associated replication-log position P, not merely a timestamp. Restore it on the new follower, then replay the subsequent log in order while the leader keeps accepting writes; a snapshot through entry 500 needs 501 onwards. Retain or archive the required log during copying and replay. If it has been discarded, use a retained archive or restart from a fresh snapshot. Once caught up, continue streaming. [Snapshot and log-position protocol](https://www.postgresql.org/docs/current/protocol-replication.html)

**When would you choose leaderless replication over a single leader?**

I would choose Dynamo-style leaderless replication when write availability during partial failures matters more than a single authoritative write order, and the application can tolerate stale reads and reconcile conflicts. A coordinator contacts the key's replicas and waits for W acknowledgements, not every node. With N=3 and W=2, two reachable normal replicas can accept a write; W=3 cannot succeed with one unavailable and no fallback.

Durability depends on persisted copies and their failure domains, not leaderlessness alone. Accept concurrent versions and ongoing repair work; higher throughput is not automatic. Prefer a single leader when simpler ordering and application invariants dominate. [Cassandra architecture](https://cassandra.apache.org/doc/latest/cassandra/architecture/dynamo.html)

**What does `R + W > N` not guarantee?**

N is a key's normal replica count; R and W are required read and write responses. The inequality ensures intersection only if both response sets use the same fixed replicas. It does not alone guarantee linearizability, resolve concurrent writes, or make enough replicas reachable.

Concrete counterexample: normal replicas {A, B, C}, N=3, R=W=2, initially x=1. A partition prevents a writer reaching B or C, so a sloppy write of x=2 succeeds on A and spare D. Before hinted handoff, a read from B and C returns x=1. Although 2+2>3, sets {A, D} and {B, C} do not overlap: D was outside the normal N. The problem is membership, not geography. [Dynamo paper](https://www.allthingsdistributed.com/files/amazon-dynamo-sosp2007.pdf)

## Three interview sentences about failover

1. I would agree the acceptable data-loss window and recovery time before choosing acknowledgement and failover policies.
2. Before promotion, I would fence the old leader and verify the candidate contains the writes our durability policy promised. [Failover fencing](https://www.postgresql.org/docs/current/warm-standby-failover.html)
3. I would monitor replication lag, test failover and client retries, and rebuild missing replicas rather than assume promotion alone restores resilience.
