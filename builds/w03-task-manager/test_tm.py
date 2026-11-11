import pytest

from tm import TaskManager


@pytest.fixture
def manager():
    return TaskManager()


def test_level_1_example(manager):
    """The exact sequence from the Level 1 example table."""
    assert manager.add_task(1, "docs", 5) == "task_1"
    assert manager.add_task(2, "docs v2", 7) == "task_2"
    assert manager.add_task(3, "tests", 7) == "task_3"
    assert manager.get_task(4, "task_1") == {"name": "docs", "priority": 5}
    assert manager.update_task(5, "task_9", "x", 1) is False
    assert manager.update_task(6, "task_1", "docs v1", 5) is True
    assert manager.get_task(7, "task_1") == {"name": "docs v1", "priority": 5}
    assert manager.get_task(8, "task_4") is None


def test_get_from_empty_manager(manager):
    assert manager.get_task(1, "task_1") is None


def test_get_unknown_task_when_other_tasks_exist(manager):
    manager.add_task(1, "docs", 5)
    assert manager.get_task(2, "task_999") is None
    assert manager.get_task(3, "task_1") == {"name": "docs", "priority": 5}


def test_ids_follow_creation_order_past_nine(manager):
    for number in range(1, 13):
        assert manager.add_task(number, f"job {number}", number) == f"task_{number}"

    for number in range(1, 13):
        assert manager.get_task(12 + number, f"task_{number}") == {
            "name": f"job {number}",
            "priority": number,
        }


def test_duplicate_names_create_separate_tasks(manager):
    assert manager.add_task(1, "docs", 5) == "task_1"
    assert manager.add_task(2, "docs", 7) == "task_2"
    assert manager.get_task(3, "task_1") == {"name": "docs", "priority": 5}
    assert manager.get_task(4, "task_2") == {"name": "docs", "priority": 7}


@pytest.mark.parametrize("priority", [-7, 0, 100])
def test_stores_integer_priority_exactly(manager, priority):
    task_id = manager.add_task(1, "job", priority)
    assert manager.get_task(2, task_id) == {"name": "job", "priority": priority}


def test_update_replaces_both_name_and_priority(manager):
    task_id = manager.add_task(1, "old name", 5)
    assert manager.update_task(2, task_id, "new name", 9) is True
    assert manager.get_task(3, task_id) == {"name": "new name", "priority": 9}


def test_update_with_unchanged_values_succeeds(manager):
    task_id = manager.add_task(1, "docs", 5)
    assert manager.update_task(2, task_id, "docs", 5) is True
    assert manager.get_task(3, task_id) == {"name": "docs", "priority": 5}


def test_repeated_updates_keep_latest_values(manager):
    task_id = manager.add_task(1, "first", 5)
    assert manager.update_task(2, task_id, "second", 10) is True
    assert manager.update_task(3, task_id, "third", 0) is True
    assert manager.get_task(4, task_id) == {"name": "third", "priority": 0}


def test_update_unknown_task_does_not_create_it(manager):
    assert manager.update_task(1, "task_9", "missing", 10) is False
    assert manager.get_task(2, "task_9") is None
    assert manager.add_task(3, "first real task", 1) == "task_1"


def test_failed_update_leaves_existing_task_unchanged(manager):
    manager.add_task(1, "docs", 5)
    assert manager.update_task(2, "task_999", "changed", 99) is False
    assert manager.get_task(3, "task_1") == {"name": "docs", "priority": 5}


def test_updating_one_duplicate_name_does_not_change_the_other(manager):
    first = manager.add_task(1, "docs", 5)
    second = manager.add_task(2, "docs", 7)
    assert manager.update_task(3, first, "renamed", 99) is True
    assert manager.get_task(4, first) == {"name": "renamed", "priority": 99}
    assert manager.get_task(5, second) == {"name": "docs", "priority": 7}


def test_renaming_to_an_existing_name_keeps_both_tasks(manager):
    first = manager.add_task(1, "first", 1)
    second = manager.add_task(2, "second", 2)
    assert manager.update_task(3, first, "second", 3) is True
    assert manager.get_task(4, first) == {"name": "second", "priority": 3}
    assert manager.get_task(5, second) == {"name": "second", "priority": 2}


def test_reads_and_updates_do_not_consume_task_ids(manager):
    assert manager.add_task(1, "first", 1) == "task_1"
    assert manager.get_task(2, "task_1") == {"name": "first", "priority": 1}
    assert manager.update_task(3, "task_1", "updated", 2) is True
    assert manager.get_task(4, "task_999") is None
    assert manager.update_task(5, "task_999", "missing", 3) is False
    assert manager.add_task(6, "second", 4) == "task_2"


def test_managers_have_independent_tasks_and_id_counters():
    first = TaskManager()
    second = TaskManager()
    assert first.add_task(1, "first manager", 1) == "task_1"
    assert second.get_task(2, "task_1") is None
    assert second.add_task(3, "second manager", 2) == "task_1"
    assert first.get_task(4, "task_1") == {"name": "first manager", "priority": 1}
    assert second.get_task(5, "task_1") == {"name": "second manager", "priority": 2}


