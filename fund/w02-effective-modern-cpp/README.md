# Effective Modern C++ flashcards

## 1. What does `noexcept` promise, and why does it matter?

`noexcept` promises that no exception will escape the function; if one does, the program calls `std::terminate`. The guarantee is part of the interface and can enable optimizations or change library behavior, such as allowing a `std::vector` to move elements safely during reallocation.

## 2. When does `std::vector` reallocation copy instead of move?

If `T` is copyable and its move constructor might throw, `std::vector<T>` generally copies existing elements during reallocation to preserve the strong exception guarantee. Marking a genuinely non-throwing move constructor `noexcept` lets the vector move; if copying is unavailable, it may have to use a potentially throwing move and weaken that guarantee.

## 3. Which special members does a user-declared destructor suppress?

A user-declared destructor suppresses implicit generation of the move constructor and move-assignment operator, while the copy constructor and copy-assignment operator may still be generated. A custom destructor often signals manual resource ownership, so safe moves may require explicitly transferring ownership instead of performing a memberwise move.

## 4. When should I consider passing a parameter by value?

Consider pass-by-value when the parameter is copyable, cheap to move, and unconditionally copied or moved into storage owned by the callee. It replaces separate `const T&` and `T&&` overloads with one function, but it may add an extra move or allocation, so it is a trade-off rather than a universal rule.

## 5. When is `emplace_back` no faster than `push_back`?

`emplace_back(widget)` is normally no faster than `push_back(widget)` because both copy-construct a `Widget` in the container; with `std::move(widget)`, both move-construct it. Emplacement can avoid a temporary when it receives constructor arguments of other types, such as `widgets.emplace_back(id, name)`, and constructs the element directly in container storage.

## 6. Why should insertion not be mechanically replaced with emplacement?

Emplacement may invoke explicit constructors through direct initialization even when insertion would reject the corresponding implicit conversion, so it can change program semantics. Passing a raw resource directly to emplacement can also leak it if container allocation throws before the element takes ownership, so establish RAII ownership first and use emplacement only when direct construction is intentional.

## Self-test corrections

The review clarified that pass-by-value's third condition concerns storage by the **callee**, and that raw resources should acquire RAII ownership before a potentially throwing container operation.

## Source

Scott Meyers, *Effective Modern C++*, Items 14, 17, 41 and 42.
