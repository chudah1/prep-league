#include "vector.hpp"

#include <cassert>
#include <iostream>
#include <memory>
#include <string_view>
#include <type_traits>

struct Counted {
    inline static int constructions = 0;
    inline static int copies = 0;
    inline static int moves = 0;
    inline static int destructions = 0;

    int value;

    explicit Counted(int initial_value = 0) : value(initial_value) {
        ++constructions;
    }

    Counted(const Counted& other) : value(other.value) {
        ++constructions;
        ++copies;
    }

    Counted(Counted&& other) noexcept : value(other.value) {
        ++constructions;
        ++moves;
        other.value = -1;
    }

    ~Counted() {
        ++destructions;
    }

    static void reset() {
        assert(constructions == destructions);
        constructions = copies = moves = destructions = 0;
    }
};

struct ConstructionFailure {};

struct ThrowingCounted {
    inline static int attempts = 0;
    inline static int constructions = 0;
    inline static int destructions = 0;
    inline static int throw_on_attempt = 0;

    ThrowingCounted() {
        if (++attempts == throw_on_attempt) {
            throw ConstructionFailure{};
        }
        ++constructions;
    }

    ~ThrowingCounted() {
        ++destructions;
    }

    static void reset(int fail_at) {
        assert(constructions == destructions);
        attempts = constructions = destructions = 0;
        throw_on_attempt = fail_at;
    }
};

struct CopyFallbackCounted {
    inline static int constructions = 0;
    inline static int copies = 0;
    inline static int moves = 0;
    inline static int destructions = 0;
    inline static int copy_attempts = 0;
    inline static int throw_on_copy = 0;

    int value;

    explicit CopyFallbackCounted(int initial_value = 0) : value(initial_value) {
        ++constructions;
    }

    CopyFallbackCounted(const CopyFallbackCounted& other) : value(other.value) {
        if (++copy_attempts == throw_on_copy) {
            throw ConstructionFailure{};
        }
        ++constructions;
        ++copies;
    }

    CopyFallbackCounted(CopyFallbackCounted&& other) noexcept(false)
        : value(other.value) {
        ++constructions;
        ++moves;
        other.value = -1;
    }

    ~CopyFallbackCounted() {
        ++destructions;
    }

    static void reset(int fail_at = 0) {
        assert(constructions == destructions);
        constructions = copies = moves = destructions = copy_attempts = 0;
        throw_on_copy = fail_at;
    }
};

void test_empty_vector() {
    Counted::reset();
    {
        Vector<Counted> values;
        assert(values.size() == 0);
        assert(values.capacity() == 0);
        assert(Counted::constructions == 0);
    }
    assert(Counted::constructions == Counted::destructions);
}

void test_zero_size_constructor() {
    Counted::reset();
    {
        Vector<Counted> values(0);
        assert(values.size() == 0);
        assert(values.capacity() == 0);
        assert(Counted::constructions == 0);
    }
    assert(Counted::constructions == Counted::destructions);
}

void test_size_constructor() {
    Counted::reset();
    {
        const Vector<Counted> values(3);
        assert(values.size() == 3);
        assert(values.capacity() == 3);
        assert(Counted::constructions == 3);
        assert(Counted::copies == 0);
        assert(Counted::moves == 0);
        assert(Counted::destructions == 0);
    }
    assert(Counted::constructions == Counted::destructions);
}

void test_partial_construction_cleanup() {
    for (int fail_at = 1; fail_at <= 3; ++fail_at) {
        ThrowingCounted::reset(fail_at);
        bool threw = false;
        try {
            Vector<ThrowingCounted> values(3);
        } catch (const ConstructionFailure&) {
            threw = true;
        }
        assert(threw);
        assert(ThrowingCounted::attempts == fail_at);
        assert(ThrowingCounted::constructions == fail_at - 1);
        assert(ThrowingCounted::constructions == ThrowingCounted::destructions);
    }
}

void test_index_access_and_value_initialization() {
    Counted::reset();
    {
        Vector<Counted> values(3);
        for (std::size_t i = 0; i < values.size(); ++i) {
            assert(values[i].value == 0);
        }
        values[1].value = 42;
        const auto& view = values;
        assert(view[1].value == 42);
        assert(&view[1] == &values[1]);
        assert(Counted::constructions == 3);
        assert(Counted::copies == 0);
        assert(Counted::moves == 0);
        assert(Counted::destructions == 0);

        Vector<int> numbers(3);
        for (std::size_t i = 0; i < numbers.size(); ++i) {
            assert(numbers[i] == 0);
        }
        numbers[1] = 7;
        const auto& number_view = numbers;
        assert(number_view[1] == 7);
    }
    assert(Counted::constructions == Counted::destructions);
}

void test_reserve_empty() {
    Counted::reset();
    {
        Vector<Counted> values;
        values.reserve(8);
        assert(values.size() == 0);
        assert(values.capacity() == 8);
        assert(Counted::constructions == 0);
        assert(Counted::destructions == 0);
    }
    assert(Counted::constructions == Counted::destructions);
}

void test_reserve_moves_existing_elements() {
    Counted::reset();
    {
        Vector<Counted> values(3);
        for (std::size_t i = 0; i < values.size(); ++i) {
            values[i].value = static_cast<int>(i + 10);
        }
        values.reserve(8);
        assert(values.size() == 3);
        assert(values.capacity() == 8);
        for (std::size_t i = 0; i < values.size(); ++i) {
            assert(values[i].value == static_cast<int>(i + 10));
        }
        assert(Counted::constructions == 6);
        assert(Counted::moves == 3);
        assert(Counted::copies == 0);
        assert(Counted::destructions == 3);
    }
    assert(Counted::constructions == Counted::destructions);
}

