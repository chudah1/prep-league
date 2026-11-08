# Top 3 strict-interviewer points

1. **Apply the numeric ID tie-breaker to automatic completion.** The completion
   heap compares task IDs as strings, so tasks finishing together are processed
   as `task_10` before `task_2`. Include the numeric ID in the heap key and test
   completion order, not just the final completed state.

2. **Handle long dependency chains without recursive stack limits.** A valid
   dependency into a 1,005-task chain raises `RecursionError` and leaves the
   tentative edge in the graph. Use an iterative traversal and check whether
   the new edge would create a cycle before adding it.

3. **Avoid rebuilding and sorting everything for one assignment.** Every public
   call rebuilds the assignment heap, while `assign_task` also scans and sorts
   all ready tasks to check one candidate. Keep a persistent completion heap,
   skip stale entries after manual completion, and check readiness directly for
   the requested task. This is a scalability improvement, not a failure of an
   explicit performance requirement.
