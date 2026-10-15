# System design interview template — 45 minutes

> Copy this file for each design. Keep the first pass simple and complete; add
> complexity only when a requirement or deep dive justifies it.

## 1. Requirements — 5 minutes

### Functional

- **Primary actors:**
- **Top 3 user/client capabilities:**
  1.
  2.
  3.
- **Out of scope:**

### Non-functional, with numbers

- **Scale:** ___ users; ___ DAU; ___ peak/average QPS; read:write ratio ___
- **Data:** ___ objects/day × ___ bytes = ___/day; retention ___
- **Latency:** p50 ___; p99 ___ for ___
- **Availability/consistency:** ___% availability; prefer ___ because ___
- **Durability, security, compliance, geography:**

Only calculate quantities that change a design decision. State assumptions and
confirm the prioritized requirements with the interviewer.

## 2. Core entities — 2 minutes

- **Actors:**
- **Resources/state:**
- **Important relationships:**
- **Terms that need a precise definition:**

Keep this to the nouns exchanged by the API or persisted by the system. Refine
fields and relationships while walking the high-level design.

## 3. API — 4 minutes

Default to REST unless another protocol has a specific advantage.

```text
METHOD /v1/resources/{id}
Auth:
Request:
Response:
Errors:
Idempotency/pagination:
```

- Map each core functional requirement to an endpoint or system interface.
- Derive identity from authentication; do not trust a user ID in the body.

## 4. Data flow — 3 minutes

Write the main end-to-end path; skip unnecessary internal detail.

1. Client sends ___
2. Edge/API layer validates ___
3. Service reads/writes ___
4. Async processing or fan-out ___
5. Client receives ___

Call out changed state, ordering boundaries, and sync versus async work.

## 5. High-level design — 10 minutes

```text
[Client] -> [Edge/LB] -> [Service] -> [Primary store]
                            |               |
                            v               v
                         [Queue]        [Cache/index]
                            |
                            v
                         [Worker]
```

- Walk each API/data flow from request to response.
- For every component: responsibility, interface, and scaling unit.
- For every store: relevant schema/keys, access pattern, index, consistency,
  partition key, replication, and retention.
- Label likely bottlenecks or open questions; defer hardening to deep dives.

## 6. Deep dives — 14 minutes

Choose the two or three issues most central to the prompt. For each one:

1. Tie it to a numbered non-functional requirement or observed bottleneck.
2. Quantify the load, limit, or failure boundary.
3. Compare realistic options and their trade-offs.
4. Select one, update the diagram/data model, and state what is sacrificed.
5. Cover correctness under retries, concurrency, partial failure, and recovery.

Candidate topics: hot partitions, caching, sharding, consistency, contention,
queues/backpressure, real-time delivery, large objects, search/indexing,
multi-region operation, security, and abuse prevention.

## 7. Closing checklist — 5 minutes

- [ ] **Failures:** timeouts, retries/idempotency, dependency outage, failover,
      data loss/corruption, degraded mode, recovery objective
- [ ] **Observability:** service-level indicators/objectives, metrics, logs,
      traces, dashboards, alerts, audit trail
- [ ] **Rollout:** migration/backfill, feature flag or canary, compatibility,
      rollback plan
- [ ] **Cost:** largest compute, storage, bandwidth, and operational drivers;
      one cost-control lever
- [ ] **At 10×:** first bottleneck, next partition/scaling boundary, and the
      component or contract that must change
- [ ] Re-check every functional and non-functional requirement against the design.

## 8. Self-score — 2 minutes

| Rubric | Score (1–4) | Evidence / next improvement |
|---|---:|---|
| Understanding |  |  |
| Approach |  |  |
| Code |  |  |
| Testing |  |  |
| Communication |  |  |
| Senior signal |  |  |

**Top 3 gaps**

1.
2.
3.

**Budget check:** 5 + 2 + 4 + 3 + 10 + 14 + 5 + 2 = **45 minutes**.
