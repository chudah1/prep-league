"""Bounded blocking queue exercise: implement one method at a time."""

from collections import deque
import threading
import time


class Closed(Exception):
    """Raised when the queue is closed and an operation cannot proceed."""


class BoundedBlockingQueue:
    def __init__(self, capacity):
        self.capacity = capacity
        if self.capacity < 1:
            raise ValueError
        self.deque = deque(maxlen=capacity)
        self._lock = threading.Lock()
        self.not_full = threading.Condition(self._lock) # cv for the producer
        self.not_empty = threading.Condition(self._lock) # cv for consumer
        self.closed = False
 

    def put(self, item, timeout=None):
        deadline = None if timeout is None else timeout + time.monotonic()
            # grab the lock with the condition
        with self.not_full:
            # if queue is full and not closed wait till a consumeer gets something off or timeout
            while len(self.deque) >= self.capacity  and not self.closed:
                if deadline is None:
                    self.not_full.wait()
                else:
                    # your time reduce when you are woken up after waiting
                    remaining = deadline - time.monotonic()
                    if remaining <= 0:
                        raise TimeoutError
                    self.not_full.wait(remaining)

            if self.closed:
                raise Closed
            self.deque.append(item)
            #notify consumer that there is an item now
            self.not_empty.notify()

    def get(self, timeout=None):
        deadline = None if timeout is None else timeout + time.monotonic()
        # grab the lock with the condition
        with self.not_empty:
            # if the queue is empty and not closed wait till a producer puts something there
            while not self.deque and not self.closed:
                if deadline is None:
                    self.not_empty.wait()
                else:
                    # your time reduce when you are woken up after waiting
                    remaining = deadline - time.monotonic()
                    if remaining <= 0:
                        raise TimeoutError
                    self.not_empty.wait(remaining)
            
            #no items items left to drain
            if not self.deque:
                raise Closed
            oldest = self.deque.popleft()
            #notify producer there is spcae
            self.not_full.notify_all()
            return oldest
        
    def size(self):
        with self._lock:
            return len(self.deque)
     

    def close(self):
        with self._lock:
            self.closed = True
            self.not_full.notify_all()
            self.not_empty.notify_all()