void check_reserve_noop(std::size_t requested_capacity) {
    Counted::reset();
    {
        Vector<Counted> values(3);
        values[1].value = 42;
        values.reserve(requested_capacity);
        assert(values.size() == 3);
        assert(values.capacity() == 3);
        assert(values[1].value == 42);
        assert(Counted::constructions == 3);
        assert(Counted::copies == 0);
        assert(Counted::moves == 0);
        assert(Counted::destructions == 0);
    }
    assert(Counted::constructions == Counted::destructions);
}

void test_reserve_smaller_capacity() {
    check_reserve_noop(2);
}

void test_reserve_equal_capacity() {
    check_reserve_noop(3);
}

void test_reserve_copy_fallback() {
    CopyFallbackCounted::reset();
    {
        Vector<CopyFallbackCounted> values(3);
        values[1].value = 42;
        values.reserve(8);
        assert(values.size() == 3);
        assert(values.capacity() == 8);
        assert(values[1].value == 42);
        assert(CopyFallbackCounted::constructions == 6);
        assert(CopyFallbackCounted::copies == 3);
        assert(CopyFallbackCounted::moves == 0);
        assert(CopyFallbackCounted::destructions == 3);
    }
    assert(CopyFallbackCounted::constructions == CopyFallbackCounted::destructions);
}

void test_reserve_exception_cleanup() {
    for (int fail_at = 1; fail_at <= 3; ++fail_at) {
        CopyFallbackCounted::reset(fail_at);
        {
            Vector<CopyFallbackCounted> values(3);
            for (std::size_t i = 0; i < values.size(); ++i) {
                values[i].value = static_cast<int>(i + 10);
            }
            bool threw = false;
            try {
                values.reserve(8);
            } catch (const ConstructionFailure&) {
                threw = true;
            }
            assert(threw);
            assert(values.size() == 3);
            assert(values.capacity() == 3);
            for (std::size_t i = 0; i < values.size(); ++i) {
                assert(values[i].value == static_cast<int>(i + 10));
            }
            assert(CopyFallbackCounted::copies == fail_at - 1);
            assert(CopyFallbackCounted::moves == 0);
        }
        assert(CopyFallbackCounted::constructions == CopyFallbackCounted::destructions);
    }
}

void test_emplace_with_spare_capacity() {
    Counted::reset();
    {
        Vector<Counted> values;
        values.reserve(2);
        const int answer = 42;
        Counted& first = values.emplace_back(answer);
        assert(&first == &values[0]);
        assert(first.value == 42);
        assert(values.size() == 1);

        Counted& second = values.emplace_back();
        assert(&second == &values[1]);
        assert(second.value == 0);
        assert(values.size() == 2);
        assert(values.capacity() == 2);
        assert(Counted::constructions == 2);
        assert(Counted::copies == 0);
        assert(Counted::moves == 0);
    }
    assert(Counted::constructions == Counted::destructions);
}

void test_emplace_growth() {
    Counted::reset();
    {
        Vector<Counted> values;
        const std::size_t expected_capacities[] = {
            1, 2, 4, 4, 8, 8, 8, 8, 16, 16, 16, 16, 16, 16, 16, 16, 32,
        };
        for (std::size_t i = 0; i < 17; ++i) {
            Counted& added = values.emplace_back(static_cast<int>(i));
            assert(&added == &values[i]);
            assert(values.size() == i + 1);
            assert(values.capacity() == expected_capacities[i]);
            for (std::size_t j = 0; j <= i; ++j) {
                assert(values[j].value == static_cast<int>(j));
            }
        }
        assert(Counted::copies == 0);
        assert(Counted::moves == 31);
        assert(Counted::constructions == 48);
        assert(Counted::destructions == 31);
    }
    assert(Counted::constructions == Counted::destructions);
}

void test_emplace_constructor_failure() {
    ThrowingCounted::reset(2);
    {
        Vector<ThrowingCounted> values;
        values.reserve(2);
        values.emplace_back();
        bool threw = false;
        try {
            values.emplace_back();
        } catch (const ConstructionFailure&) {
            threw = true;
        }
        assert(threw);
        assert(values.size() == 1);
        assert(values.capacity() == 2);
        assert(ThrowingCounted::constructions == 1);
        assert(ThrowingCounted::destructions == 0);
        values.emplace_back();
        assert(values.size() == 2);
        assert(ThrowingCounted::constructions == 2);
    }
    assert(ThrowingCounted::constructions == ThrowingCounted::destructions);
}

void test_emplace_alias_during_growth() {
    Counted::reset();
    {
        Vector<Counted> values;
        values.emplace_back(42);
        values.emplace_back(values[0]);
        assert(values.size() == 2);
        assert(values.capacity() == 2);
        assert(values[0].value == 42);
        assert(values[1].value == 42);
        assert(Counted::copies == 1);
        assert(Counted::moves == 1);
    }
    assert(Counted::constructions == Counted::destructions);
}

void test_emplace_growth_constructor_failure() {
    ThrowingCounted::reset(2);
    {
        Vector<ThrowingCounted> values(1);
        bool threw = false;
        try {
            values.emplace_back();
        } catch (const ConstructionFailure&) {
            threw = true;
        }
        assert(threw);
        assert(values.size() == 1);
        assert(values.capacity() == 1);
        assert(ThrowingCounted::constructions == 1);
        assert(ThrowingCounted::destructions == 0);
    }
    assert(ThrowingCounted::constructions == ThrowingCounted::destructions);
}

