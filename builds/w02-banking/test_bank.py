"""Specification examples and regression tests for the four banking levels."""

import pytest

from bank import Bank


EXAMPLE_STEPS = [
    (1, "create_account", (1, "a"), True),
    (1, "create_account", (2, "a"), False),
    (1, "create_account", (3, "b"), True),
    (1, "deposit", (4, "a", 500), 500),
    (1, "transfer", (6, "a", "b", 200), 300),
    (1, "transfer", (7, "b", "a", 201), None),
    (1, "transfer", (8, "b", "c", 10), None),
    (1, "transfer", (9, "a", "a", 10), None),
    (2, "top_spenders", (10, 2), ["a(200)", "b(0)"]),
    (2, "create_account", (11, "c"), True),
    (2, "transfer", (12, "b", "c", 200), 0),
    (2, "top_spenders", (13, 3), ["a(200)", "b(200)", "c(0)"]),
    (2, "top_spenders", (14, 10), ["a(200)", "b(200)", "c(0)"]),
    (2, "top_spenders", (15, 1), ["a(200)"]),
    (3, "schedule_payment", (16, "a", 100, 4), "payment1"),
    (3, "schedule_payment", (17, "b", 50, 3), "payment2"),
    (3, "cancel_payment", (19, "b", "payment1"), False),
    (3, "deposit", (20, "a", 50), 250),
    (3, "top_spenders", (21, 3), ["a(300)", "b(200)", "c(0)"]),
    (3, "cancel_payment", (22, "a", "payment1"), False),
    (3, "schedule_payment", (23, "c", 10, 5), "payment3"),
    (3, "cancel_payment", (24, "c", "payment3"), True),
    (4, "schedule_payment", (25, "c", 40, 10), "payment4"),
    (4, "merge_accounts", (26, "a", "c"), True),
    (4, "merge_accounts", (27, "a", "a"), False),
    (4, "get_balance", (28, "c", 27), None),
    (4, "get_balance", (29, "c", 12), 200),
    (4, "get_balance", (30, "a", 5), 500),
    (4, "deposit", (35, "a", 10), 420),
    (4, "get_balance", (36, "a", 26), 450),
]


@pytest.fixture
def bank():
    return Bank()


@pytest.fixture
def funded_bank(bank):
    bank.create_account(1, "a")
    bank.create_account(2, "b")
    bank.deposit(3, "a", 100)
    return bank


@pytest.mark.parametrize(
    "row_index",
    [
        pytest.param(index, id=f"level-{level}-{method}-{args[0]}")
        for index, (level, method, args, _) in enumerate(EXAMPLE_STEPS)
    ],
)
def test_example_row(bank, row_index):
    """Replay earlier rows because each level continues the previous state."""
    for _, method, args, expected in EXAMPLE_STEPS[: row_index + 1]:
        actual = getattr(bank, method)(*args)
        assert actual == expected, f"{method}{args}"
        assert type(actual) is type(expected), f"Return type for {method}{args}"


@pytest.mark.parametrize(
    "source,target,amount",
    [
        ("missing", "b", 10),
        ("a", "missing", 10),
        ("a", "a", 10),
        ("a", "b", 101),
    ],
)
def test_failed_transfer_changes_neither_balance_nor_outgoing_total(
    funded_bank, source, target, amount
):
    bank = funded_bank
    assert bank.transfer(4, source, target, amount) is None
    assert bank.get_balance(5, "a", 4) == 100
    assert bank.get_balance(6, "b", 4) == 0
    assert bank.top_spenders(7, 2) == ["a(0)", "b(0)"]


def test_deposits_persist_and_missing_accounts_are_not_created(bank):
    assert bank.deposit(1, "missing", 10) is None
    assert bank.create_account(2, "a") is True
    assert bank.deposit(3, "a", 500) == 500
    assert bank.deposit(4, "a", 10) == 510
    assert bank.get_balance(5, "a", 4) == 510


def test_whole_balance_transfer_is_allowed(funded_bank):
    bank = funded_bank
    assert bank.transfer(4, "a", "b", 100) == 0
    assert bank.get_balance(5, "a", 4) == 0
    assert bank.get_balance(6, "b", 4) == 100
    assert bank.top_spenders(7, 2) == ["a(100)", "b(0)"]


