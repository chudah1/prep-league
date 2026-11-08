
from dataclasses import dataclass, field
from collections import defaultdict
from enum import Enum, auto
import heapq


class Status(Enum):
    assigned = auto()
    pending = auto()
    completed = auto()

@dataclass
class TaskEntry:
    name: str
    priority: int
    time_added: int
    status: Status = Status.assigned
    time_assigned:int = 0


@dataclass
class User:
    id: str
    quota: int
    tasks:list = field(default_factory=set)



class TaskManager:

    def __init__(self):
        #name->Entry
        self.task_tracker : dict = {}
        #task_id -> task
        self.task_id_map: dict = {}
        self.task_counter = 0
        #task_id; [task_2, task_3]
        self.dep_tracker:dict[list] = defaultdict(list)
        self.users = {}
        # task_id : User
        self.tasks_assigned:dict = {}


    def _complete_due_assignments(self, timestamp):
        tasks = [(self.task_id_map[task_id].time_assigned, task_id ) for task_id in self.tasks_assigned]
        heapq.heapify(tasks)

        while tasks and tasks[0][0] <= timestamp:
            finish_time, task_id = heapq.heappop(tasks)
            self.task_id_map[task_id].status = Status.completed
            user = self.tasks_assigned.pop(task_id)
            user.tasks.remove(task_id)
            


    def add_task(self, timestamp, name, priority) ->str:
        self._complete_due_assignments(timestamp)
        task_entry = TaskEntry(name=name, priority=priority, time_added=timestamp)
        self.task_tracker[name] = task_entry
        self.task_counter +=1
        task_id = f"task_{self.task_counter}"
        self.task_id_map[task_id] = task_entry
        return task_id
    
    def update_task(self, timestamp, task_id, name, priority)->bool:
        self._complete_due_assignments(timestamp)

        task = self.task_id_map.get(task_id)
        if task is None: return False


        self.task_id_map[task_id].name = name
        self.task_id_map[task_id].priority = priority
        return True

    def get_task(self, timestamp, task_id) -> dict | None:
        self._complete_due_assignments(timestamp)

        task = self.task_id_map.get(task_id)

        if not task is None:
            return {"name": task.name, "priority": task.priority}
        return None

    def search_tasks(self, timestamp, name_filter, k) -> list[str]:
        self._complete_due_assignments(timestamp)

        if k <= 0: return []
        tasks = [(task_id, entry.priority)  for task_id, entry in self.task_id_map.items() if name_filter == "" or name_filter in entry.name]

        tasks.sort(key=lambda x: (-x[1], int(x[0].split("_")[1])))
        result = [t[0] for t in tasks][:k]
        return result
    
    def list_tasks_sorted(self, timestamp, k) -> list[str]:
        self._complete_due_assignments(timestamp)

        if k <=0: return []
        tasks = [(task_id, entry.priority)  for task_id, entry in self.task_id_map.items()]

        tasks.sort(key=lambda x: (-x[1], int(x[0].split("_")[1])))
        result = [t[0] for t in tasks][:k]
        return result

    def _would_create_cycle(self, task, visiting, visited):

        if task in visiting:
            return True #cycle

        if task in visited:
            return False #already seen

        visiting.add(task)
        for dependency in self.dep_tracker[task]:
            if self._would_create_cycle(dependency, visiting, visited):
                return True
        visited.add(task)
        visiting.remove(task)
        return False


    def add_dependency(self, timestamp, task_id, depends_on) -> bool:
        self._complete_due_assignments(timestamp)

        if task_id == depends_on or self.task_id_map.get(task_id) is None or self.task_id_map.get(depends_on) is None or self.task_id_map[task_id].status == Status.completed:
            return False

        if depends_on in self.dep_tracker[task_id]:
            return False
        self.dep_tracker[task_id].append(depends_on)
        if self._would_create_cycle(task_id, set(), set()):
            self.dep_tracker[task_id].pop()
            return False
        return True

    def complete_task(self, timestamp, task_id) -> bool:
        self._complete_due_assignments(timestamp)

        if self.task_id_map.get(task_id) is None: return False

        if self.task_id_map[task_id].status == Status.completed:
            return False

        for task in self.dep_tracker[task_id]:
            if self.task_id_map[task].status != Status.completed:
                return False

        self.task_id_map.get(task_id).status = Status.completed
        #remove it is now complete
        user = self.tasks_assigned.pop(task_id, None)
        if user is not None:
            user.tasks.remove(task_id)
        return True

    def get_ready_tasks(self, timestamp) -> list[str]:
        self._complete_due_assignments(timestamp)

        tasks = []
        for task, entry in self.task_id_map.items():

            if entry.status != Status.completed:
                if self.dep_tracker.get(task) is None:
                    tasks.append((task, entry.priority))
                else:
                    if all(self.task_id_map[dep].status == Status.completed for dep in self.dep_tracker[task]):
                        tasks.append((task, entry.priority))

        tasks.sort(key=lambda x: (-x[1], int(x[0].split("_")[1])))
        return [task_id for task_id, priority in tasks]

    def add_user(self, timestamp, user_id, quota) -> bool:
        self._complete_due_assignments(timestamp)

        user = self.users.get(user_id)
        if user:
            return False
        self.users[user_id] = User(user_id, quota)
        return True

    def assign_task(self, timestamp, task_id, user_id, finish_ts) -> bool:
        self._complete_due_assignments(timestamp)

        task = self.task_id_map.get(task_id)
        if task is None: return False
        user = self.users.get(user_id)
        if user is None: return False


        ready_tasks = self.get_ready_tasks(timestamp)

        if any(task_id== task for task in ready_tasks) and self.tasks_assigned.get(task_id) is None:

            if len(user.tasks) < user.quota and finish_ts > timestamp:
                #assign
                user.tasks.add(task_id)
                self.tasks_assigned[task_id] = user
                self.task_id_map[task_id].time_assigned = finish_ts
                return True
        return False

    def get_user_tasks(self, timestamp, user_id) -> list[str]:
        self._complete_due_assignments(timestamp)

     
        user = self.users.get(user_id)
        if user is None: return []

        if not user.tasks: return []

        tasks = [(self.task_id_map[task_id].time_assigned, task_id) for task_id in user.tasks]
        tasks.sort(key= lambda x: (x[0], int(x[1].split("_")[1])))
        result = [t[1] for t in tasks]
        return result



