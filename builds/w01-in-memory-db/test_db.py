from db import InMemoryDB


def test_level_1_records_and_fields():
    db = InMemoryDB()

    assert db.set("u1", "name", "ann") is None
    assert db.set("u1", "age", "30") is None
    assert db.set("u1", "name", "bob") is None
    assert db.get("u1", "name") == "bob"
    assert db.get("u2", "name") is None
    assert db.get("u1", "zip") is None
    assert db.delete("u1", "zip") is False
    assert db.delete("u1", "age") is True


def test_level_1_delete_removes_empty_record():
    db = InMemoryDB()
    db.set("u1", "name", "ann")

    assert db.delete("u1", "name") is True
    assert db.get("u1", "name") is None
    assert db.scan("u1") == []


def test_level_2_scan():
    db = InMemoryDB()
    db.set("u1", "name", "ann")
    db.set("u1", "age", "30")
    db.set("u1", "nickname", "a")

    assert db.scan("u1") == ["age(30)", "name(ann)", "nickname(a)"]
    assert db.scan("u9") == []


def test_level_2_scan_by_prefix():
    db = InMemoryDB()
    db.set("u1", "name", "ann")
    db.set("u1", "age", "30")
    db.set("u1", "nickname", "a")

    assert db.scan_by_prefix("u1", "n") == ["name(ann)", "nickname(a)"]
    assert db.scan_by_prefix("u1", "x") == []
    assert db.scan_by_prefix("u9", "n") == []


def test_level_3_timestamps_and_ttl():
    db = InMemoryDB()

    assert db.set_at_with_ttl("k", "f", "v", 10, 5) is None
    assert db.get_at("k", "f", 14) == "v"
    assert db.get_at("k", "f", 15) is None
    assert db.set_at("k", "g", "w", 16) is None
    assert db.scan_at("k", 20) == ["g(w)"]
    assert db.set_at_with_ttl("k", "g", "x", 21, 3) is None
    assert db.get_at("k", "g", 24) is None
    assert db.delete_at("k", "g", 25) is False


def test_level_3_overwrites_replace_expiry_policy():
    db = InMemoryDB()
    db.set_at_with_ttl("k", "f", "temporary", 1, 2)
    db.set_at("k", "f", "permanent", 2)

    assert db.get_at("k", "f", 100) == "permanent"


def test_level_3_timed_scans_are_sorted_and_filter_expired_fields():
    db = InMemoryDB()
    db.set_at("k", "zebra", "z", 1)
    db.set_at_with_ttl("k", "alpha", "a", 2, 3)
    db.set_at_with_ttl("k", "alpine", "b", 3, 10)

    assert db.scan_at("k", 5) == ["alpine(b)", "zebra(z)"]
    assert db.scan_by_prefix_at("k", "al", 5) == ["alpine(b)"]
    assert db.scan_at("missing", 5) == []


def test_level_4_backup_and_restore():
    db = InMemoryDB()
    db.set_at_with_ttl("a", "f", "1", 10, 10)
    db.set_at("b", "g", "2", 11)

    assert db.backup(15) == 2
    db.set_at("a", "h", "3", 16)
    assert db.restore(30, 17) is None
    assert db.get_at("a", "f", 34) == "1"
    assert db.get_at("a", "f", 35) is None
    assert db.get_at("a", "h", 31) is None
    assert db.get_at("b", "g", 100) == "2"


def test_level_4_restore_uses_latest_eligible_backup():
    db = InMemoryDB()
    db.set_at("k", "f", "first", 1)
    db.backup(2)
    db.set_at("k", "f", "second", 3)
    db.backup(4)
    db.set_at("k", "f", "third", 5)

    db.restore(10, 3)
    assert db.get_at("k", "f", 10) == "first"


def test_level_4_restore_without_eligible_backup_is_no_op():
    db = InMemoryDB()
    db.set_at("k", "f", "value", 10)

    assert db.restore(20, 5) is None
    assert db.get_at("k", "f", 20) == "value"