def test_large_balances_remain_exact_integers(bank):
    amount = 2**60 + 1
    bank.create_account(1, "a")
    bank.create_account(2, "b")
    balance = bank.deposit(3, "a", amount)
    assert type(balance) is int
    assert balance == amount
    assert bank.transfer(4, "a", "b", amount) == 0
    balance = bank.get_balance(5, "b", 4)
    assert type(balance) is int
    assert balance == amount


@pytest.mark.parametrize("n", [-1, 0, 1, 10])
def test_top_spenders_on_an_empty_bank(bank, n):
    assert bank.top_spenders(1, n) == []


@pytest.mark.parametrize("n", [-2, 0])
def test_top_spenders_with_nonpositive_n(funded_bank, n):
    assert funded_bank.top_spenders(4, n) == []


def test_zero_spenders_are_sorted_by_id(bank):
    bank.create_account(1, "c")
    bank.create_account(2, "b")
    bank.create_account(3, "a")
    assert bank.top_spenders(4, 2) == ["a(0)", "b(0)"]
    assert bank.top_spenders(5, 10) == ["a(0)", "b(0)", "c(0)"]


def test_higher_outgoing_total_ranks_first(funded_bank):
    bank = funded_bank
    bank.create_account(4, "c")
    bank.deposit(5, "b", 100)
    bank.transfer(6, "a", "c", 20)
    bank.transfer(7, "b", "c", 60)
    assert bank.top_spenders(8, 2) == ["b(60)", "a(20)"]
    assert bank.top_spenders(9, 10) == ["b(60)", "a(20)", "c(0)"]


def test_payment_ids_are_global_and_never_reused(funded_bank):
    bank = funded_bank
    assert bank.schedule_payment(4, "missing", 10, 1) is None
    assert bank.schedule_payment(5, "a", 10, 1) == "payment1"
    assert bank.schedule_payment(6, "b", 10, 100) == "payment2"
    assert bank.cancel_payment(7, "b", "payment2") is True
    assert bank.schedule_payment(8, "a", 10, 100) == "payment3"
    assert bank.cancel_payment(9, "a", "payment1") is False
    assert bank.get_balance(10, "a", 6) == 90


def test_scheduling_neither_requires_nor_reserves_funds(bank):
    bank.create_account(1, "a")
    bank.create_account(2, "b")
    assert bank.schedule_payment(3, "a", 80, 20) == "payment1"
    assert bank.deposit(4, "a", 100) == 100
    assert bank.transfer(5, "a", "b", 100) == 0
    assert bank.top_spenders(24, 2) == ["a(100)", "b(0)"]
    assert bank.get_balance(25, "a", 23) == 0


def test_skipped_payment_is_never_retried(bank):
    bank.create_account(1, "a")
    bank.schedule_payment(2, "a", 50, 1)
    assert bank.deposit(3, "a", 50) == 50
    assert bank.cancel_payment(4, "a", "payment1") is False
    assert bank.deposit(5, "a", 1) == 51
    assert bank.top_spenders(6, 1) == ["a(0)"]
    assert bank.get_balance(7, "a", 3) == 50


def test_cancelled_payment_cannot_run_or_be_cancelled_again(funded_bank):
    bank = funded_bank
    bank.schedule_payment(4, "a", 30, 6)
    assert bank.cancel_payment(5, "b", "payment1") is False
    assert bank.cancel_payment(6, "a", "payment1") is True
    assert bank.cancel_payment(7, "a", "payment1") is False
    assert bank.cancel_payment(8, "a", "unknown") is False
    assert bank.top_spenders(10, 2) == ["a(0)", "b(0)"]
    assert bank.get_balance(11, "a", 10) == 100


@pytest.mark.parametrize("balance", [0, 50, 100])
def test_cancellation_at_due_time_fails_even_when_payment_is_skipped(bank, balance):
    bank.create_account(1, "a")
    if balance:
        bank.deposit(2, "a", balance)
    bank.schedule_payment(3, "a", 50, 2)
    assert bank.cancel_payment(5, "a", "payment1") is False
    withdrawn = 50 if balance >= 50 else 0
    assert bank.get_balance(6, "a", 5) == balance - withdrawn
    assert bank.top_spenders(7, 1) == [f"a({withdrawn})"]