void test_emplace_growth_exception_cleanup() {
    for (int fail_at = 1; fail_at <= 3; ++fail_at) {
        CopyFallbackCounted::reset(fail_at);
        {
            Vector<CopyFallbackCounted> values(3);
            for (std::size_t i = 0; i < values.size(); ++i) {
                values[i].value = static_cast<int>(i + 10);
            }
            bool threw = false;
            try {
                values.emplace_back(99);
            } catch (const ConstructionFailure&) {
                threw = true;
            }
            assert(threw);
            assert(values.size() == 3);
            assert(values.capacity() == 3);
            for (std::size_t i = 0; i < values.size(); ++i) {
                assert(values[i].value == static_cast<int>(i + 10));
            }
            assert(CopyFallbackCounted::copies == fail_at - 1);
            assert(CopyFallbackCounted::moves == 0);
        }
        assert(CopyFallbackCounted::constructions == CopyFallbackCounted::destructions);
    }
}

void test_push_back_lvalue() {
    Counted::reset();
    {
        Vector<Counted> values;
        values.reserve(2);
        Counted source(42);
        const Counted constant_source(7);
        values.push_back(source);
        values.push_back(constant_source);
        assert(values.size() == 2);
        assert(values[0].value == 42);
        assert(values[1].value == 7);
        assert(source.value == 42);
        assert(constant_source.value == 7);
        assert(Counted::copies == 2);
        assert(Counted::moves == 0);
        assert(Counted::constructions == 4);
    }
    assert(Counted::constructions == Counted::destructions);
}

void test_push_back_rvalue() {
    Counted::reset();
    {
        Vector<Counted> values;
        values.reserve(2);
        Counted source(42);
        values.push_back(std::move(source));
        assert(values.size() == 1);
        assert(values[0].value == 42);
        assert(source.value == -1);
        assert(Counted::copies == 0);
        assert(Counted::moves == 1);
        assert(Counted::constructions == 2);
    }
    assert(Counted::constructions == Counted::destructions);
}

void test_push_back_temporary() {
    Counted::reset();
    {
        Vector<Counted> values;
        values.reserve(2);
        values.push_back(Counted(42));
        assert(values.size() == 1);
        assert(values[0].value == 42);
        assert(Counted::copies == 0);
        assert(Counted::moves == 1);
        assert(Counted::constructions == 2);
        assert(Counted::destructions == 1);
    }
    assert(Counted::constructions == Counted::destructions);
}

void test_push_back_const_rvalue_copies() {
    Counted::reset();
    {
        Vector<Counted> values;
        values.reserve(2);
        const Counted source(42);
        values.push_back(std::move(source));
        assert(values.size() == 1);
        assert(values[0].value == 42);
        assert(source.value == 42);
        assert(Counted::copies == 1);
        assert(Counted::moves == 0);
    }
    assert(Counted::constructions == Counted::destructions);
}

void test_push_back_growth() {
    Counted::reset();
    {
        Vector<Counted> values;
        Counted source(42);
        const std::size_t expected_capacities[] = {
            1, 2, 4, 4, 8, 8, 8, 8, 16, 16, 16, 16, 16, 16, 16, 16, 32,
        };
        for (std::size_t i = 0; i < 17; ++i) {
            values.push_back(source);
            assert(values.size() == i + 1);
            assert(values.capacity() == expected_capacities[i]);
            for (std::size_t j = 0; j <= i; ++j) {
                assert(values[j].value == 42);
            }
        }
        assert(source.value == 42);
        assert(Counted::copies == 17);
        assert(Counted::moves == 31);
        assert(Counted::constructions == 49);
        assert(Counted::destructions == 31);
    }
    assert(Counted::constructions == Counted::destructions);
}

void test_push_back_alias_during_growth() {
    Counted::reset();
    {
        Vector<Counted> values;
        values.emplace_back(42);
        values.push_back(values[0]);
        assert(values.size() == 2);
        assert(values.capacity() == 2);
        assert(values[0].value == 42);
        assert(values[1].value == 42);
        assert(Counted::copies == 1);
        assert(Counted::moves == 1);
    }
    assert(Counted::constructions == Counted::destructions);
}

void test_forwarding_and_move_only_elements() {
    struct Payload : Counted {
        std::unique_ptr<int> owned;

        Payload(int label, std::unique_ptr<int> resource)
            : Counted(label), owned(std::move(resource)) {}

        Payload(const Payload&) = delete;
        Payload(Payload&&) noexcept = default;
    };

    Counted::reset();
    {
        Vector<Payload> values;
        auto resource = std::make_unique<int>(99);
        Payload& first = values.emplace_back(7, std::move(resource));
        assert(!resource);
        assert(&first == &values[0]);
        assert(first.value == 7);
        assert(*first.owned == 99);

        values.push_back(Payload(8, std::make_unique<int>(100)));
        values.reserve(8);
        assert(values.size() == 2);
        assert(values.capacity() == 8);
        assert(values[0].value == 7);
        assert(*values[0].owned == 99);
        assert(values[1].value == 8);
        assert(*values[1].owned == 100);
        assert(Counted::copies == 0);
        assert(Counted::moves == 4);
        assert(Counted::constructions == 6);
        assert(Counted::destructions == 4);
    }
    assert(Counted::constructions == Counted::destructions);
}

void test_copy_constructor_independent_storage() {
    Counted::reset();
    {
        Vector<Counted> source(3);
        source.reserve(8);
        for (std::size_t i = 0; i < source.size(); ++i) {
            source[i].value = static_cast<int>(i + 10);
        }
        const auto& const_source = source;
        const int previous_constructions = Counted::constructions;
        const int previous_copies = Counted::copies;
        const int previous_moves = Counted::moves;
        {
            Vector<Counted> copied(const_source);
            assert(copied.size() == 3);
            assert(copied.capacity() >= copied.size());
            assert(&copied[0] != &source[0]);
            for (std::size_t i = 0; i < source.size(); ++i) {
                assert(copied[i].value == source[i].value);
            }
            assert(Counted::constructions == previous_constructions + 3);
            assert(Counted::copies == previous_copies + 3);
            assert(Counted::moves == previous_moves);

            copied[0].value = 99;
            assert(source[0].value == 10);
            source[1].value = 77;
            assert(copied[1].value == 11);
        }
        assert(source.size() == 3);
        assert(source.capacity() == 8);
        assert(source[0].value == 10);
        assert(source[1].value == 77);
        assert(source[2].value == 12);
        assert(Counted::constructions - Counted::destructions == 3);
    }
    assert(Counted::constructions == Counted::destructions);
}