class TestLevel2:
    """Run just these tests with pytest -k TestLevel2."""

    def test_prompt_example(self, manager):
        manager.add_task(1, "docs", 5)
        manager.add_task(2, "docs v2", 7)
        manager.add_task(3, "tests", 7)
        assert manager.update_task(6, "task_1", "docs v1", 5) is True

        assert manager.search_tasks(9, "docs", 5) == ["task_2", "task_1"]
        assert manager.list_tasks_sorted(10, 10) == ["task_2", "task_3", "task_1"]
        assert manager.list_tasks_sorted(11, 2) == ["task_2", "task_3"]
        assert manager.search_tasks(12, "Docs", 5) == []
        assert manager.search_tasks(13, "s", 0) == []
        assert manager.search_tasks(14, "", 1) == ["task_2"]

    def test_empty_manager(self, manager):
        assert manager.list_tasks_sorted(1, 10) == []
        assert manager.search_tasks(2, "docs", 10) == []
        assert manager.search_tasks(3, "", 10) == []

    @pytest.mark.parametrize("k", [0, -1, -100])
    def test_nonpositive_limits(self, manager, k):
        manager.add_task(1, "docs", 5)
        manager.add_task(2, "tests", 7)
        assert manager.list_tasks_sorted(3, k) == []
        assert manager.search_tasks(4, "docs", k) == []
        assert manager.search_tasks(5, "", k) == []

    def test_priority_descending_with_zero_and_negative_priorities(self, manager):
        manager.add_task(1, "negative", -5)
        manager.add_task(2, "zero", 0)
        manager.add_task(3, "high first", 20)
        manager.add_task(4, "middle", 3)
        manager.add_task(5, "high second", 20)
        assert manager.list_tasks_sorted(6, 100) == [
            "task_3", "task_5", "task_4", "task_2", "task_1"
        ]

    def test_ties_use_numeric_id_not_lexicographic_id(self, manager):
        expected = []
        for number in range(1, 13):
            task_id = manager.add_task(number, f"job {number}", 7)
            expected.append(task_id)

        assert manager.list_tasks_sorted(13, 100) == expected
        assert manager.search_tasks(14, "job", 100) == expected
        assert manager.list_tasks_sorted(15, 3) == ["task_1", "task_2", "task_3"]
        assert manager.search_tasks(16, "job", 3) == ["task_1", "task_2", "task_3"]

    def test_search_is_case_sensitive_substring_not_prefix(self, manager):
        manager.add_task(1, "docs", 1)
        manager.add_task(2, "write docs now", 1)
        manager.add_task(3, "mydocs", 1)
        manager.add_task(4, "DOCS", 1)
        manager.add_task(5, "documentation", 1)
        assert manager.search_tasks(6, "docs", 100) == ["task_1", "task_2", "task_3"]
        assert manager.search_tasks(7, "DOCS", 100) == ["task_4"]
        assert manager.search_tasks(8, "Docs", 100) == []
        assert manager.search_tasks(9, "write", 100) == ["task_2"]

    def test_empty_filter_matches_all_in_sorted_order(self, manager):
        manager.add_task(1, "zebra", 1)
        manager.add_task(2, "apple", 9)
        manager.add_task(3, "middle", 5)
        assert manager.search_tasks(4, "", 10) == ["task_2", "task_3", "task_1"]
        assert manager.list_tasks_sorted(5, 10) == ["task_2", "task_3", "task_1"]

    def test_search_filters_before_applying_limit(self, manager):
        manager.add_task(1, "unrelated high priority", 100)
        manager.add_task(2, "docs low", 1)
        manager.add_task(3, "docs high", 10)
        manager.add_task(4, "docs middle", 5)
        assert manager.search_tasks(5, "docs", 1) == ["task_3"]
        assert manager.search_tasks(6, "docs", 2) == ["task_3", "task_4"]
        assert manager.search_tasks(7, "docs", 100) == ["task_3", "task_4", "task_2"]

    def test_duplicate_names_are_all_returned(self, manager):
        manager.add_task(1, "docs", 5)
        manager.add_task(2, "docs", 7)
        manager.add_task(3, "docs", 7)
        assert manager.search_tasks(4, "docs", 10) == ["task_2", "task_3", "task_1"]
        assert manager.list_tasks_sorted(5, 10) == ["task_2", "task_3", "task_1"]

    def test_update_immediately_changes_search_and_sort_results(self, manager):
        manager.add_task(1, "docs", 1)
        manager.add_task(2, "tests", 5)
        assert manager.list_tasks_sorted(3, 10) == ["task_2", "task_1"]
        assert manager.search_tasks(4, "docs", 10) == ["task_1"]

        assert manager.update_task(5, "task_1", "release", 10) is True
        assert manager.list_tasks_sorted(6, 10) == ["task_1", "task_2"]
        assert manager.search_tasks(7, "docs", 10) == []
        assert manager.search_tasks(8, "release", 10) == ["task_1"]

    def test_renaming_to_existing_name_keeps_both_search_results(self, manager):
        manager.add_task(1, "first", 1)
        manager.add_task(2, "docs", 2)
        assert manager.update_task(3, "task_1", "docs", 3) is True
        assert manager.search_tasks(4, "docs", 10) == ["task_1", "task_2"]
        assert manager.search_tasks(5, "first", 10) == []

    def test_limits_do_not_remove_tasks_or_consume_ids(self, manager):
        manager.add_task(1, "docs", 1)
        manager.add_task(2, "tests", 2)
        assert manager.list_tasks_sorted(3, 1) == ["task_2"]
        assert manager.search_tasks(4, "", 1) == ["task_2"]
        assert manager.search_tasks(5, "absent", 100) == []
        assert manager.list_tasks_sorted(6, 100) == ["task_2", "task_1"]
        assert manager.get_task(7, "task_1") == {"name": "docs", "priority": 1}
        assert manager.get_task(8, "task_2") == {"name": "tests", "priority": 2}
        assert manager.add_task(9, "new", 3) == "task_3"


