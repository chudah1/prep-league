"""Construction, FIFO, timeout, blocking, and shutdown checks."""

from collections import Counter
import threading
import time
from types import SimpleNamespace

import pytest

import bbq
from bbq import BoundedBlockingQueue, Closed


@pytest.mark.parametrize("capacity", [0, -1])
def test_capacity_must_be_positive(capacity):
    with pytest.raises(ValueError):
        BoundedBlockingQueue(capacity)


@pytest.mark.parametrize("capacity", [1, 2])
def test_new_queue_is_empty(capacity):
    queue = BoundedBlockingQueue(capacity)
    assert queue.size() == 0


def test_put_into_available_space_succeeds():
    queue = BoundedBlockingQueue(2)
    assert queue.put("first", timeout=0) is None
    assert queue.size() == 1
    assert queue.put("second", timeout=0) is None
    assert queue.size() == 2


def test_put_into_full_queue_with_zero_timeout_fails_immediately(monkeypatch):
    queue = BoundedBlockingQueue(1)
    queue.put("first", timeout=0)

    def unexpected_wait(timeout=None):
        pytest.fail("A full queue with timeout=0 must raise without waiting")

    monkeypatch.setattr(queue.not_full, "wait", unexpected_wait)
    with pytest.raises(TimeoutError):
        queue.put("second", timeout=0)
    assert queue.size() == 1


def test_put_preserves_original_deadline_after_repeated_wakeups(monkeypatch):
    """Wake-ups without free space must not restart the timeout budget."""
    queue = BoundedBlockingQueue(1)
    queue.put("first", timeout=0)
    clock = [100.0]
    waits = []

    # Replace only this module's clock, leaving the real time module intact.
    monkeypatch.setattr(
        bbq, "time", SimpleNamespace(monotonic=lambda: clock[0])
    )

    def wake_without_space(timeout=None):
        assert timeout is not None, "A timed put must use a bounded wait"
        assert 0 < timeout <= 2, "Wait exceeds the original timeout budget"
        waits.append(timeout)
        assert len(waits) <= 2, "put kept waiting beyond its original deadline"
        clock[0] += 1
        return True

    monkeypatch.setattr(queue.not_full, "wait", wake_without_space)

    with pytest.raises(TimeoutError):
        queue.put("second", timeout=2)
    assert waits == [2.0, 1.0]
    assert queue.size() == 1


def test_close_is_idempotent_and_preserves_queued_items():
    queue = BoundedBlockingQueue(2)
    queue.put("first", timeout=0)
    assert queue.close() is None
    assert queue.close() is None
    assert queue.size() == 1


@pytest.mark.parametrize(
    "capacity,items",
    [(1, ()), (2, ("first",)), (1, ("first",))],
    ids=["empty", "partly-full", "full"],
)
def test_put_after_close_raises_closed(capacity, items):
    queue = BoundedBlockingQueue(capacity)
    for item in items:
        queue.put(item, timeout=0)
    queue.close()
    with pytest.raises(Closed):
        queue.put("new", timeout=0)
    assert queue.size() == len(items)


def test_get_returns_items_in_fifo_order():
    queue = BoundedBlockingQueue(3)
    for item in ("first", "second", None):
        queue.put(item, timeout=0)
    assert queue.get(timeout=0) == "first"
    assert queue.size() == 2
    assert queue.get(timeout=0) == "second"
    assert queue.size() == 1
    assert queue.get(timeout=0) is None
    assert queue.size() == 0


def test_get_from_empty_queue_with_zero_timeout_fails_immediately(monkeypatch):
    queue = BoundedBlockingQueue(1)

    def unexpected_wait(timeout=None):
        pytest.fail("An empty queue with timeout=0 must raise without waiting")

    monkeypatch.setattr(queue.not_empty, "wait", unexpected_wait)
    with pytest.raises(TimeoutError):
        queue.get(timeout=0)