void test_copy_constructor_empty() {
    Counted::reset();
    {
        const Vector<Counted> empty;
        Vector<Counted> empty_copy(empty);
        assert(empty_copy.size() == 0);

        Vector<Counted> reserved;
        reserved.reserve(8);
        Vector<Counted> reserved_copy(reserved);
        assert(reserved_copy.size() == 0);
        assert(reserved.size() == 0);
        assert(reserved.capacity() == 8);
        assert(Counted::constructions == 0);
        assert(Counted::copies == 0);
        assert(Counted::moves == 0);
    }
    assert(Counted::constructions == Counted::destructions);
}

void test_copy_constructor_exception_cleanup() {
    for (int fail_at = 1; fail_at <= 3; ++fail_at) {
        CopyFallbackCounted::reset(fail_at);
        {
            Vector<CopyFallbackCounted> source(3);
            for (std::size_t i = 0; i < source.size(); ++i) {
                source[i].value = static_cast<int>(i + 10);
            }
            bool threw = false;
            try {
                Vector<CopyFallbackCounted> copied(source);
            } catch (const ConstructionFailure&) {
                threw = true;
            }
            assert(threw);
            assert(source.size() == 3);
            assert(source.capacity() == 3);
            for (std::size_t i = 0; i < source.size(); ++i) {
                assert(source[i].value == static_cast<int>(i + 10));
            }
            assert(CopyFallbackCounted::copy_attempts == fail_at);
            assert(CopyFallbackCounted::copies == fail_at - 1);
            assert(CopyFallbackCounted::moves == 0);
            assert(CopyFallbackCounted::constructions == 3 + fail_at - 1);
            assert(CopyFallbackCounted::destructions == fail_at - 1);
        }
        assert(CopyFallbackCounted::constructions == CopyFallbackCounted::destructions);
    }
}

void test_copy_constructor_non_default_elements() {
    struct NonDefault : Counted {
        explicit NonDefault(int initial_value) : Counted(initial_value) {}
    };

    Counted::reset();
    {
        Vector<NonDefault> source;
        source.emplace_back(42);
        source.emplace_back(7);
        const int previous_constructions = Counted::constructions;
        const int previous_copies = Counted::copies;
        const int previous_moves = Counted::moves;
        Vector<NonDefault> copied(source);
        assert(copied.size() == 2);
        assert(copied[0].value == 42);
        assert(copied[1].value == 7);
        assert(&copied[0] != &source[0]);
        assert(Counted::constructions == previous_constructions + 2);
        assert(Counted::copies == previous_copies + 2);
        assert(Counted::moves == previous_moves);
    }
    assert(Counted::constructions == Counted::destructions);
}

void test_move_constructor_transfers_buffer() {
    static_assert(std::is_nothrow_move_constructible_v<Vector<Counted>>);
    Counted::reset();
    {
        Vector<Counted> source(3);
        source.reserve(8);
        for (std::size_t i = 0; i < source.size(); ++i) {
            source[i].value = static_cast<int>(i + 10);
        }
        Counted* original_storage = &source[0];
        const int previous_constructions = Counted::constructions;
        const int previous_copies = Counted::copies;
        const int previous_moves = Counted::moves;
        const int previous_destructions = Counted::destructions;
        {
            Vector<Counted> moved(std::move(source));
            assert(moved.size() == 3);
            assert(moved.capacity() == 8);
            assert(&moved[0] == original_storage);
            assert(source.size() == 0);
            assert(source.capacity() == 0);
            for (std::size_t i = 0; i < moved.size(); ++i) {
                assert(moved[i].value == static_cast<int>(i + 10));
            }
            assert(Counted::constructions == previous_constructions);
            assert(Counted::copies == previous_copies);
            assert(Counted::moves == previous_moves);
            assert(Counted::destructions == previous_destructions);

            source.emplace_back(99);
            assert(source.size() == 1);
            assert(source.capacity() == 1);
            assert(source[0].value == 99);
            assert(&source[0] != &moved[0]);
            assert(moved[0].value == 10);
        }
        assert(source.size() == 1);
        assert(source[0].value == 99);
        assert(Counted::constructions - Counted::destructions == 1);
    }
    assert(Counted::constructions == Counted::destructions);
}

void test_move_constructor_outlives_source() {
    Counted::reset();
    {
        Vector<Counted> moved = [] {
            Vector<Counted> source(3);
            source[0].value = 10;
            source[1].value = 11;
            source[2].value = 12;
            return Vector<Counted>(std::move(source));
        }();
        assert(moved.size() == 3);
        assert(moved.capacity() == 3);
        assert(moved[0].value == 10);
        assert(moved[1].value == 11);
        assert(moved[2].value == 12);
        assert(Counted::constructions == 3);
        assert(Counted::copies == 0);
        assert(Counted::moves == 0);
        assert(Counted::destructions == 0);
    }
    assert(Counted::constructions == Counted::destructions);
}

