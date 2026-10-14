
from typing import Any
from collections import defaultdict
from dataclasses import dataclass
import time
from bisect import bisect_right

@dataclass
class Entry:
    value: str
    timestamp: int | None = None
    ttl: int | None = None

class InMemoryDB:

    def __init__(self):
        self.db: dict[str: dict[str: Entry]] = {}
        #backup should prlly be [{timestamp: [{key: {field: Entry}}]}]
        self.backup_list: list[tuple[int, dict[str, dict[str, Entry]]]] = []


    def set(self, key: str, field: str, value:Any) -> None:

        if key in self.db:
            self.db[key][field] = Entry(value)
        else:
            self.db[key] = {field: Entry(value)}

    def get(self, key, field) -> str | None:

        key_value = self.db.get(key)
        if key_value:
            field_value = key_value.get(field)
            return field_value.value if field_value else None
        return None

    def delete(self, key, field):

        if self.get(key, field) is not None:
            del self.db[key][field]
            if len(self.db[key]) == 0:
                del self.db[key]
            return True
        else: return False

    def scan(self, key) -> str:
        record = self.db.get(key, {})
        return [f"{field}({entry_value.value})" for field, entry_value in sorted(record.items())]

    def scan_by_prefix(self, key, prefix) -> list[str]:
        record = self.db.get(key, {})
        return [f"{field}({entry_value.value})" for field, entry_value in sorted(record.items()) if field.startswith(prefix)] #todo: can use trie

    def set_at(self, key, field, value, timestamp) -> None:

        self.db.setdefault(key, {})[field] = Entry(value, timestamp=timestamp, ttl=None)

    def set_at_with_ttl(self, key, field, value, timestamp, ttl):
        self.db.setdefault(key, {})[field] = Entry(value, timestamp=timestamp, ttl=ttl)

    def _is_alive(self, entry: Entry, timestamp: int) -> bool:

        return (
        entry.ttl is None
        or timestamp < entry.timestamp + entry.ttl
    )

    def get_at(self, key, field, timestamp):

        if key in self.db:
            if field in self.db[key]:
                entry = self.db[key][field]
                if self._is_alive(entry, timestamp):
                    return entry.value
        return None

    def scan_at(self, key, timestamp) -> str:
        record = self.db.get(key, {})
        return [f"{field}({entry_value.value})" for field, entry_value in sorted(record.items()) if self._is_alive(entry_value, timestamp)]

    def scan_by_prefix_at(self, key, prefix, timestamp) -> list[str]:
        record = self.db.get(key, {})
        return [f"{field}({entry_value.value})" for field, entry_value in sorted(record.items()) if field.startswith(prefix) and self._is_alive(entry_value, timestamp)] #todo: can use trie

    def delete_at(self, key, field, timestamp):
        if self.get_at(key, field, timestamp) is not None:
                
                del self.db[key][field]
                if len(self.db[key]) == 0:
                    del self.db[key]
                return True
        else: 
            return False

    def backup(self, timestamp) -> int:
        snapshot = {}

        for key, record in self.db.items():
            for field, entry in record.items():
                if not self._is_alive(entry, timestamp):
                    continue

                remaining_ttl = None
                if entry.ttl is not None:
                    remaining_ttl = entry.timestamp + entry.ttl - timestamp

                snapshot.setdefault(key, {})[field] = Entry(
                    value=entry.value,
                    timestamp=timestamp,
                    ttl=remaining_ttl,
                )

        self.backup_list.append((timestamp, snapshot))
        return len(snapshot)

    def restore(self, timestamp, timestamp_to_restore) -> None:

        #i want to find before or at so bisect_right

        backup_times = [backup_time for backup_time, _ in self.backup_list]
        
        index = bisect_right(backup_times, timestamp_to_restore) -1
        if index < 0: return None

        snapshot = self.backup_list[index]
        _, db_mapping = snapshot
        backup_db = {}
        for key, record in db_mapping.items():
            backup_db[key] = {}
            for field, entry in record.items():
                backup_db[key][field] = Entry(
                value=entry.value,
                timestamp=timestamp,
                ttl=entry.ttl,
            )
        self.db = backup_db
        return None
