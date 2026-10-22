# DDIA Chapter 3: LSM-trees vs B-trees

## LSM-tree write and read paths

On a write, an LSM-tree first appends the change to a write-ahead log (WAL) for durability, then inserts it into a sorted in-memory memtable. When the memtable fills, it becomes immutable and is flushed to disk as a sorted, immutable SSTable. Background compaction later merges SSTables and discards overwritten values and deletion tombstones when safe. On a read, the engine checks the memtable first, then relevant SSTables from newer data toward older data. A Bloom filter can rule out an SSTable, and a sparse index identifies the disk block that may contain the key.

## B-tree write and read paths

A B-tree divides the sorted keyspace into fixed-size pages. A read follows separator keys and child-page pointers from the root to one leaf page. A write first records the change in the WAL, follows the same root-to-leaf path, and overwrites the target page in place. If that page is full, it splits into two pages and the parent gains a new separator and pointer; a full parent can make the split cascade toward the root.

## Write amplification

A normal B-tree update produces roughly two persistent writes: one WAL write and one data-page write. Its byte amplification can still be high because changing a small value may rewrite an entire 4 KiB or larger page; a split additionally writes two child pages and updates the parent. An LSM value is written to the WAL, written again during its initial SSTable flush, and then rewritten as compaction moves it through levels. For example, a value surviving four level transitions may be written roughly six times (WAL, flush, and four transitions), although the actual amplification depends on the compaction strategy and overlapping data. LSM writes are mostly sequential and batched, whereas B-tree page writes may be random.

## Compaction and latency spikes

Compaction reads several SSTables and writes a merged replacement, consuming disk bandwidth, CPU, memory and cache capacity that foreground requests also need. Reads normally continue using the immutable old files, but their I/O may queue behind compaction. If compaction falls behind, SSTables accumulate, reads consult more files, and writes may eventually be throttled or stalled. One mitigation is to rate-limit compaction and reserve I/O headroom for foreground traffic; smaller incremental compactions also reduce large bursts.

## What Bloom filters save

A Bloom filter answers either "definitely absent" or "possibly present" for a particular SSTable. A definite absence lets the engine skip that file, avoiding its sparse-index lookup and disk read. A false positive can cause an unnecessary lookup, but a Bloom filter does not produce false negatives. It is especially useful for unsuccessful reads that might otherwise check many SSTables.

## Choice for a write-heavy key-value store

I would start with an LSM-tree because its foreground write path is an append to the WAL plus an in-memory update, and it converts many writes into sequential SSTable flushes and compactions. This generally supports better sustained write throughput than performing random in-place page updates. I am accepting read amplification—the need to consult multiple structures—and possible tail-latency spikes from compaction. Bloom filters, indexes and controlled background compaction mitigate those costs. The final choice would still depend on measured read/write ratios, latency targets and storage hardware.

## Interview sentence

> I would choose an LSM-tree for this write-heavy key-value store because it batches updates into sequential disk writes for high write throughput, while accepting and mitigating its read amplification and compaction-driven tail latency.