class TestLevel3:
    """Dependency rules only; no users or timed assignments required."""

    def test_prompt_example(self, manager):
        manager.add_task(1, "docs", 5)
        manager.add_task(2, "docs v2", 7)
        manager.add_task(3, "tests", 7)
        assert manager.update_task(6, "task_1", "docs v1", 5) is True

        assert manager.add_dependency(15, "task_2", "task_1") is True
        assert manager.add_dependency(16, "task_1", "task_2") is False
        assert manager.add_dependency(17, "task_3", "task_3") is False
        assert manager.get_ready_tasks(18) == ["task_3", "task_1"]
        assert manager.complete_task(19, "task_2") is False
        assert manager.complete_task(20, "task_1") is True
        assert manager.get_ready_tasks(21) == ["task_2", "task_3"]
        assert manager.complete_task(22, "task_1") is False

    def test_empty_manager_and_missing_completion(self, manager):
        assert manager.get_ready_tasks(1) == []
        assert manager.complete_task(2, "task_999") is False
        assert manager.get_ready_tasks(3) == []

    def test_task_without_dependencies_can_complete_without_assignment(self, manager):
        task_id = manager.add_task(1, "docs", 5)
        assert manager.get_ready_tasks(2) == [task_id]
        assert manager.complete_task(3, task_id) is True
        assert manager.get_ready_tasks(4) == []
        assert manager.complete_task(5, task_id) is False

    @pytest.mark.parametrize(
        "task_id, depends_on",
        [("task_9", "task_1"), ("task_1", "task_9"), ("task_8", "task_9")],
    )
    def test_dependency_rejects_missing_tasks_without_changes(
        self, manager, task_id, depends_on
    ):
        manager.add_task(1, "exists", 5)
        assert manager.add_dependency(2, task_id, depends_on) is False
        assert manager.get_ready_tasks(3) == ["task_1"]
        assert manager.get_task(4, "task_9") is None
        assert manager.add_task(5, "new", 1) == "task_2"

    def test_self_dependency_is_rejected_without_changes(self, manager):
        task_id = manager.add_task(1, "docs", 5)
        assert manager.add_dependency(2, task_id, task_id) is False
        assert manager.get_ready_tasks(3) == [task_id]
        assert manager.complete_task(4, task_id) is True

    def test_duplicate_dependency_is_rejected(self, manager):
        manager.add_task(1, "dependent", 10)
        manager.add_task(2, "prerequisite", 1)
        assert manager.add_dependency(3, "task_1", "task_2") is True
        assert manager.add_dependency(4, "task_1", "task_2") is False
        assert manager.get_ready_tasks(5) == ["task_2"]
        assert manager.complete_task(6, "task_2") is True
        assert manager.get_ready_tasks(7) == ["task_1"]
        assert manager.complete_task(8, "task_1") is True

    def test_cannot_add_dependency_to_completed_task(self, manager):
        manager.add_task(1, "already done", 10)
        manager.add_task(2, "still open", 1)
        assert manager.complete_task(3, "task_1") is True
        assert manager.add_dependency(4, "task_1", "task_2") is False
        assert manager.get_ready_tasks(5) == ["task_2"]
        assert manager.complete_task(6, "task_1") is False

    def test_dependency_on_completed_task_is_allowed(self, manager):
        manager.add_task(1, "dependent", 10)
        manager.add_task(2, "prerequisite", 1)
        assert manager.complete_task(3, "task_2") is True
        assert manager.add_dependency(4, "task_1", "task_2") is True
        assert manager.get_ready_tasks(5) == ["task_1"]
        assert manager.complete_task(6, "task_1") is True

    def test_dependency_blocks_only_the_dependent_task(self, manager):
        manager.add_task(1, "dependent", 100)
        manager.add_task(2, "prerequisite", 1)
        assert manager.add_dependency(3, "task_1", "task_2") is True
        assert manager.get_ready_tasks(4) == ["task_2"]
        assert manager.complete_task(5, "task_1") is False
        assert manager.get_ready_tasks(6) == ["task_2"]
        assert manager.get_task(7, "task_1") == {"name": "dependent", "priority": 100}

    def test_all_dependencies_must_be_completed(self, manager):
        manager.add_task(1, "dependent", 10)
        manager.add_task(2, "first prerequisite", 2)
        manager.add_task(3, "second prerequisite", 3)
        manager.add_task(4, "independent", 1)
        assert manager.add_dependency(5, "task_1", "task_2") is True
        assert manager.add_dependency(6, "task_1", "task_3") is True
        assert manager.get_ready_tasks(7) == ["task_3", "task_2", "task_4"]
        assert manager.complete_task(8, "task_1") is False
        assert manager.complete_task(9, "task_2") is True
        assert manager.get_ready_tasks(10) == ["task_3", "task_4"]
        assert manager.complete_task(11, "task_1") is False
        assert manager.complete_task(12, "task_3") is True
        assert manager.get_ready_tasks(13) == ["task_1", "task_4"]
        assert manager.complete_task(14, "task_1") is True
        assert manager.get_ready_tasks(15) == ["task_4"]

    def test_chain_unblocks_one_task_at_a_time_without_auto_completion(self, manager):
        manager.add_task(1, "A", 30)
        manager.add_task(2, "B", 20)
        manager.add_task(3, "C", 10)
        assert manager.add_dependency(4, "task_1", "task_2") is True
        assert manager.add_dependency(5, "task_2", "task_3") is True
        assert manager.get_ready_tasks(6) == ["task_3"]
        assert manager.complete_task(7, "task_1") is False
        assert manager.complete_task(8, "task_2") is False
        assert manager.complete_task(9, "task_3") is True
        assert manager.get_ready_tasks(10) == ["task_2"]
        assert manager.complete_task(11, "task_1") is False
        assert manager.complete_task(12, "task_2") is True
        assert manager.get_ready_tasks(13) == ["task_1"]
        assert manager.complete_task(14, "task_1") is True
        assert manager.get_ready_tasks(15) == []

    def test_shared_prerequisite_unblocks_multiple_tasks(self, manager):
        manager.add_task(1, "first dependent", 5)
        manager.add_task(2, "second dependent", 10)
        manager.add_task(3, "shared prerequisite", 1)
        assert manager.add_dependency(4, "task_1", "task_3") is True
        assert manager.add_dependency(5, "task_2", "task_3") is True
        assert manager.get_ready_tasks(6) == ["task_3"]
        assert manager.complete_task(7, "task_3") is True
        assert manager.get_ready_tasks(8) == ["task_2", "task_1"]
        assert manager.complete_task(9, "task_2") is True
        assert manager.get_ready_tasks(10) == ["task_1"]

    def test_diamond_dependency_graph_is_not_a_cycle(self, manager):
        # A depends on B and C; B and C both depend on D.
        for timestamp, name in enumerate(["A", "B", "C", "D"], start=1):
            manager.add_task(timestamp, name, 5)
        assert manager.add_dependency(5, "task_1", "task_2") is True
        assert manager.add_dependency(6, "task_1", "task_3") is True
        assert manager.add_dependency(7, "task_2", "task_4") is True
        assert manager.add_dependency(8, "task_3", "task_4") is True
        assert manager.get_ready_tasks(9) == ["task_4"]
        assert manager.complete_task(10, "task_4") is True
        assert manager.get_ready_tasks(11) == ["task_2", "task_3"]
        assert manager.complete_task(12, "task_2") is True
        assert manager.get_ready_tasks(13) == ["task_3"]
        assert manager.complete_task(14, "task_3") is True
        assert manager.get_ready_tasks(15) == ["task_1"]

    def test_direct_cycle_is_rejected_and_original_edge_is_preserved(self, manager):
        manager.add_task(1, "A", 5)
        manager.add_task(2, "B", 5)
        assert manager.add_dependency(3, "task_1", "task_2") is True
        assert manager.add_dependency(4, "task_2", "task_1") is False
        assert manager.get_ready_tasks(5) == ["task_2"]
        assert manager.complete_task(6, "task_2") is True
        assert manager.get_ready_tasks(7) == ["task_1"]
        assert manager.complete_task(8, "task_1") is True

    def test_indirect_cycle_is_rejected_without_changing_the_chain(self, manager):
        manager.add_task(1, "A", 5)
        manager.add_task(2, "B", 5)
        manager.add_task(3, "C", 5)
        assert manager.add_dependency(4, "task_1", "task_2") is True
        assert manager.add_dependency(5, "task_2", "task_3") is True
        assert manager.add_dependency(6, "task_3", "task_1") is False
        assert manager.get_ready_tasks(7) == ["task_3"]
        assert manager.complete_task(8, "task_3") is True
        assert manager.get_ready_tasks(9) == ["task_2"]
        assert manager.complete_task(10, "task_2") is True
        assert manager.get_ready_tasks(11) == ["task_1"]
        assert manager.complete_task(12, "task_1") is True

    def test_direct_edge_along_existing_transitive_path_is_allowed(self, manager):
        manager.add_task(1, "A", 5)
        manager.add_task(2, "B", 5)
        manager.add_task(3, "C", 5)
        assert manager.add_dependency(4, "task_1", "task_2") is True
        assert manager.add_dependency(5, "task_2", "task_3") is True
        assert manager.add_dependency(6, "task_1", "task_3") is True
        assert manager.add_dependency(7, "task_1", "task_3") is False
        assert manager.get_ready_tasks(8) == ["task_3"]
        assert manager.complete_task(9, "task_3") is True
        assert manager.get_ready_tasks(10) == ["task_2"]
        assert manager.complete_task(11, "task_2") is True
        assert manager.get_ready_tasks(12) == ["task_1"]

    def test_ready_tasks_use_numeric_ids_for_priority_ties(self, manager):
        for number in range(1, 13):
            manager.add_task(number, f"job {number}", 5)
        assert manager.get_ready_tasks(13) == [f"task_{number}" for number in range(1, 13)]

    def test_ready_tasks_use_priority_order_and_exclude_blocked_tasks(self, manager):
        manager.add_task(1, "low", -1)
        manager.add_task(2, "high first", 10)
        manager.add_task(3, "blocked highest", 100)
        manager.add_task(4, "high second", 10)
        assert manager.add_dependency(5, "task_3", "task_1") is True
        assert manager.get_ready_tasks(6) == ["task_2", "task_4", "task_1"]
        assert manager.complete_task(7, "task_1") is True
        assert manager.get_ready_tasks(8) == ["task_3", "task_2", "task_4"]

    def test_completed_tasks_remain_in_get_search_and_sorted_results(self, manager):
        manager.add_task(1, "docs", 10)
        manager.add_task(2, "tests", 5)
        assert manager.complete_task(3, "task_1") is True
        assert manager.get_task(4, "task_1") == {"name": "docs", "priority": 10}
        assert manager.search_tasks(5, "docs", 10) == ["task_1"]
        assert manager.list_tasks_sorted(6, 10) == ["task_1", "task_2"]
        assert manager.get_ready_tasks(7) == ["task_2"]

    def test_updating_completed_task_does_not_reopen_it(self, manager):
        manager.add_task(1, "docs", 1)
        assert manager.complete_task(2, "task_1") is True
        assert manager.update_task(3, "task_1", "finished docs", 99) is True
        assert manager.get_task(4, "task_1") == {"name": "finished docs", "priority": 99}
        assert manager.search_tasks(5, "finished", 10) == ["task_1"]
        assert manager.get_ready_tasks(6) == []
        assert manager.complete_task(7, "task_1") is False

    def test_new_task_with_completed_tasks_name_is_separate_and_ready(self, manager):
        assert manager.add_task(1, "docs", 5) == "task_1"
        assert manager.complete_task(2, "task_1") is True
        assert manager.add_task(3, "docs", 5) == "task_2"
        assert manager.get_ready_tasks(4) == ["task_2"]
        assert manager.list_tasks_sorted(5, 10) == ["task_1", "task_2"]
        assert manager.complete_task(6, "task_1") is False
        assert manager.complete_task(7, "task_2") is True