void test_move_constructor_empty() {
    Counted::reset();
    {
        Vector<Counted> empty;
        Vector<Counted> moved_empty(std::move(empty));
        assert(empty.size() == 0);
        assert(empty.capacity() == 0);
        assert(moved_empty.size() == 0);
        assert(moved_empty.capacity() == 0);

        Vector<Counted> reserved;
        reserved.reserve(8);
        Vector<Counted> moved_reserved(std::move(reserved));
        assert(reserved.size() == 0);
        assert(reserved.capacity() == 0);
        assert(moved_reserved.size() == 0);
        assert(moved_reserved.capacity() == 8);
        assert(Counted::constructions == 0);
        assert(Counted::copies == 0);
        assert(Counted::moves == 0);
        assert(Counted::destructions == 0);
    }
    assert(Counted::constructions == Counted::destructions);
}

void test_move_constructor_move_only_elements() {
    struct MoveOnly : Counted {
        explicit MoveOnly(int initial_value) : Counted(initial_value) {}
        MoveOnly(const MoveOnly&) = delete;
        MoveOnly(MoveOnly&&) noexcept = default;
    };

    Counted::reset();
    {
        Vector<MoveOnly> source;
        source.emplace_back(42);
        MoveOnly* original_storage = &source[0];
        Vector<MoveOnly> moved(std::move(source));
        assert(source.size() == 0);
        assert(source.capacity() == 0);
        assert(moved.size() == 1);
        assert(moved.capacity() == 1);
        assert(&moved[0] == original_storage);
        assert(moved[0].value == 42);
        assert(Counted::constructions == 1);
        assert(Counted::copies == 0);
        assert(Counted::moves == 0);
        assert(Counted::destructions == 0);
    }
    assert(Counted::constructions == Counted::destructions);
}

void test_copy_assignment_replaces_contents() {
    Counted::reset();
    {
        Vector<Counted> source(3);
        source.reserve(8);
        for (std::size_t i = 0; i < source.size(); ++i) {
            source[i].value = static_cast<int>(i + 10);
        }
        Vector<Counted> destination(2);
        destination[0].value = 90;
        destination[1].value = 91;
        destination.reserve(4);
        const int previous_constructions = Counted::constructions;
        const int previous_copies = Counted::copies;
        const int previous_moves = Counted::moves;
        const int previous_destructions = Counted::destructions;
        const auto& const_source = source;

        Vector<Counted>& result = (destination = const_source);
        assert(&result == &destination);
        assert(destination.size() == 3);
        assert(destination.capacity() >= destination.size());
        assert(&destination[0] != &source[0]);
        assert(source.size() == 3);
        assert(source.capacity() == 8);
        for (std::size_t i = 0; i < source.size(); ++i) {
            assert(destination[i].value == static_cast<int>(i + 10));
            assert(source[i].value == static_cast<int>(i + 10));
        }
        assert(Counted::constructions == previous_constructions + 3);
        assert(Counted::copies == previous_copies + 3);
        assert(Counted::moves == previous_moves);
        assert(Counted::destructions == previous_destructions + 2);
        destination[0].value = 99;
        assert(source[0].value == 10);
        source[1].value = 77;
        assert(destination[1].value == 11);
    }
    assert(Counted::constructions == Counted::destructions);
}

void test_copy_assignment_empty_cases() {
    for (std::size_t source_size = 0; source_size <= 2; source_size += 2) {
        for (std::size_t destination_size = 0; destination_size <= 3; destination_size += 3) {
            Counted::reset();
            {
                Vector<Counted> source(source_size);
                Vector<Counted> destination(destination_size);
                for (std::size_t i = 0; i < source.size(); ++i) {
                    source[i].value = static_cast<int>(i + 10);
                }
                Vector<Counted>& result = (destination = source);
                assert(&result == &destination);
                assert(destination.size() == source_size);
                assert(destination.capacity() >= source_size);
                assert(source.size() == source_size);
                for (std::size_t i = 0; i < source.size(); ++i) {
                    assert(destination[i].value == static_cast<int>(i + 10));
                    assert(source[i].value == static_cast<int>(i + 10));
                }
                assert(Counted::copies == static_cast<int>(source_size));
                assert(Counted::moves == 0);
                assert(Counted::destructions == static_cast<int>(destination_size));
            }
            assert(Counted::constructions == Counted::destructions);
        }
    }
}

void test_copy_assignment_self() {
    Counted::reset();
    {
        Vector<Counted> values(3);
        values.reserve(8);
        for (std::size_t i = 0; i < values.size(); ++i) {
            values[i].value = static_cast<int>(i + 10);
        }
        const auto& alias = values;
        Vector<Counted>& result = (values = alias);
        assert(&result == &values);
        assert(values.size() == 3);
        assert(values.capacity() >= values.size());
        for (std::size_t i = 0; i < values.size(); ++i) {
            assert(values[i].value == static_cast<int>(i + 10));
        }
        assert(Counted::constructions - Counted::destructions == 3);
    }
    assert(Counted::constructions == Counted::destructions);
}

void test_copy_assignment_strong_guarantee() {
    for (int fail_at = 1; fail_at <= 3; ++fail_at) {
        CopyFallbackCounted::reset();
        {
            Vector<CopyFallbackCounted> source(3);
            Vector<CopyFallbackCounted> destination(2);
            destination.reserve(8);
            for (std::size_t i = 0; i < source.size(); ++i) {
                source[i].value = static_cast<int>(i + 10);
            }
            destination[0].value = 90;
            destination[1].value = 91;
            CopyFallbackCounted* original_storage = &destination[0];
            const int previous_constructions = CopyFallbackCounted::constructions;
            const int previous_copies = CopyFallbackCounted::copies;
            const int previous_destructions = CopyFallbackCounted::destructions;
            const int previous_attempts = CopyFallbackCounted::copy_attempts;
            CopyFallbackCounted::throw_on_copy = previous_attempts + fail_at;

            bool threw = false;
            try {
                destination = source;
            } catch (const ConstructionFailure&) {
                threw = true;
            }
            assert(threw);
            assert(destination.size() == 2);
            assert(destination.capacity() == 8);
            assert(&destination[0] == original_storage);
            assert(destination[0].value == 90);
            assert(destination[1].value == 91);
            assert(source.size() == 3);
            assert(source.capacity() == 3);
            for (std::size_t i = 0; i < source.size(); ++i) {
                assert(source[i].value == static_cast<int>(i + 10));
            }
            assert(CopyFallbackCounted::copy_attempts == previous_attempts + fail_at);
            assert(CopyFallbackCounted::copies == previous_copies + fail_at - 1);
            assert(CopyFallbackCounted::moves == 0);
            assert(CopyFallbackCounted::constructions == previous_constructions + fail_at - 1);
            assert(CopyFallbackCounted::destructions == previous_destructions + fail_at - 1);
        }
        assert(CopyFallbackCounted::constructions == CopyFallbackCounted::destructions);
    }
}

