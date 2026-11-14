import threading

from bbq import BoundedBlockingQueue, Closed


class Cancelled(Exception):
    """Raised when a queued task is cancelled before it runs."""


class Future:
    def __init__(self):
        self._event = threading.Event()
        self._value = None
        self._exception = None
        self._cancelled = False


    def result(self, timeout=None):
        if not self._event.wait(timeout): #timeout error
           raise TimeoutError
        else:
            if self._cancelled:
               raise Cancelled
            if self._exception is not None:
                raise self._exception
        return self._value


    def done(self):
        return self._event.is_set()


class WorkerPool:
    def __init__(self, n_workers, capacity=1000):
        self.capacity = capacity
        self.queue = BoundedBlockingQueue(capacity)
        self._workers = []
        self._shutdown_lock = threading.Lock()
        if n_workers < 1:
            raise ValueError
        for i in range(n_workers):
            worker = threading.Thread(
                target= self._worker,
                name= f"pool-worker-{i}",
                daemon= False
            )
            self._workers.append(worker)
            worker.start()

    def _worker(self):
        # Take jobs from the queue until it is closed and drained.
        while True:
            try:
                future, fn, args, kwargs = self.queue.get()
            except Closed:
                return

            try:
                future._value = fn(*args, **kwargs)
            except Exception as e:
                future._exception = e
            finally:
                future._event.set()



    def submit(self, fn, *args, **kwargs):
        try:
            future = Future()
            self.queue.put((future, fn, args, kwargs))
        except Closed as e:
            raise RuntimeError
        return future



    def map(self, fn, iterable):
        #input to function and put on queue
        futures = []
        for input in iterable:
            futures.append(self.submit(fn, input))

        results = []
        for future in futures:
            results.append(future.result())
        return results



    def shutdown(self, wait=True, cancel_pending=False):
        # Serialize close/cancel so another shutdown cannot return before
        # the futures removed from the queue have been signalled.
        with self._shutdown_lock:
            if cancel_pending:
                pending = self.queue.close_and_drain()
                for future, fn, args, kwargs in pending:
                    future._cancelled = True
                    future._event.set()
            else:
                self.queue.close()

        if wait:
            for worker in self._workers:
                worker.join()