class TestLevel4:
    """Users, quotas, and timed assignments; run with pytest -k TestLevel4."""

    def test_prompt_example(self, manager):
        manager.add_task(1, "docs", 5)
        manager.add_task(2, "docs v2", 7)
        manager.add_task(3, "tests", 7)
        assert manager.update_task(6, "task_1", "docs v1", 5) is True
        assert manager.add_dependency(15, "task_2", "task_1") is True
        assert manager.complete_task(20, "task_1") is True

        assert manager.add_user(23, "ann", 1) is True
        assert manager.add_user(24, "ann", 5) is False
        assert manager.assign_task(25, "task_3", "ann", 40) is True
        assert manager.assign_task(26, "task_2", "ann", 30) is False
        assert manager.assign_task(27, "task_2", "bob", 30) is False
        assert manager.assign_task(40, "task_2", "ann", 50) is True
        assert manager.get_ready_tasks(41) == ["task_2"]
        assert manager.get_user_tasks(50, "ann") == []

    def test_duplicate_user_keeps_original_quota_and_assignments(self, manager):
        manager.add_task(1, "first", 1)
        manager.add_task(2, "second", 1)
        assert manager.add_user(3, "ann", 1) is True
        assert manager.assign_task(4, "task_1", "ann", 20) is True
        assert manager.add_user(5, "ann", 10) is False
        assert manager.get_user_tasks(6, "ann") == ["task_1"]
        assert manager.assign_task(7, "task_2", "ann", 30) is False

    def test_unknown_user_and_user_without_assignments_return_empty(self, manager):
        assert manager.get_user_tasks(1, "missing") == []
        assert manager.add_user(2, "ann", 1) is True
        assert manager.get_user_tasks(3, "ann") == []
        assert manager.get_user_tasks(4, "missing") == []

    def test_users_have_independent_assignments_and_quotas(self, manager):
        manager.add_task(1, "first", 1)
        manager.add_task(2, "second", 1)
        manager.add_task(3, "third", 1)
        assert manager.add_user(4, "ann", 1) is True
        assert manager.add_user(5, "bob", 1) is True
        assert manager.assign_task(6, "task_1", "ann", 30) is True
        assert manager.get_user_tasks(7, "bob") == []
        assert manager.assign_task(8, "task_2", "bob", 40) is True
        assert manager.assign_task(9, "task_3", "ann", 50) is False
        assert manager.get_user_tasks(10, "ann") == ["task_1"]
        assert manager.get_user_tasks(11, "bob") == ["task_2"]

    @pytest.mark.parametrize(
        "task_id, user_id",
        [("task_999", "ann"), ("task_1", "missing"), ("task_999", "missing")],
    )
    def test_missing_task_or_user_is_rejected_without_consuming_quota(
        self, manager, task_id, user_id
    ):
        manager.add_task(1, "docs", 5)
        assert manager.add_user(2, "ann", 1) is True
        assert manager.assign_task(3, task_id, user_id, 20) is False
        assert manager.get_user_tasks(4, "ann") == []
        assert manager.assign_task(5, "task_1", "ann", 20) is True

    @pytest.mark.parametrize("finish_ts", [-1, 3, 4])
    def test_finish_time_must_be_strictly_after_assignment_time(self, manager, finish_ts):
        manager.add_task(1, "docs", 5)
        assert manager.add_user(2, "ann", 1) is True
        assert manager.assign_task(4, "task_1", "ann", finish_ts) is False
        assert manager.get_user_tasks(5, "ann") == []
        assert manager.assign_task(6, "task_1", "ann", 20) is True

    def test_completed_task_cannot_be_assigned(self, manager):
        manager.add_task(1, "completed", 5)
        manager.add_task(2, "open", 1)
        assert manager.add_user(3, "ann", 1) is True
        assert manager.complete_task(4, "task_1") is True
        assert manager.assign_task(5, "task_1", "ann", 20) is False
        assert manager.assign_task(6, "task_2", "ann", 20) is True
        assert manager.get_user_tasks(7, "ann") == ["task_2"]

    def test_blocked_task_cannot_be_assigned_until_prerequisite_completes(self, manager):
        manager.add_task(1, "dependent", 10)
        manager.add_task(2, "prerequisite", 1)
        assert manager.add_user(3, "ann", 1) is True
        assert manager.add_dependency(4, "task_1", "task_2") is True
        assert manager.assign_task(5, "task_1", "ann", 20) is False
        assert manager.get_user_tasks(6, "ann") == []
        assert manager.complete_task(7, "task_2") is True
        assert manager.assign_task(8, "task_1", "ann", 20) is True

    def test_duplicate_assignment_does_not_extend_finish_time(self, manager):
        manager.add_task(1, "docs", 5)
        assert manager.add_user(2, "ann", 2) is True
        assert manager.assign_task(3, "task_1", "ann", 20) is True
        assert manager.assign_task(4, "task_1", "ann", 40) is False
        assert manager.get_user_tasks(5, "ann") == ["task_1"]
        assert manager.get_user_tasks(20, "ann") == []
        assert manager.complete_task(21, "task_1") is False

    def test_task_cannot_be_assigned_to_two_users(self, manager):
        manager.add_task(1, "first", 5)
        manager.add_task(2, "second", 1)
        assert manager.add_user(3, "ann", 1) is True
        assert manager.add_user(4, "bob", 1) is True
        assert manager.assign_task(5, "task_1", "ann", 30) is True
        assert manager.assign_task(6, "task_1", "bob", 40) is False
        assert manager.get_user_tasks(7, "ann") == ["task_1"]
        assert manager.get_user_tasks(8, "bob") == []
        assert manager.assign_task(9, "task_2", "bob", 40) is True

    def test_quota_is_an_exact_limit_and_due_completion_frees_one_slot(self, manager):
        for timestamp, name in enumerate(["first", "second", "third"], start=1):
            manager.add_task(timestamp, name, 1)
        assert manager.add_user(4, "ann", 2) is True
        assert manager.assign_task(5, "task_1", "ann", 20) is True
        assert manager.assign_task(6, "task_2", "ann", 30) is True
        assert manager.assign_task(7, "task_3", "ann", 40) is False
        assert manager.get_user_tasks(8, "ann") == ["task_1", "task_2"]
        assert manager.assign_task(20, "task_3", "ann", 40) is True
        assert manager.get_user_tasks(21, "ann") == ["task_2", "task_3"]

    def test_zero_quota_user_cannot_receive_assignments(self, manager):
        manager.add_task(1, "docs", 5)
        assert manager.add_user(2, "ann", 0) is True
        assert manager.assign_task(3, "task_1", "ann", 20) is False
        assert manager.get_user_tasks(4, "ann") == []
        assert manager.get_ready_tasks(5) == ["task_1"]

    def test_user_tasks_sort_by_finish_time_then_numeric_id(self, manager):
        for number in range(1, 13):
            manager.add_task(number, f"job {number}", 1)
        assert manager.add_user(13, "ann", 12) is True
        assert manager.assign_task(14, "task_12", "ann", 100) is True
        assert manager.assign_task(15, "task_10", "ann", 90) is True
        assert manager.assign_task(16, "task_2", "ann", 90) is True
        assert manager.assign_task(17, "task_11", "ann", 90) is True
        assert manager.assign_task(18, "task_1", "ann", 100) is True
        assert manager.get_user_tasks(19, "ann") == [
            "task_2", "task_10", "task_11", "task_1", "task_12"
        ]
        assert manager.get_user_tasks(90, "ann") == ["task_1", "task_12"]
        assert manager.get_user_tasks(100, "ann") == []
        assert manager.complete_task(101, "task_10") is False

    def test_assigned_tasks_stay_in_ready_results_until_completion(self, manager):
        manager.add_task(1, "assigned", 10)
        manager.add_task(2, "unassigned", 5)
        assert manager.add_user(3, "ann", 1) is True
        assert manager.assign_task(4, "task_1", "ann", 20) is True
        assert manager.get_ready_tasks(5) == ["task_1", "task_2"]
        assert manager.get_user_tasks(6, "ann") == ["task_1"]

    def test_assignment_is_active_before_finish_and_completed_at_exact_finish(self, manager):
        manager.add_task(1, "docs", 5)
        assert manager.add_user(2, "ann", 1) is True
        assert manager.assign_task(3, "task_1", "ann", 10) is True
        assert manager.get_user_tasks(9, "ann") == ["task_1"]
        assert manager.get_user_tasks(10, "ann") == []
        assert manager.get_ready_tasks(11) == []
        assert manager.complete_task(12, "task_1") is False
        assert manager.get_task(13, "task_1") == {"name": "docs", "priority": 5}

    def test_manual_completion_frees_quota_and_old_finish_has_no_second_effect(self, manager):
        for timestamp, name in enumerate(["first", "second", "third"], start=1):
            manager.add_task(timestamp, name, 1)
        assert manager.add_user(4, "ann", 1) is True
        assert manager.assign_task(5, "task_1", "ann", 20) is True
        assert manager.complete_task(6, "task_1") is True
        assert manager.get_user_tasks(7, "ann") == []
        assert manager.assign_task(8, "task_2", "ann", 30) is True
        assert manager.get_user_tasks(20, "ann") == ["task_2"]
        assert manager.assign_task(21, "task_3", "ann", 40) is False
        assert manager.complete_task(22, "task_1") is False
        assert manager.get_user_tasks(30, "ann") == []
        assert manager.assign_task(31, "task_3", "ann", 40) is True

    def test_manual_completion_at_finish_reports_already_completed(self, manager):
        manager.add_task(1, "docs", 5)
        assert manager.add_user(2, "ann", 1) is True
        assert manager.assign_task(3, "task_1", "ann", 10) is True
        assert manager.complete_task(10, "task_1") is False
        assert manager.get_user_tasks(11, "ann") == []

    def test_auto_completion_unblocks_dependency_and_frees_quota_before_assign(self, manager):
        manager.add_task(1, "prerequisite", 1)
        manager.add_task(2, "dependent", 10)
        assert manager.add_user(3, "ann", 1) is True
        assert manager.add_dependency(4, "task_2", "task_1") is True
        assert manager.assign_task(5, "task_1", "ann", 10) is True
        assert manager.assign_task(9, "task_2", "ann", 20) is False
        assert manager.assign_task(10, "task_2", "ann", 20) is True
        assert manager.get_ready_tasks(11) == ["task_2"]
        assert manager.get_user_tasks(12, "ann") == ["task_2"]
        assert manager.get_user_tasks(20, "ann") == []
        assert manager.get_ready_tasks(21) == []

    def test_expired_task_cannot_be_reassigned_even_though_slot_is_free(self, manager):
        manager.add_task(1, "first", 5)
        manager.add_task(2, "second", 1)
        assert manager.add_user(3, "ann", 1) is True
        assert manager.assign_task(4, "task_1", "ann", 10) is True
        assert manager.assign_task(10, "task_1", "ann", 20) is False
        assert manager.assign_task(11, "task_2", "ann", 20) is True

    def test_cannot_add_dependency_to_task_finishing_at_current_timestamp(self, manager):
        manager.add_task(1, "finishing", 5)
        manager.add_task(2, "open", 1)
        assert manager.add_user(3, "ann", 1) is True
        assert manager.assign_task(4, "task_1", "ann", 10) is True
        assert manager.add_dependency(10, "task_1", "task_2") is False
        assert manager.get_ready_tasks(11) == ["task_2"]
        assert manager.get_user_tasks(12, "ann") == []

    def test_dependency_on_task_finishing_now_is_immediately_satisfied(self, manager):
        manager.add_task(1, "finishing", 5)
        manager.add_task(2, "dependent", 1)
        assert manager.add_user(3, "ann", 1) is True
        assert manager.assign_task(4, "task_1", "ann", 10) is True
        assert manager.add_dependency(10, "task_2", "task_1") is True
        assert manager.get_ready_tasks(11) == ["task_2"]

    @pytest.mark.parametrize(
        "method_name, args, expected",
        [
            ("add_task", ("new", 3), "task_3"),
            ("update_task", ("task_2", "renamed", 5), True),
            ("get_task", ("task_1",), {"name": "finishing", "priority": 1}),
            ("search_tasks", ("", 10), ["task_2", "task_1"]),
            ("list_tasks_sorted", (10,), ["task_2", "task_1"]),
            ("add_dependency", ("task_2", "task_1"), True),
            ("complete_task", ("task_1",), False),
            ("get_ready_tasks", (), ["task_2"]),
            ("add_user", ("bob", 1), True),
            ("assign_task", ("task_2", "ann", 30), True),
            ("get_user_tasks", ("ann",), []),
        ],
    )
    def test_due_assignments_work_with_every_public_method(
        self, manager, method_name, args, expected
    ):
        manager.add_task(1, "finishing", 1)
        manager.add_task(2, "next", 2)
        assert manager.add_user(3, "ann", 1) is True
        assert manager.assign_task(4, "task_1", "ann", 10) is True

        result = getattr(manager, method_name)(10, *args)
        if isinstance(expected, bool):
            assert result is expected
        else:
            assert result == expected
        active = ["task_2"] if method_name == "assign_task" else []
        assert manager.get_user_tasks(11, "ann") == active
        assert manager.complete_task(12, "task_1") is False

    def test_updating_assigned_task_does_not_change_finish_order(self, manager):
        manager.add_task(1, "first", 10)
        manager.add_task(2, "second", 1)
        assert manager.add_user(3, "ann", 2) is True
        assert manager.assign_task(4, "task_1", "ann", 30) is True
        assert manager.assign_task(5, "task_2", "ann", 20) is True
        assert manager.update_task(6, "task_1", "renamed", 100) is True
        assert manager.get_user_tasks(7, "ann") == ["task_2", "task_1"]
        assert manager.get_user_tasks(20, "ann") == ["task_1"]
        assert manager.get_task(21, "task_1") == {"name": "renamed", "priority": 100}
        assert manager.get_user_tasks(30, "ann") == []

    def test_time_jump_completes_all_due_tasks_across_users_but_not_future_tasks(self, manager):
        for timestamp, name in enumerate(["first", "second", "third"], start=1):
            manager.add_task(timestamp, name, 1)
        assert manager.add_user(4, "ann", 2) is True
        assert manager.add_user(5, "bob", 1) is True
        assert manager.assign_task(6, "task_1", "ann", 20) is True
        assert manager.assign_task(7, "task_2", "ann", 30) is True
        assert manager.assign_task(8, "task_3", "bob", 20) is True
        assert manager.get_user_tasks(25, "ann") == ["task_2"]
        assert manager.get_user_tasks(26, "bob") == []
        assert manager.complete_task(27, "task_1") is False
        assert manager.complete_task(28, "task_3") is False
        assert manager.get_ready_tasks(29) == ["task_2"]
        assert manager.get_user_tasks(30, "ann") == []

    def test_unassigned_task_does_not_auto_complete_as_time_passes(self, manager):
        manager.add_task(1, "never assigned", 5)
        assert manager.add_user(2, "ann", 1) is True
        assert manager.get_ready_tasks(1000) == ["task_1"]
        assert manager.get_user_tasks(1001, "ann") == []
        assert manager.complete_task(1002, "task_1") is True

    def test_auto_completion_orders_by_finish_time_then_numeric_id(self, manager, monkeypatch):
        from heapq import heappop

        for number in range(1, 13):
            manager.add_task(number, f"job {number}", 1)
        assert manager.add_user(13, "ann", 4) is True
        assert manager.assign_task(14, "task_12", "ann", 100) is True
        assert manager.assign_task(15, "task_1", "ann", 100) is True
        assert manager.assign_task(16, "task_10", "ann", 90) is True
        assert manager.assign_task(17, "task_2", "ann", 90) is True

        # Final state alone cannot reveal the order of same-time completions.
        completion_order = []

        def record_pop(heap):
            entry = heappop(heap)
            completion_order.append(entry[-1])
            return entry

        monkeypatch.setattr("tm.heapq.heappop", record_pop)
        assert manager.get_user_tasks(100, "ann") == []
        assert completion_order == ["task_2", "task_10", "task_1", "task_12"]
