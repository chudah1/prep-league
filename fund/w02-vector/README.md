# Vector<T>: storage, growth, and ownership

C++20 learning implementation for parts 1 and 2. The implementation uses raw
storage, placement new, explicit destruction, and global operator delete; it does
not use std::vector internally.

## Implemented

- Default construction and construction of n value-initialized elements.
- push_back overloads, perfect-forwarding emplace_back, indexing, size, capacity,
  and reserve. Growth starts at 1 and doubles; reserve never shrinks.
- Deep-copy construction and copy assignment using copy-and-swap.
- noexcept move construction and assignment, transferring the buffer without
  copying or moving individual elements. A distinct moved-from source has size
  and capacity zero and can be reused; self-move preserves the vector.
- pop_back and clear destroy live elements without releasing capacity.
- Mutable and const pointer iterators through begin/end.

## Build and run

From the repository root:

```sh
cd fund/w02-vector
task_build_dir=$(mktemp -d)
clang++ -std=c++20 -Wall -Wextra -Wpedantic -O0 -g \
  -fsanitize=address,undefined -fno-omit-frame-pointer \
  test_vector.cpp -o "$task_build_dir/test_vector" && \
  "$task_build_dir/test_vector"
```

Verified final output line:

```text
PASS: 46 tests
```

The verified build produced no compiler warnings, and the run produced no ASan
or UBSan reports. Each test checks balanced successful constructions and
destructions after its objects leave scope. A single test can also be selected
by passing its name to the executable.

## Coverage and exception safety

Tests cover copy/move counts, move-only elements, multi-argument forwarding,
independent copies, ownership transfer, self-assignment, capacity retention,
pointer iteration, and appending an existing element during growth.

Growth tests check capacities 1, 2, 4, and 8 at sizes 1, 2, 3, and 5 respectively,
and continue through 17 elements. With noexcept-moving Counted elements, those
17 emplacements cause 31 relocation moves and no copies.

Reallocation uses std::move_if_noexcept: it moves noexcept-movable elements and
copies copyable elements whose move may throw. Failure tests throw on the first,
second, and third copies, checking unchanged source/destination state and cleanup
of partially constructed buffers. Copy assignment builds its temporary before
committing any member changes.

Growing emplace_back constructs the appended element before relocating existing
ones, so lvalue arguments referring to the old buffer remain usable during its
construction. Cleanup separately tracks the appended object and the relocated
prefix. This also preserves the initial empty state if the first constructor
throws.

## Baseline limitations

This is not a drop-in replacement for std::vector. Byte-count and capacity
overflow are not guarded, and the raw allocation path does not support types
requiring extended alignment. Element destructors are expected not to throw.
Indexing is unchecked; pop_back requires a non-empty vector.

For move-only elements whose move constructor can throw, std::move_if_noexcept
cannot fall back to copying. The implementation cleans up the new buffer on
failure, but cannot generally restore values already moved from in the old one.