def test_get_preserves_original_deadline_after_repeated_wakeups(monkeypatch):
    queue = BoundedBlockingQueue(1)
    clock = [100.0]
    waits = []
    monkeypatch.setattr(
        bbq, "time", SimpleNamespace(monotonic=lambda: clock[0])
    )

    def wake_without_items(timeout=None):
        assert timeout is not None, "A timed get must use a bounded wait"
        assert 0 < timeout <= 2, "Wait exceeds the original timeout budget"
        waits.append(timeout)
        assert len(waits) <= 2, "get kept waiting beyond its original deadline"
        clock[0] += 1
        return True

    monkeypatch.setattr(queue.not_empty, "wait", wake_without_items)
    with pytest.raises(TimeoutError):
        queue.get(timeout=2)
    assert waits == [2.0, 1.0]


@pytest.mark.parametrize("timeout", [None, 0, 2], ids=["unbounded", "zero", "finite"])
def test_get_from_closed_empty_queue_raises_without_waiting(monkeypatch, timeout):
    queue = BoundedBlockingQueue(1)
    queue.close()

    def unexpected_wait(timeout=None):
        pytest.fail("A closed, empty queue must raise Closed without waiting")

    monkeypatch.setattr(queue.not_empty, "wait", unexpected_wait)
    with pytest.raises(Closed):
        queue.get(timeout=timeout)


def test_get_drains_closed_queue_one_item_at_a_time():
    queue = BoundedBlockingQueue(2)
    queue.put("first", timeout=0)
    queue.put("second", timeout=0)
    queue.close()
    assert queue.get(timeout=0) == "first"
    assert queue.size() == 1
    assert queue.get(timeout=0) == "second"
    assert queue.size() == 0
    with pytest.raises(Closed):
        queue.get(timeout=0)


def test_get_wakes_a_producer_waiting_for_space(monkeypatch):
    queue = BoundedBlockingQueue(1)
    queue.put("first", timeout=0)
    waiting = threading.Event()
    outcomes = []
    original_wait = queue.not_full.wait

    def mark_waiting(timeout=None):
        waiting.set()
        return original_wait(timeout)

    monkeypatch.setattr(queue.not_full, "wait", mark_waiting)

    def produce():
        try:
            queue.put("second")
        except Exception as exc:
            outcomes.append(exc)
        else:
            outcomes.append("put-completed")

    producer = threading.Thread(target=produce, daemon=True)
    producer.start()
    try:
        assert waiting.wait(timeout=2), "Producer did not reach its wait"
        assert queue.get(timeout=0) == "first"
        producer.join(timeout=2)
        assert not producer.is_alive(), "Removing an item did not wake the producer"
        assert outcomes == ["put-completed"]
        assert queue.get(timeout=0) == "second"
    finally:
        queue.close()
        producer.join(timeout=2)


@pytest.mark.parametrize("operation", ["put", "get"])
def test_positive_timeouts_expire_without_changing_queue(operation):
    queue = BoundedBlockingQueue(1)
    if operation == "put":
        queue.put("kept", timeout=0)
    timeout = 0.02
    started = time.monotonic()
    with pytest.raises(TimeoutError):
        if operation == "put":
            queue.put("blocked", timeout=timeout)
        else:
            queue.get(timeout=timeout)
    assert time.monotonic() - started >= timeout * 0.8
    if operation == "put":
        assert queue.get(timeout=0) == "kept"
    assert queue.size() == 0


def test_put_wakes_a_consumer_waiting_for_an_item(monkeypatch):
    queue = BoundedBlockingQueue(1)
    waiting = threading.Event()
    outcomes = []
    original_wait = queue.not_empty.wait

    def mark_waiting(timeout=None):
        waiting.set()
        return original_wait(timeout)

    monkeypatch.setattr(queue.not_empty, "wait", mark_waiting)

    def consume():
        try:
            outcomes.append(queue.get())
        except Exception as exc:
            outcomes.append(exc)

    consumer = threading.Thread(target=consume, daemon=True)
    consumer.start()
    try:
        assert waiting.wait(timeout=2), "Consumer did not reach its wait"
        queue.put("first", timeout=0)
        consumer.join(timeout=2)
        assert not consumer.is_alive(), "Adding an item did not wake the consumer"
        assert outcomes == ["first"]
    finally:
        queue.close()
        consumer.join(timeout=2)


