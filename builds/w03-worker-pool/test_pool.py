"""Tests for the worker pool exercise."""

import threading

import pytest

from bbq import BoundedBlockingQueue, Closed
from pool import Cancelled, WorkerPool


def test_task_exception_reaches_future_and_worker_continues():
    pool = WorkerPool(1)
    try:
        failed = pool.submit(lambda: 1 / 0)
        with pytest.raises(ZeroDivisionError):
            failed.result(timeout=2)
        assert failed.done()
        assert pool.submit(pow, 2, 10).result(timeout=2) == 1024
    finally:
        pool.queue.close()
        for worker in pool._workers:
            worker.join(timeout=2)
    assert all(not worker.is_alive() for worker in pool._workers)


def test_map_preserves_input_order_and_none_results():
    pool = WorkerPool(2)
    second_finished = threading.Event()
    finished = []

    def job(value):
        if value == 0:
            if not second_finished.wait(2):
                raise TimeoutError('Second job did not finish')
            finished.append(0)
            return None
        finished.append(1)
        second_finished.set()
        return 10

    try:
        assert pool.map(job, [0, 1]) == [None, 10]
        assert finished == [1, 0]
        assert pool.map(job, []) == []
        with pytest.raises(ZeroDivisionError):
            pool.map(lambda value: 1 / value, [0])
    finally:
        pool.queue.close()
        for worker in pool._workers:
            worker.join(timeout=2)
    assert all(not worker.is_alive() for worker in pool._workers)


def test_close_and_drain_removes_items_and_is_idempotent():
    queue = BoundedBlockingQueue(2)
    queue.put(1)
    queue.put(2)
    assert queue.close_and_drain() == [1, 2]
    assert queue.close_and_drain() == []
    assert queue.size() == 0
    with pytest.raises(Closed):
        queue.get()
    with pytest.raises(Closed):
        queue.put(3)


def test_cancel_pending_preserves_running_job_and_wakes_submitter():
    pool = WorkerPool(1, capacity=1)
    started = threading.Event()
    release = threading.Event()
    submitting = threading.Event()
    submitted = threading.Event()
    errors = []
    executed = []
    submitter = None

    def running_job():
        started.set()
        if not release.wait(5):
            raise TimeoutError('Test did not release running job')
        return 42

    def submit_blocked_job():
        submitting.set()
        try:
            pool.submit(executed.append, 'blocked')
        except RuntimeError as error:
            errors.append(error)
        finally:
            submitted.set()

    try:
        running = pool.submit(running_job)
        assert started.wait(2)
        pending = pool.submit(executed.append, 'pending')
        submitter = threading.Thread(target=submit_blocked_job)
        submitter.start()
        assert submitting.wait(2)
        assert not submitted.wait(0.05)

        pool.shutdown(wait=False, cancel_pending=True)
        assert pending.done()
        with pytest.raises(Cancelled):
            pending.result(timeout=0)
        assert not running.done()
        assert executed == []
        submitter.join(timeout=2)
        assert not submitter.is_alive()
        assert len(errors) == 1
        pool.shutdown(wait=False, cancel_pending=True)

        release.set()
        assert running.result(timeout=2) == 42
    finally:
        release.set()
        pool.shutdown(wait=False, cancel_pending=True)
        for worker in pool._workers:
            worker.join(timeout=2)
        if submitter is not None:
            submitter.join(timeout=2)
    assert all(not worker.is_alive() for worker in pool._workers)
    pool.shutdown(wait=True, cancel_pending=True)


def test_normal_shutdown_drains_jobs_and_joins_workers():
    pool = WorkerPool(4, capacity=8)
    try:
        futures = [pool.submit(pow, i, 2) for i in range(1000)]
        pool.shutdown(wait=True)
        assert [future.result(timeout=0) for future in futures] == [i * i for i in range(1000)]
        pool.shutdown(wait=True)
        with pytest.raises(RuntimeError):
            pool.submit(lambda: None)
    finally:
        pool.queue.close()
        for worker in pool._workers:
            worker.join(timeout=2)
    assert not any(thread.name.startswith('pool-worker-') for thread in threading.enumerate())
