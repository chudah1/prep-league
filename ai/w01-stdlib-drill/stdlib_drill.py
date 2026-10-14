# Mistakes fixed during the drill:
# - Wrote the Counter expectation as one string instead of a (value, count) tuple.
# - Forgot that defaultdict grouping puts "nice" in the "n" group.
# - Expected appendleft on a bounded deque to drop the wrong end.
# - Did not initially build a size-k heap or compare it with heapq.nlargest.
# - Forgot that insort preserves duplicate values and misread bisect_left's index.
# - Expected dataclass ordering to use age even though name was declared first.
# - Created separate locks, used commas instead of numeric underscores, and added
#   the loop index instead of incrementing the threaded counter by one.
# - Forgot that itertools.groupby only combines consecutive matching keys.
# - Initially omitted asyncio.gather and its argument-order guarantee.

import collections
import heapq
from bisect import insort, bisect_left
from dataclasses import dataclass
import itertools
import threading
import asyncio

counter_res = collections.Counter("abracadabra").most_common(1)

assert counter_res == [("a", 5)]

mapping = collections.defaultdict(list)
words = ["soft", "tech", "software", "twitter", "nice"]

for word in words:
    mapping[word[0]].append(word)

assert mapping == {"s":["soft", "software"], "t":["tech", "twitter"], "n": ["nice"]}

deque = collections.deque([1,2,4], maxlen=3)
deque.appendleft(0)
assert list(deque) == [0,1,2]
deque.popleft()
assert list(deque) == [1,2]

numbers = [7, 1, 9, 3, 12, 5, 10]
k = 3
min_heap = []

for number in numbers:
    if len(min_heap) < k:
        heapq.heappush(min_heap, number)
    else:
        heapq.heappushpop(min_heap, number)

heap_largest = sorted(min_heap, reverse=True)
nlargest_result = heapq.nlargest(k, numbers)

assert heap_largest == nlargest_result == [12, 10, 9]

array = [1,2,2,4,5,5]

insort(array, 0)
assert array == [0, 1,2,2,4,5,5]
index = bisect_left(array, 2)
assert index == 2


@dataclass(order=True)
class Person:
    name: str
    age: int

p1 = Person(name="Kofi", age=10)
p2 = Person(name="Ama", age =20)

assert p1 > p2

assert sorted([p1, p2]) == [p2, p1]

count = 0
lock = threading.Lock()

def increment_count():
    global count

    with lock:
        for i in range(10_000):
            count +=1

threads = []
for _ in range(4):
    thread = threading.Thread(target=increment_count)
    threads.append(thread)
    thread.start()

for t in threads:
    t.join()

assert count == 40_000

words = ["ate", "cat", "ant", "bat"]
expected = [{"a":["ate", "ant"],
             "b": ["bat"],
             "c": ["cat"]
             }]
unsorted = [

    {
        letter: list(group)
        for letter, group in itertools.groupby(words, lambda x: x[0])
    }
]

assert unsorted != expected

sorted_words = sorted(words, key=lambda x:x[0])

sorted_group = [

    {
        letter: list(group)
        for letter, group in itertools.groupby(sorted_words, lambda x: x[0])
    }
]

assert sorted_group == expected

async def fetch(name, delay) -> str:
    await asyncio.sleep(delay)
    return name

async def main():
    results = await asyncio.gather(
        fetch("first", 0.3),
        fetch("second", 0.1),
        fetch("third", 0.2)
    )

    assert results == ["first", "second", "third"]

asyncio.run(main())
