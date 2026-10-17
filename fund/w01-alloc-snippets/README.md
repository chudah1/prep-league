# C++ allocation, copy, and move snippets

## Environment

- Compiler: Apple Clang 17
- Standard: C++20
- Optimisation: `-O0`
- Sanitizers: AddressSanitizer and UndefinedBehaviorSanitizer
- Standard library: libc++

## Predictions and measurements

Predictions were recorded before running each snippet. Copy and move columns
refer specifically to observable `Tracer` constructor calls.

| # | Snippet | Predicted allocations | Predicted `Tracer` copies | Predicted `Tracer` moves | Actual allocations | Actual `Tracer` copies | Actual `Tracer` moves | Explanation if wrong |
|---:|---|---:|---:|---:|---:|---:|---:|---|
| 1 | Return a local by value (NRVO) | 0 | 2 | 0 | 0 | 0 | 0 | Clang applied NRVO, constructing the named local directly in the caller's `result` storage, so neither apparent copy occurred. |
| 2 | Return one of two locals via a ternary | 0 | 1 | 0 | 0 | 1 | 0 | Prediction matched: the ternary expression is an lvalue, so the selected local is copied into the return value. |
| 3a | `push_back(Tracer{})` | 1 | 0 | 1 | 1 | 0 | 1 | Prediction matched: the vector allocated its first storage block and moved the temporary into it. |
| 3b | `emplace_back(Tracer{})` | 2 | 0 | 0 | 1 | 0 | 1 | The vector needs only one storage allocation, while the already-created `Tracer{}` argument must still be moved into that storage. |
| 4 | `vector` growth to 17 elements without `reserve` | 17 | 0 | 7 | 6 | 0 | 31 | libc++ grew capacity geometrically, allocating at six capacity changes and moving all 1 + 2 + 4 + 8 + 16 existing elements during reallocations. |
| 5a | Short `std::string` (`"hello"`) | 0 | 0 | 0 | 0 | 0 | 0 | Prediction matched: libc++ stored the five characters in the string object's inline SSO buffer. |
| 5b | Long `std::string` (100 characters) | 1 | 0 | 0 | 1 | 0 | 0 | Prediction matched: the text exceeded the inline capacity, so the string allocated one external character buffer. |
| 6a | `std::function` with a large lambda capture | 1 | 1 | 0 | 1 | 1 | 1 | Capturing the lvalue copied the `LargeCapture`, then `std::function` allocated external storage and moved the resulting closure into it. |
| 6b | `std::function` with a small lambda capture | 0 | 0 | 0 | 0 | 0 | 0 | Prediction matched: the small closure fit in `std::function`'s inline storage and contained no `Tracer`. |
| 7 | `std::move` of a `const` object | 1 | 1 | 0 | 0 | 1 | 0 | Both local `Tracer` objects use automatic storage, while the `const Tracer&&` cannot bind to the non-const move constructor and therefore selects the copy constructor. |
| 8a | Range-for by value | 1 | 3 | 0 | 0 | 3 | 0 | `std::array` stores its elements inline without allocating, while each by-value loop variable is copy-constructed from an lvalue element. |
| 8b | Range-for by `const&` | 1 | 0 | 0 | 0 | 0 | 0 | `std::array` still needs no allocation, and each loop variable is only a reference to an existing element. |
| 9 | `vector<string>` from an initializer list | 0 | 0 | 0 | 1 | 0 | 0 | SSO avoided separate character buffers, but the vector still allocated one contiguous element buffer; the two semantic `std::string` copies are outside `Tracer`'s instrumentation. |
| 10 | `map::operator[]` on a missing key | 1 | 0 | 1 | 1 | 0 | 0 | The map allocated one node and default-constructed the mapped `Tracer` directly in that node, so no temporary was moved; the supplementary default-construction count was 1. |

## Build and run

```bash
clang++ -std=c++20 -O0 -g \
  -Wall -Wextra -Wpedantic \
  -fsanitize=address,undefined \
  -fno-omit-frame-pointer \
  main.cpp -o alloc_snippets
./alloc_snippets
```