@pytest.mark.parametrize("operation", ["put", "get"], ids=["putters", "getters"])
def test_close_wakes_every_blocked_thread(monkeypatch, operation):
    queue = BoundedBlockingQueue(1)
    worker_count = 8
    if operation == "put":
        queue.put("kept", timeout=0)
        condition = queue.not_full
    else:
        condition = queue.not_empty

    all_waiting = threading.Event()
    waiting_threads = set()
    outcomes = [None] * worker_count
    original_wait = condition.wait

    def mark_waiting(timeout=None):
        # Condition.wait is entered with the queue lock held, so this set is
        # protected by that same lock. Count distinct threads, not wake-ups.
        waiting_threads.add(threading.get_ident())
        if len(waiting_threads) == worker_count:
            all_waiting.set()
        return original_wait(timeout)

    monkeypatch.setattr(condition, "wait", mark_waiting)

    def run_worker(index):
        try:
            if operation == "put":
                queue.put(index)
            else:
                queue.get()
        except BaseException as exc:
            outcomes[index] = exc
        else:
            outcomes[index] = "unexpected-success"

    threads = [
        threading.Thread(
            target=run_worker,
            args=(index,),
            name=f"blocked-{operation}-{index}",
            daemon=True,
        )
        for index in range(worker_count)
    ]
    for thread in threads:
        thread.start()
    try:
        assert all_waiting.wait(timeout=2), "Not every worker reached its wait"
        queue.close()
        for thread in threads:
            thread.join(timeout=2)
            assert not thread.is_alive(), f"close did not wake {thread.name}"
        assert all(isinstance(outcome, Closed) for outcome in outcomes), outcomes
        if operation == "put":
            assert queue.get(timeout=0) == "kept"
        assert queue.size() == 0
    finally:
        queue.close()
        for thread in threads:
            if thread.is_alive():
                thread.join(timeout=2)


def test_eight_producers_and_consumers_deliver_every_item_exactly_once():
    producer_count = 8
    consumer_count = 8
    items_per_worker = 10_000
    queue = BoundedBlockingQueue(64)
    start = threading.Barrier(producer_count + consumer_count)
    producer_done = [threading.Event() for _ in range(producer_count)]
    received = [[] for _ in range(consumer_count)]
    errors = [None] * (producer_count + consumer_count)

    def produce(index):
        try:
            start.wait(timeout=2)
            for item_index in range(items_per_worker):
                queue.put((index, item_index))
        except BaseException as exc:
            errors[consumer_count + index] = exc
        finally:
            producer_done[index].set()

    def consume(index):
        try:
            start.wait(timeout=2)
            for _ in range(items_per_worker):
                received[index].append(queue.get())
        except BaseException as exc:
            errors[index] = exc

    threads = [
        threading.Thread(
            target=consume, args=(index,), name=f"consumer-{index}", daemon=True
        )
        for index in range(consumer_count)
    ] + [
        threading.Thread(
            target=produce, args=(index,), name=f"producer-{index}", daemon=True
        )
        for index in range(producer_count)
    ]
    for thread in threads:
        thread.start()
    try:
        deadline = time.monotonic() + 30
        for index, done in enumerate(producer_done):
            assert done.wait(timeout=max(0, deadline - time.monotonic())), (
                f"Producer {index} did not finish within the stress-test budget"
            )
        queue.close()
        for thread in threads:
            thread.join(timeout=2)
            assert not thread.is_alive(), f"{thread.name} failed to stop"
        assert not any(errors), errors
        assert all(len(items) == items_per_worker for items in received)
        actual = Counter(item for items in received for item in items)
        expected = Counter(
            (producer_index, item_index)
            for producer_index in range(producer_count)
            for item_index in range(items_per_worker)
        )
        assert actual == expected
        assert queue.size() == 0
    finally:
        queue.close()
        for thread in threads:
            if thread.is_alive():
                thread.join(timeout=2)
