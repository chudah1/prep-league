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
            raise ValueError("capcity should not be less than 1")
        self.deque = deque(maxlen=capacity)
        self._lock = threading.Lock()
        self.closed =  False # to sync among the thread 
        self.not_full = threading.Condition(self._lock) #for producer
        self.not_empty = threading.Condition(self._lock) #for consumer

    def put(self, item, timeout=None):
        deadline = None if timeout is None else time.monotonic() + timeout
        with self.not_full:
            while len(self.deque) >= self.capacity and not self.closed:
                if deadline is None:
                    self.not_full.wait()
                else:
                    remaining = deadline - time.monotonic()
                    if remaining <= 0:
                        raise TimeoutError
                    else:
                        self.not_full.wait(remaining)
            if self.closed:
                raise Closed
            self.deque.append(item)
            self.not_empty.notify_all()

    def get(self, timeout=None):
        deadline = None if timeout is None else time.monotonic() + timeout
        with self.not_empty:
            while not self.deque and not self.closed:
                if deadline is None:
                    self.not_empty.wait()
                else:
                    remaining = deadline - time.monotonic()
                    if remaining <=0:
                        raise TimeoutError
                    else:
                        self.not_empty.wait(remaining)
            
            if not self.deque:
                raise Closed
            
            oldest = self.deque.popleft()
            self.not_full.notify_all()
            return oldest
    def size(self):
        with self._lock as lock:
            size = len(self.deque)
            return size

    def close(self):
        with self._lock:
            self.closed = True
            self.not_empty.notify_all()
            self.not_full.notify_all()
