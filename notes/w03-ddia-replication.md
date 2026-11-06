# DDIA Chapter 5: Replication (1st edition)

**What can be lost on leader failover with asynchronous replication, and how would you limit it?**

With async replication, we can reply to the client before the follower gets the write. So if x was 1 and the leader updated it to 2, the follower might still have 1. If the leader dies permanently and that follower takes over, clients read 1, even though the client was already told the write worked.

For this leader-and-follower setup, I would use synchronous replication if we cannot accept losing that write. We wait for the follower to save the write to disk before replying. The cost is that writes take longer, and if the required follower is down we may have to wait or reject writes. [Reference](https://www.postgresql.org/docs/current/warm-standby.html)

**How does a new follower catch up (snapshot plus log position)?**

We can capture a consistent snapshot of the data and copy it to the follower. While that copy is happening, the leader can still receive writes, so we also need the changes since the snapshot.

The important detail is keeping the snapshot's log position, not just its time. If it includes everything through entry 500, we need 501 onwards. We keep those log entries during the copy and apply them in order until the follower catches up, then keep receiving new changes. [Reference](https://www.postgresql.org/docs/current/protocol-replication.html)

**When would you choose leaderless replication over a single leader?**

I would choose leaderless when I want to keep accepting writes even if some nodes are unavailable, rather than depend on one leader.

We do not need every node to acknowledge. With three replicas A, B and C, N=3. If W=2 and C is down, A and B can still acknowledge the write. If W=3, without a spare taking C's place, we cannot get enough replies.

The trade-off is that nodes can have different versions, so reads might be stale and we need to handle conflicting writes. Leaderless does not automatically mean higher throughput or better durability. [Reference](https://cassandra.apache.org/doc/latest/cassandra/architecture/dynamo.html)

**What does `R + W > N` not guarantee?**

It does not mean a read will always get the latest value. The overlap depends on reads and writes using the same normal set of replicas.

For example, N=3 with normal replicas A, B and C, and R=W=2. A sloppy write of x=2 succeeds on A and spare D because B and C cannot be reached. Another client reads B and C, which still have x=1.

The write set {A, D} and read set {B, C} do not overlap, even though 2+2>3. That is the issue: different nodes accepted the write from the ones serving the read, not necessarily different datacenters. [Reference](https://www.allthingsdistributed.com/files/amazon-dynamo-sosp2007.pdf)

## Three interview sentences about failover

1. With async replication, I can lose a write that the leader already told the client was successful.
2. If I cannot accept that, I would wait for the follower to save the write to disk before replying.
3. The trade-off is that writes take longer and may have to wait or fail if the required follower is unavailable.