@pytest.mark.parametrize(
    "method,args,expected",
    [
        ("create_account", (5, "a"), False),
        ("deposit", (5, "missing", 1), None),
        ("transfer", (5, "a", "b", 50), None),
        ("top_spenders", (5, 0), []),
        ("schedule_payment", (5, "missing", 1, 1), None),
        ("cancel_payment", (5, "a", "payment1"), False),
        ("merge_accounts", (5, "a", "a"), False),
        ("get_balance", (5, "missing", 4), None),
    ],
    ids=["create", "deposit", "transfer", "rank", "schedule", "cancel", "merge", "history"],
)
def test_every_public_operation_processes_due_payments_before_early_return(
    funded_bank, method, args, expected
):
    bank = funded_bank
    bank.schedule_payment(4, "a", 80, 1)
    assert getattr(bank, method)(*args) == expected
    # Inspect immediately: another public call would itself process payments,
    # potentially hiding the original operation's failure to do so.
    assert bank.bank["a"].amount == 20
    assert bank.bank["b"].amount == 0
    assert bank.transfers["a"] == 80


def test_payments_run_by_due_time_before_creation_order(bank):
    bank.create_account(1, "a")
    bank.deposit(2, "a", 100)
    bank.schedule_payment(3, "a", 70, 7)
    bank.schedule_payment(4, "a", 50, 1)
    assert bank.top_spenders(11, 1) == ["a(50)"]
    assert bank.get_balance(12, "a", 5) == 50
    assert bank.get_balance(13, "a", 10) == 50


def test_same_due_time_uses_numeric_payment_order(bank):
    bank.create_account(1, "a")
    bank.deposit(2, "a", 20)
    for number in range(1, 11):
        timestamp = number + 2
        amount = 100 if number <= 8 else (10 if number == 9 else 20)
        assert bank.schedule_payment(timestamp, "a", amount, 20 - timestamp) == (
            f"payment{number}"
        )
    assert bank.top_spenders(20, 1) == ["a(10)"]
    assert bank.get_balance(21, "a", 20) == 10
    assert bank.cancel_payment(22, "a", "payment10") is False


def test_skipping_one_payment_does_not_block_an_affordable_payment(bank):
    bank.create_account(1, "a")
    bank.deposit(2, "a", 40)
    bank.schedule_payment(3, "a", 50, 3)
    bank.schedule_payment(4, "a", 30, 2)
    assert bank.top_spenders(6, 1) == ["a(30)"]
    assert bank.get_balance(7, "a", 6) == 10


def test_merge_combines_balances_and_outgoing_but_preserves_earlier_history(bank):
    bank.create_account(1, "a")
    bank.create_account(2, "b")
    bank.create_account(3, "c")
    bank.deposit(4, "a", 100)
    bank.deposit(5, "b", 80)
    bank.transfer(6, "a", "b", 20)
    bank.transfer(7, "b", "c", 30)
    assert bank.merge_accounts(8, "a", "b") is True
    assert bank.top_spenders(9, 10) == ["a(50)", "c(0)"]
    assert bank.get_balance(10, "a", 7) == 80
    assert bank.get_balance(11, "a", 8) == 150
    assert bank.get_balance(12, "b", 7) == 70
    assert bank.get_balance(13, "b", 8) is None
    assert bank.get_balance(14, "c", 8) == 30


@pytest.mark.parametrize(
    "target,source", [("a", "a"), ("a", "missing"), ("missing", "a")]
)
def test_invalid_merge_leaves_accounts_unchanged(funded_bank, target, source):
    bank = funded_bank
    assert bank.merge_accounts(4, target, source) is False
    assert bank.get_balance(5, "a", 4) == 100
    assert bank.get_balance(6, "b", 4) == 0
    assert bank.top_spenders(7, 2) == ["a(0)", "b(0)"]


def test_merged_accounts_behave_as_missing_for_current_operations(funded_bank):
    bank = funded_bank
    assert bank.merge_accounts(4, "a", "b") is True
    assert bank.deposit(5, "b", 1) is None
    assert bank.transfer(6, "b", "a", 1) is None
    assert bank.transfer(7, "a", "b", 1) is None
    assert bank.schedule_payment(8, "b", 1, 1) is None
    assert bank.merge_accounts(9, "a", "b") is False
    assert bank.top_spenders(10, 10) == ["a(0)"]


