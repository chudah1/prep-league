#include <array>
#include <atomic>
#include <cstddef>
#include <cstdlib>
#include <functional>
#include <iostream>
#include <map>
#include <new>
#include <string>
#include <string_view>
#include <utility>
#include <vector>

std::atomic<std::size_t> allocation_count{0};

void* operator new(std::size_t size) {
    allocation_count.fetch_add(1, std::memory_order_relaxed);
    size = size == 0 ? 1 : size;
    if (void* memory = std::malloc(size)) {
        return memory;
    }
    throw std::bad_alloc{};
}

void operator delete(void* pointer) noexcept {
    std::free(pointer);
}

void operator delete(void* pointer, std::size_t) noexcept {
    std::free(pointer);
}

struct Tracer {
    static inline std::size_t defaults = 0;
    static inline std::size_t copies = 0;
    static inline std::size_t moves = 0;

    Tracer() { ++defaults; }
    Tracer(const Tracer&) { ++copies; }
    Tracer(Tracer&&) noexcept { ++moves; }

    static void reset() {
        defaults = 0;
        copies = 0;
        moves = 0;
    }
};

struct Counts {
    std::size_t allocations;
    std::size_t defaults;
    std::size_t copies;
    std::size_t moves;
};

struct LargeCapture {
    Tracer tracer;
    std::array<int, 1000> values{};
};

void reset_counts() {
    allocation_count.store(0, std::memory_order_relaxed);
    Tracer::reset();
}

Counts snapshot_counts() {
    return {allocation_count.load(std::memory_order_relaxed), Tracer::defaults,
            Tracer::copies, Tracer::moves};
}

void print_counts(std::string_view label, Counts counts) {
    std::cout << label << ": allocations=" << counts.allocations
              << ", defaults=" << counts.defaults
              << ", copies=" << counts.copies
              << ", moves=" << counts.moves << '\n';
}

Tracer return_local() {
    Tracer local;
    return local;
}

Tracer choose_tracer(bool choose_first) {
    Tracer first;
    Tracer second;
    return choose_first ? first : second;
}

Counts snippet_1_return_local() {
    reset_counts();
    [[maybe_unused]] Tracer result = return_local();
    return snapshot_counts();
}

Counts snippet_2_return_ternary() {
    reset_counts();
    [[maybe_unused]] Tracer result = choose_tracer(true);
    return snapshot_counts();
}

Counts snippet_3a_push_temporary() {
    reset_counts();
    std::vector<Tracer> values;
    values.push_back(Tracer{});
    return snapshot_counts();
}

Counts snippet_3b_emplace_temporary() {
    reset_counts();
    std::vector<Tracer> values;
    values.emplace_back(Tracer{});
    return snapshot_counts();
}

Counts snippet_4_vector_growth() {
    reset_counts();
    std::vector<Tracer> values;
    for (int i = 0; i < 17; ++i) {
        values.emplace_back();
    }
    return snapshot_counts();
}

Counts snippet_5a_short_string() {
    reset_counts();
    [[maybe_unused]] std::string text = "hello";
    return snapshot_counts();
}

Counts snippet_5b_long_string() {
    reset_counts();
    [[maybe_unused]] std::string text(100, 'x');
    return snapshot_counts();
}

Counts snippet_6a_large_lambda() {
    LargeCapture captured;
    reset_counts();
    [[maybe_unused]] std::function<int()> function =
        [captured]() { return captured.values[0]; };
    return snapshot_counts();
}

Counts snippet_6b_small_lambda() {
    int number = 10;
    reset_counts();
    [[maybe_unused]] std::function<int()> function = [number]() { return number; };
    return snapshot_counts();
}

Counts snippet_7_move_const() {
    const Tracer source;
    reset_counts();
    [[maybe_unused]] Tracer destination = std::move(source);
    return snapshot_counts();
}

Counts snippet_8a_range_by_value() {
    std::array<Tracer, 3> values{};
    reset_counts();
    for (auto value : values) {
        (void)value;
    }
    return snapshot_counts();
}

Counts snippet_8b_range_by_reference() {
    std::array<Tracer, 3> values{};
    reset_counts();
    for (const auto& value : values) {
        (void)value;
    }
    return snapshot_counts();
}

Counts snippet_9_initializer_list() {
    reset_counts();
    [[maybe_unused]] std::vector<std::string> names{"chat", "gpt"};
    return snapshot_counts();
}

Counts snippet_10_map_missing_key() {
    std::map<std::string, Tracer> records;
    reset_counts();
    (void)records["missing"];
    return snapshot_counts();
}

int main() {
    print_counts("1. return local", snippet_1_return_local());
    print_counts("2. return ternary", snippet_2_return_ternary());
    print_counts("3a. push_back temporary", snippet_3a_push_temporary());
    print_counts("3b. emplace_back temporary", snippet_3b_emplace_temporary());
    print_counts("4. growth to 17", snippet_4_vector_growth());
    print_counts("5a. short string", snippet_5a_short_string());
    print_counts("5b. long string", snippet_5b_long_string());
    print_counts("6a. large lambda", snippet_6a_large_lambda());
    print_counts("6b. small lambda", snippet_6b_small_lambda());
    print_counts("7. move const object", snippet_7_move_const());
    print_counts("8a. range by value", snippet_8a_range_by_value());
    print_counts("8b. range by const reference", snippet_8b_range_by_reference());
    print_counts("9. vector<string> initializer list", snippet_9_initializer_list());
    print_counts("10. map missing key", snippet_10_map_missing_key());
}