void test_move_assignment_transfers_buffer() {
    static_assert(std::is_nothrow_move_assignable_v<Vector<Counted>>);
    Counted::reset();
    {
        Vector<Counted> destination(2);
        destination.reserve(4);
        {
            Vector<Counted> source(3);
            source.reserve(8);
            for (std::size_t i = 0; i < source.size(); ++i) {
                source[i].value = static_cast<int>(i + 10);
            }
            Counted* original_storage = &source[0];
            const int previous_constructions = Counted::constructions;
            const int previous_copies = Counted::copies;
            const int previous_moves = Counted::moves;
            const int previous_destructions = Counted::destructions;

            Vector<Counted>& result = (destination = std::move(source));
            assert(&result == &destination);
            assert(destination.size() == 3);
            assert(destination.capacity() == 8);
            assert(&destination[0] == original_storage);
            assert(source.size() == 0);
            assert(source.capacity() == 0);
            assert(Counted::constructions == previous_constructions);
            assert(Counted::copies == previous_copies);
            assert(Counted::moves == previous_moves);
            assert(Counted::destructions == previous_destructions + 2);
            source.emplace_back(99);
            assert(source.size() == 1);
            assert(source.capacity() == 1);
            assert(source[0].value == 99);
            assert(&source[0] != &destination[0]);
        }
        for (std::size_t i = 0; i < destination.size(); ++i) {
            assert(destination[i].value == static_cast<int>(i + 10));
        }
        assert(Counted::constructions - Counted::destructions == 3);
    }
    assert(Counted::constructions == Counted::destructions);
}

void test_move_assignment_empty_cases() {
    for (std::size_t source_size = 0; source_size <= 2; source_size += 2) {
        for (std::size_t destination_size = 0; destination_size <= 3; destination_size += 3) {
            Counted::reset();
            {
                Vector<Counted> source(source_size);
                if (source_size == 0) {
                    source.reserve(8);
                }
                Vector<Counted> destination(destination_size);
                for (std::size_t i = 0; i < source.size(); ++i) {
                    source[i].value = static_cast<int>(i + 10);
                }
                const std::size_t previous_capacity = source.capacity();
                const int previous_constructions = Counted::constructions;
                Vector<Counted>& result = (destination = std::move(source));
                assert(&result == &destination);
                assert(destination.size() == source_size);
                assert(destination.capacity() == previous_capacity);
                assert(source.size() == 0);
                assert(source.capacity() == 0);
                for (std::size_t i = 0; i < destination.size(); ++i) {
                    assert(destination[i].value == static_cast<int>(i + 10));
                }
                assert(Counted::constructions == previous_constructions);
                assert(Counted::copies == 0);
                assert(Counted::moves == 0);
                assert(Counted::destructions == static_cast<int>(destination_size));
            }
            assert(Counted::constructions == Counted::destructions);
        }
    }
}

void test_move_assignment_self() {
    Counted::reset();
    {
        Vector<Counted> values(3);
        values.reserve(8);
        for (std::size_t i = 0; i < values.size(); ++i) {
            values[i].value = static_cast<int>(i + 10);
        }
        Counted* original_storage = &values[0];
        const int previous_constructions = Counted::constructions;
        const int previous_copies = Counted::copies;
        const int previous_moves = Counted::moves;
        const int previous_destructions = Counted::destructions;
        auto& alias = values;
        Vector<Counted>& result = (values = std::move(alias));
        assert(&result == &values);
        assert(values.size() == 3);
        assert(values.capacity() == 8);
        assert(&values[0] == original_storage);
        for (std::size_t i = 0; i < values.size(); ++i) {
            assert(values[i].value == static_cast<int>(i + 10));
        }
        assert(Counted::constructions == previous_constructions);
        assert(Counted::copies == previous_copies);
        assert(Counted::moves == previous_moves);
        assert(Counted::destructions == previous_destructions);
    }
    assert(Counted::constructions == Counted::destructions);
}

void test_move_assignment_move_only_elements() {
    struct MoveOnly : Counted {
        explicit MoveOnly(int initial_value) : Counted(initial_value) {}
        MoveOnly(const MoveOnly&) = delete;
        MoveOnly(MoveOnly&&) noexcept = default;
    };

    Counted::reset();
    {
        Vector<MoveOnly> source;
        source.emplace_back(42);
        MoveOnly* original_storage = &source[0];
        Vector<MoveOnly> destination;
        destination.emplace_back(7);
        Vector<MoveOnly>& result = (destination = std::move(source));
        assert(&result == &destination);
        assert(source.size() == 0);
        assert(source.capacity() == 0);
        assert(destination.size() == 1);
        assert(destination.capacity() == 1);
        assert(&destination[0] == original_storage);
        assert(destination[0].value == 42);
        assert(Counted::constructions == 2);
        assert(Counted::copies == 0);
        assert(Counted::moves == 0);
        assert(Counted::destructions == 1);
    }
    assert(Counted::constructions == Counted::destructions);
}