def test_merge_transfers_payment_cancellation_and_execution_to_survivor(bank):
    bank.create_account(1, "a")
    bank.create_account(2, "b")
    bank.deposit(3, "a", 100)
    bank.deposit(4, "b", 50)
    bank.schedule_payment(5, "b", 40, 5)
    bank.schedule_payment(6, "b", 10, 5)
    assert bank.merge_accounts(7, "a", "b") is True
    assert bank.cancel_payment(8, "b", "payment1") is False
    assert bank.cancel_payment(9, "a", "payment1") is True
    assert bank.top_spenders(10, 10) == ["a(0)"]
    assert bank.top_spenders(11, 10) == ["a(10)"]
    assert bank.get_balance(12, "a", 11) == 140
    assert bank.get_balance(13, "b", 6) == 50
    assert bank.get_balance(14, "b", 7) is None


def test_pending_payments_follow_chained_merges(bank):
    bank.create_account(1, "a")
    bank.create_account(2, "b")
    bank.create_account(3, "c")
    bank.deposit(4, "c", 100)
    bank.schedule_payment(5, "c", 20, 10)
    assert bank.merge_accounts(6, "b", "c") is True
    assert bank.merge_accounts(7, "a", "b") is True
    assert bank.top_spenders(15, 10) == ["a(20)"]
    assert bank.get_balance(16, "c", 5) == 100
    assert bank.get_balance(17, "c", 6) is None
    assert bank.get_balance(18, "b", 6) == 100
    assert bank.get_balance(19, "b", 7) is None
    assert bank.get_balance(20, "a", 6) == 0
    assert bank.get_balance(21, "a", 7) == 100
    assert bank.get_balance(22, "a", 15) == 80


@pytest.mark.parametrize("source_balance", [10, 30])
def test_payment_due_at_merge_runs_before_balances_combine(bank, source_balance):
    bank.create_account(1, "a")
    bank.create_account(2, "b")
    bank.deposit(3, "a", 100)
    bank.deposit(4, "b", source_balance)
    bank.schedule_payment(5, "b", 20, 1)
    assert bank.merge_accounts(6, "a", "b") is True
    withdrawn = 20 if source_balance >= 20 else 0
    assert bank.get_balance(7, "a", 6) == 100 + source_balance - withdrawn
    assert bank.get_balance(8, "b", 6) is None
    assert bank.get_balance(9, "b", 5) == source_balance
    assert bank.top_spenders(10, 10) == [f"a({withdrawn})"]


def test_history_handles_creation_boundaries_and_missing_accounts(bank):
    bank.create_account(10, "a")
    assert bank.get_balance(11, "a", 9) is None
    assert bank.get_balance(12, "a", 10) == 0
    assert bank.get_balance(13, "missing", 10) is None
    assert bank.deposit(14, "a", 100) == 100
    assert bank.create_account(15, "a") is False
    assert bank.get_balance(16, "a", 15) == 100


def test_late_payment_processing_records_due_time_not_processing_time(bank):
    bank.create_account(1, "a")
    bank.deposit(2, "a", 100)
    bank.schedule_payment(3, "a", 40, 7)
    assert bank.deposit(20, "a", 10) == 70
    assert bank.get_balance(21, "a", 9) == 100
    assert bank.get_balance(22, "a", 10) == 60
    assert bank.get_balance(23, "a", 19) == 60
    assert bank.get_balance(24, "a", 20) == 70


def test_history_at_one_timestamp_includes_all_payments_and_the_operation(bank):
    bank.create_account(1, "a")
    bank.deposit(2, "a", 100)
    bank.schedule_payment(3, "a", 30, 7)
    bank.schedule_payment(4, "a", 20, 6)
    assert bank.deposit(10, "a", 10) == 60
    assert bank.get_balance(11, "a", 10) == 60
    assert bank.get_balance(12, "a", 9) == 100


def test_recreated_account_preserves_earlier_history_and_absence_gap(bank):
    bank.create_account(1, "a")
    bank.create_account(2, "b")
    bank.deposit(3, "b", 100)
    bank.schedule_payment(4, "b", 20, 6)
    assert bank.merge_accounts(5, "a", "b") is True
    assert bank.get_balance(6, "b", 3) == 100
    assert bank.get_balance(7, "b", 5) is None
    assert bank.create_account(8, "b") is True
    assert bank.get_balance(9, "b", 7) is None
    assert bank.get_balance(10, "a", 10) == 80
    assert bank.get_balance(11, "b", 8) == 0
    assert bank.get_balance(12, "b", 3) == 100
    assert bank.top_spenders(13, 10) == ["a(20)", "b(0)"]
