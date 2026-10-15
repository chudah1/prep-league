# Week 1 baseline: rate limiter for a public LLM API

## Proof

- [Baseline recording, part 1](https://drive.google.com/file/d/19-MonsjsYSKol4Bb6hu7iTQAMHAkXlN5/view?usp=drivesdk)
- [Baseline recording, part 2](https://drive.google.com/file/d/1x8sLehORpMoRwT-EzljafieAN0iR46Lm/view?usp=drivesdk)

The two unaided recordings total roughly 12 minutes rather than the requested 45.
Afterward, I continued in an interviewer-guided discussion. This document keeps
the original baseline decisions and the post-review design separate.

## Prompt

Design a rate limiter for a public LLM API with 10,000 API keys, per-key limits
in requests per minute (RPM) and tokens per minute (TPM), and a peak of 50,000
requests per second across three regions.

## Baseline design

### Requirements and numbers

- Authenticate and rate-limit each API key.
- Enforce a configurable RPM limit and TPM limit for every key.
- Return `429 Too Many Requests` when either allowance is exhausted.
- Prefer availability over perfectly strict global enforcement during a regional
  partition, accepting temporary quota overshoot.
- Use an idempotency key so a retried admission request is not charged twice.
- Allow legitimate high-volume keys to receive higher configured limits and
  block abusive keys.

Back-of-envelope calculations:

```text
Requests per region:
50,000 / 3 ~= 16,667 requests/second/region

Limiter operations per region, assuming admission + reconciliation:
16,667 * 2 ~= 33,334 operations/second/region

Raw counter count:
10,000 keys * 2 counters * 3 regions = 60,000 counters

Raw memory at 8 bytes/counter:
60,000 * 8 = 480,000 bytes ~= 480 KB
```

An exact 60-second rolling window would retain up to:

```text
50,000 requests/second * 60 seconds = 3,000,000 timestamps
3,000,000 * 8 bytes = 24 MB raw timestamp data
```

Real Redis memory would be higher because of keys, sorted-set nodes, replication,
and allocator overhead. During the discussion, this led to replacing the exact
rolling-window proposal with token buckets.

### API

The public request contains:

```text
X-API-Key
Idempotency-Key or request ID
Request body
Requested maximum output tokens
```

The gateway authenticates the key, tokenizes the input, determines the request's
region, and calls the limiter.

Allowed requests continue to the LLM service. Rejected requests receive:

```http
HTTP/1.1 429 Too Many Requests
Retry-After: <seconds>
X-RateLimit-Requests-Remaining: <count>
X-RateLimit-Tokens-Remaining: <count>
```

### Data model

Baseline Redis state per API key:

```text
APIKeyConfig
  rpm_limit
  tpm_limit
  tier
  status: active | blocked

RequestBucket
  available_credits
  capacity
  refill_rate
  last_refill_at

TokenBucket
  available_credits
  capacity
  refill_rate
  last_refill_at

IdempotencyRecord
  request_id
  admission_result
  expires_at
```

The baseline suggested a ten-minute idempotency TTL. At 50,000 requests/second,
that could create as many as 30 million records, so the production value must be
chosen from measured retry behaviour and is likely much shorter.

### High-level design

```text
                              API-key configuration
                                      |
                                      v
Client ---> Global/Geo routing ---> Regional API Gateway
                                          |
                                          | authenticate, tokenize input,
                                          | calculate reservation
                                          v
                                 Regional Rate Limiter
                                          |
                                          | atomic Lua check + update
                                          v
                                  Redis shard primary
                                          |
                                          | asynchronous replication
                                          v
                                   Redis followers
                                          |
                         allowed ----------+---------- rejected
                            |                              |
                            v                              v
                      LLM service                    HTTP 429
                            |
                            | actual token usage
                            v
                  token reconciliation/refund
```

The complete admission decision runs atomically on the Redis primary. Followers
must not make authoritative admission decisions because a stale read could allow
two gateways to spend the same final credit.

API keys are consistently hashed to Redis shards. A very hot key can be isolated
on a dedicated shard. The baseline preferred regional availability over strict
global consistency and proposed falling back to another region when the home
region was unavailable.

## Baseline deep dives

### Unknown output length

At admission time, input tokens are known but output tokens are not. The baseline
proposed reserving approximately twice the input size and refunding unused tokens
after generation. The exact accounting for outputs larger than the estimate was
not resolved during the baseline.

A stronger policy is described in the post-review section: reserve known input
tokens plus the admitted maximum output-token count, cap generation at that
maximum, and reconcile against actual usage.

### Slow or unavailable counter store

The baseline policy was:

```text
Free tier:       fail closed
Paid/enterprise: fail open
```

The discussion exposed that unlimited fail-open behaviour could permit an
unbounded cost spike across gateway instances. The baseline did not resolve how
to cap this risk or reconcile missing usage after Redis recovery.

### Multi-region enforcement

The baseline proposed routing each key to an owning shard and failing over to
another region. During a partition, two regions could both believe they own the
key and grant independent quota. The baseline consciously preferred availability
and accepted temporary overshoot, but did not initially quantify or bound it.

### Hot keys

All state for one key must remain on one authoritative shard for atomic updates.
Read replicas do not solve a hot write path. The baseline response was to detect
a legitimate hot key and isolate it on a dedicated shard; abusive keys would be
blocked.

### Testing

The baseline named chaos testing for Redis failures and partitions. It did not
initially cover deterministic boundary tests, concurrent admission at the final
credit, idempotency replay, token-reconciliation correctness, or full load tests.

## Failure modes

| Failure | Baseline behaviour | Risk or unresolved question |
|---|---|---|
| Redis follower is stale | Admission moved to the primary | Primary remains the write bottleneck |
| Redis primary is slow/down | Free fails closed; paid fails open | Paid-tier exposure was unbounded |
| Gateway retries after timeout | Reuse request/idempotency key | Ten-minute TTL may consume substantial memory |
| Region becomes unreachable | Fall back to another region | Split ownership can overspend global quota |
| One API key becomes hot | Move it to a dedicated shard | Migration and fencing were not specified |
| Reconciliation is duplicated | Not resolved in baseline | Duplicate refunds must be prevented |
| Reconciliation event is lost | Not resolved in baseline | Reservation may remain consumed or usage may be lost |

## Provisional self-score

| Rubric | Score (1-4) | Evidence |
|---|---:|---|
| Understanding | 2 | Identified RPM and TPM, but initially lacked a precise token-accounting model. |
| Approach | 2 | Reached gateway, Redis, Lua atomicity, token buckets, sharding, and failover, but global enforcement remained loose. |
| Code | 1 | No executable limiter or Lua transaction was produced in this design exercise. |
| Testing | 1 | Mentioned chaos testing but omitted most correctness and load-testing detail. |
| Communication | 2 | Explained the main components but needed interviewer prompts and arithmetic corrections. |
| Senior signal | 2 | Discussed tiers, idempotency, hot keys, regional trade-offs, and explicit availability choices, but several risks were not bounded. |

## Top three baseline gaps

1. Token reservation and reconciliation were not made precise, especially when
   actual output differs from the estimate or reconciliation is retried.
2. Multi-region failover and paid-tier fail-open behaviour could overspend quota
   without a clear upper bound.
3. The test plan was incomplete: correctness, concurrency, idempotency, load, and
   recovery tests were missing.

## Post-review design

This section is intentionally separate from the baseline.

### Precise reservation and refund

For a request with 5,000 input tokens and `max_output_tokens=2,000`:

```text
Reserve at admission: 5,000 + 2,000 = 7,000 tokens
Actual output:                           800 tokens
Actual total:             5,000 + 800 = 5,800 tokens
Refund:                  7,000 - 5,800 = 1,200 tokens
```

The Redis admission transaction deducts one request credit and the full token
reservation atomically, or deducts neither. Generation is capped at the admitted
maximum, so actual usage cannot legitimately exceed the reservation. A durable,
idempotent reconciliation event refunds unused token credits exactly once.

### Regional quota leases

A lease is an architectural pattern, not a particular database or commercial
product. It is a temporary grant of part of a global allowance to one region.

For a key with 600 RPM and 60,000 TPM, an allocator might issue:

```text
London: 300 request credits and 30,000 token credits
US:     200 request credits and 20,000 token credits
Asia:   100 request credits and 10,000 token credits
```

The invariant is:

```text
sum(active regional leases) <= global per-key allowance
```

Each region spends its credits locally with low latency. When credits run low, it
requests another chunk. During a partition it can spend only its existing lease,
which bounds overshoot. Paid tiers can receive a small pre-issued emergency lease;
free tiers fail closed after exhausting their normal lease.

One possible lease record is:

```text
lease_id
api_key
region
quota_epoch
request_credits
token_credits
expires_at
version/fencing_token
```

### What technology implements a lease?

The lease mechanism consists of two pieces:

1. A small global quota-allocator service that issues, renews, transfers, and
   expires grants.
2. A strongly consistent store that prevents the allocator from issuing the same
   credits twice.

Possible backing technologies include:

- PostgreSQL with transactions or compare-and-swap/version columns at this small
  10,000-key control-plane scale.
- Spanner or CockroachDB when multi-region transactional availability is needed.
- DynamoDB conditional writes in an AWS design.
- FoundationDB for transactional key-value state.
- etcd or Consul for coordination-oriented leases, although they should not sit
  on the 50,000-RPS request path.

Regional Redis remains the fast data plane. The global allocator and consistent
store are a lower-rate control plane: regions request chunks periodically or when
their local balance crosses a threshold, not once per API request.

```text
                   Global quota allocator
                  + consistent lease store
                           /   |   \
                          /    |    \
                         v     v     v
                 London Redis  US Redis  Asia Redis
                      |            |          |
                 local request admission at low latency
```

Lease IDs, quota epochs, and fencing tokens prevent an expired or superseded
owner from continuing to issue valid grants after failover. Unused leases expire
or are explicitly returned and can then be reassigned safely.

### Improved failure policy

| Failure | Improved behaviour |
|---|---|
| Regional Redis primary fails | Promote a replica through quorum; followers do not independently admit traffic. |
| Global allocator is unavailable | Regions spend existing leases but cannot obtain unlimited new quota. |
| Free-tier regional lease is empty | Fail closed with `429`. |
| Paid-tier regional lease is empty | Spend a bounded emergency lease, then fail closed. |
| Usage event is delayed | Retry from durable queue; reservation remains conservatively consumed. |
| Duplicate usage event | Reconciliation idempotency key prevents a second refund. |
| Hot key overloads one shard | Move to a dedicated shard or issue smaller sub-leases to gateway groups. |

### Improved test plan

- Unit tests with a controllable clock for refill and exact boundary behaviour.
- Property tests: buckets never go negative; admission spends both quotas or none;
  total active leases never exceed the global allowance.
- Concurrency tests with many gateways racing for the final credit.
- Duplicate admission and duplicate reconciliation tests.
- Load tests at 50,000 RPS plus admission/reconciliation overhead.
- Hot-key load tests against a single shard.
- Chaos tests for Redis latency, primary loss, replica promotion, allocator loss,
  delayed events, and regional network partitions.