void test_pop_back_retains_storage() {
    Counted::reset();
    {
        Vector<Counted> values(3);
        values.reserve(8);
        for (std::size_t i = 0; i < values.size(); ++i) {
            values[i].value = static_cast<int>(i + 10);
        }
        Counted* original_storage = &values[0];
        const int previous_constructions = Counted::constructions;
        const int previous_copies = Counted::copies;
        const int previous_moves = Counted::moves;
        const int previous_destructions = Counted::destructions;

        values.pop_back();
        assert(values.size() == 2);
        assert(values.capacity() == 8);
        assert(values[0].value == 10);
        assert(values[1].value == 11);
        assert(Counted::destructions == previous_destructions + 1);
        values.pop_back();
        assert(values.size() == 1);
        assert(values[0].value == 10);
        values.pop_back();
        assert(values.size() == 0);
        assert(values.capacity() == 8);
        assert(Counted::constructions == previous_constructions);
        assert(Counted::copies == previous_copies);
        assert(Counted::moves == previous_moves);
        assert(Counted::destructions == previous_destructions + 3);

        Counted& added = values.emplace_back(99);
        assert(&added == original_storage);
        assert(values.size() == 1);
        assert(values.capacity() == 8);
        assert(values[0].value == 99);
        assert(Counted::constructions == previous_constructions + 1);
        assert(Counted::moves == previous_moves);
    }
    assert(Counted::constructions == Counted::destructions);
}

void test_clear_retains_storage() {
    Counted::reset();
    {
        Vector<Counted> values(3);
        values.reserve(8);
        Counted* original_storage = &values[0];
        const int previous_constructions = Counted::constructions;
        const int previous_copies = Counted::copies;
        const int previous_moves = Counted::moves;
        const int previous_destructions = Counted::destructions;
        values.clear();
        assert(values.size() == 0);
        assert(values.capacity() == 8);
        assert(Counted::constructions == previous_constructions);
        assert(Counted::copies == previous_copies);
        assert(Counted::moves == previous_moves);
        assert(Counted::destructions == previous_destructions + 3);

        Counted& added = values.emplace_back(99);
        assert(&added == original_storage);
        assert(values.size() == 1);
        assert(values.capacity() == 8);
        assert(values[0].value == 99);
        assert(Counted::constructions == previous_constructions + 1);
        assert(Counted::copies == previous_copies);
        assert(Counted::moves == previous_moves);
    }
    assert(Counted::constructions == Counted::destructions);
}

void test_clear_empty_and_repeated() {
    Counted::reset();
    {
        Vector<Counted> empty;
        empty.clear();
        empty.clear();
        assert(empty.size() == 0);
        assert(empty.capacity() == 0);

        Vector<Counted> reserved;
        reserved.reserve(8);
        reserved.clear();
        assert(reserved.size() == 0);
        assert(reserved.capacity() == 8);

        Vector<Counted> values(3);
        values.clear();
        assert(Counted::constructions == 3);
        assert(Counted::destructions == 3);
        values.clear();
        assert(values.size() == 0);
        assert(values.capacity() == 3);
        assert(Counted::destructions == 3);
    }
    assert(Counted::constructions == Counted::destructions);
}

void test_iterator_boundaries_and_const_access() {
    static_assert(std::is_same_v<decltype(std::declval<Vector<Counted>&>().begin()), Counted*>);
    static_assert(std::is_same_v<decltype(std::declval<Vector<Counted>&>().end()), Counted*>);
    static_assert(std::is_same_v<decltype(std::declval<const Vector<Counted>&>().begin()), const Counted*>);
    static_assert(std::is_same_v<decltype(std::declval<const Vector<Counted>&>().end()), const Counted*>);
    static_assert(noexcept(std::declval<Vector<Counted>&>().begin()));
    static_assert(noexcept(std::declval<Vector<Counted>&>().end()));
    static_assert(noexcept(std::declval<const Vector<Counted>&>().begin()));
    static_assert(noexcept(std::declval<const Vector<Counted>&>().end()));

    Counted::reset();
    {
        Vector<Counted> values(3);
        values.reserve(8);
        Counted* original_storage = values.begin();
        assert(values.begin() == &values[0]);
        assert(values.end() == values.begin() + 3);
        const int previous_constructions = Counted::constructions;
        const int previous_copies = Counted::copies;
        const int previous_moves = Counted::moves;
        int visited = 0;
        for (auto& item : values) {
            item.value = ++visited;
        }
        assert(visited == 3);
        const auto& view = values;
        assert(view.begin() == values.begin());
        assert(view.end() == values.end());
        int sum = 0;
        for (const auto& item : view) {
            sum += item.value;
        }
        assert(sum == 6);
        assert(Counted::constructions == previous_constructions);
        assert(Counted::copies == previous_copies);
        assert(Counted::moves == previous_moves);

        values.pop_back();
        assert(values.end() == original_storage + 2);
        assert(view.end() == original_storage + 2);
        values.clear();
        assert(values.begin() == original_storage);
        assert(values.begin() == values.end());
        assert(view.begin() == view.end());
        assert(values.capacity() == 8);
    }
    assert(Counted::constructions == Counted::destructions);
}

void test_iterators_empty_and_moved_from() {
    Counted::reset();
    {
        Vector<Counted> empty;
        const auto& empty_view = empty;
        assert(empty.begin() == nullptr);
        assert(empty.end() == nullptr);
        assert(empty_view.begin() == nullptr);
        assert(empty_view.end() == nullptr);
        int visited = 0;
        for (const auto& item : empty) {
            (void)item;
            ++visited;
        }
        assert(visited == 0);

        Vector<Counted> reserved;
        reserved.reserve(8);
        Counted* original_storage = reserved.begin();
        assert(original_storage != nullptr);
        assert(reserved.begin() == reserved.end());
        const auto& reserved_view = reserved;
        assert(reserved_view.begin() == reserved_view.end());
        Vector<Counted> moved(std::move(reserved));
        assert(reserved.begin() == nullptr);
        assert(reserved.end() == nullptr);
        assert(reserved_view.begin() == nullptr);
        assert(reserved_view.end() == nullptr);
        assert(moved.begin() == original_storage);
        assert(moved.end() == original_storage);
        assert(moved.capacity() == 8);
        assert(Counted::constructions == 0);
        assert(Counted::copies == 0);
        assert(Counted::moves == 0);
        moved.emplace_back(42);
        moved.clear();
        assert(moved.begin() == original_storage);
        assert(moved.end() == original_storage);
        assert(moved.capacity() == 8);
    }
    assert(Counted::constructions == Counted::destructions);
}

void test_first_emplace_failure_strong_guarantee() {
    ThrowingCounted::reset(1);
    {
        Vector<ThrowingCounted> values;
        bool threw = false;
        try {
            values.emplace_back();
        } catch (const ConstructionFailure&) {
            threw = true;
        }
        assert(threw);
        assert(values.size() == 0);
        assert(values.capacity() == 0);
        assert(values.begin() == nullptr);
        assert(values.begin() == values.end());
        assert(ThrowingCounted::constructions == 0);
        assert(ThrowingCounted::destructions == 0);
        values.emplace_back();
        assert(values.size() == 1);
        assert(values.capacity() == 1);
        assert(ThrowingCounted::constructions == 1);
    }
    assert(ThrowingCounted::constructions == ThrowingCounted::destructions);
}

int main(int argc, char* argv[]) {
    struct Test {
        const char* name;
        void (*run)();
    };
    const Test tests[] = {
        {"empty_vector", test_empty_vector},
        {"zero_size_constructor", test_zero_size_constructor},
        {"size_constructor", test_size_constructor},
        {"partial_construction_cleanup", test_partial_construction_cleanup},
        {"index_access_and_value_initialization", test_index_access_and_value_initialization},
        {"reserve_empty", test_reserve_empty},
        {"reserve_moves_existing_elements", test_reserve_moves_existing_elements},
        {"reserve_smaller_capacity", test_reserve_smaller_capacity},
        {"reserve_copy_fallback", test_reserve_copy_fallback},
        {"reserve_equal_capacity", test_reserve_equal_capacity},
        {"reserve_exception_cleanup", test_reserve_exception_cleanup},
        {"emplace_with_spare_capacity", test_emplace_with_spare_capacity},
        {"emplace_growth", test_emplace_growth},
        {"emplace_constructor_failure", test_emplace_constructor_failure},
        {"emplace_alias_during_growth", test_emplace_alias_during_growth},
        {"emplace_growth_constructor_failure", test_emplace_growth_constructor_failure},
        {"emplace_growth_exception_cleanup", test_emplace_growth_exception_cleanup},
        {"push_back_lvalue", test_push_back_lvalue},
        {"push_back_rvalue", test_push_back_rvalue},
        {"push_back_temporary", test_push_back_temporary},
        {"push_back_const_rvalue_copies", test_push_back_const_rvalue_copies},
        {"push_back_growth", test_push_back_growth},
        {"push_back_alias_during_growth", test_push_back_alias_during_growth},
        {"forwarding_and_move_only_elements", test_forwarding_and_move_only_elements},
        {"copy_constructor_independent_storage", test_copy_constructor_independent_storage},
        {"copy_constructor_empty", test_copy_constructor_empty},
        {"copy_constructor_exception_cleanup", test_copy_constructor_exception_cleanup},
        {"copy_constructor_non_default_elements", test_copy_constructor_non_default_elements},
        {"move_constructor_transfers_buffer", test_move_constructor_transfers_buffer},
        {"move_constructor_outlives_source", test_move_constructor_outlives_source},
        {"move_constructor_empty", test_move_constructor_empty},
        {"move_constructor_move_only_elements", test_move_constructor_move_only_elements},
        {"copy_assignment_replaces_contents", test_copy_assignment_replaces_contents},
        {"copy_assignment_empty_cases", test_copy_assignment_empty_cases},
        {"copy_assignment_self", test_copy_assignment_self},
        {"copy_assignment_strong_guarantee", test_copy_assignment_strong_guarantee},
        {"move_assignment_transfers_buffer", test_move_assignment_transfers_buffer},
        {"move_assignment_empty_cases", test_move_assignment_empty_cases},
        {"move_assignment_self", test_move_assignment_self},
        {"move_assignment_move_only_elements", test_move_assignment_move_only_elements},
        {"pop_back_retains_storage", test_pop_back_retains_storage},
        {"clear_retains_storage", test_clear_retains_storage},
        {"clear_empty_and_repeated", test_clear_empty_and_repeated},
        {"iterator_boundaries_and_const_access", test_iterator_boundaries_and_const_access},
        {"iterators_empty_and_moved_from", test_iterators_empty_and_moved_from},
        {"first_emplace_failure_strong_guarantee", test_first_emplace_failure_strong_guarantee},
    };

    int ran = 0;
    for (const auto& test : tests) {
        if (argc > 1 && std::string_view(argv[1]) != test.name) {
            continue;
        }
        test.run();
        ++ran;
        std::cout << "PASS: " << test.name << std::endl;
    }
    if (ran == 0) {
        std::cerr << "No matching test\n";
        return 1;
    }
    std::cout << "PASS: " << ran << " tests\n";
}
