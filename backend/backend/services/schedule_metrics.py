"""
Schedule metrics and critical path calculation utilities for Diriyah AI.

This module provides functions to compute the critical path and
schedule slack for a set of tasks represented as dictionaries with
start and finish dates and predecessor relationships. It implements a
simple Critical Path Method (CPM) using a directed acyclic graph and
dynamic programming. Dates are parsed using Python's ``datetime``
library; durations are computed in days.

Task schema::

    {
        "id": "1",
        "name": "Task Name",
        "start": "2026-01-01",
        "finish": "2026-01-05",
        "dependencies": ["0", ...]  # optional list of predecessor IDs
    }

The algorithm assumes tasks without predecessors start at day zero. It
computes earliest and latest start/finish times, slack, and returns
the list of critical tasks (slack == 0).
"""

from datetime import datetime
from typing import Dict, List, Tuple, Any


def _parse_date(date_str: str) -> datetime:
    """Parse ISO8601 or date string to ``datetime``; raise if invalid."""
    for fmt in ("%Y-%m-%d", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M:%S%z"):
        try:
            return datetime.strptime(date_str, fmt)
        except Exception:
            continue
    raise ValueError(f"Unsupported date format: {date_str}")


def compute_critical_path(tasks: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Compute the critical path and slack for a list of tasks.

    Args:
        tasks: List of task dictionaries with at least keys ``id``,
            ``start``, ``finish``, and optional ``dependencies`` (list of
            predecessor IDs). Durations are computed in days.

    Returns:
        A dictionary containing per‑task timing metrics and critical path
        information::

            {
                'tasks': {
                    'task_id': {
                        'duration': ...,
                        'earliest_start': ...,
                        'earliest_finish': ...,
                        'latest_start': ...,
                        'latest_finish': ...,
                        'slack': ...,
                    },
                    ...
                },
                'critical_path': ['task_id', ...],
                'project_duration': ...
            }
    """
    # Build mapping from ID to task info
    task_map: Dict[str, Dict[str, Any]] = {t["id"]: t for t in tasks}
    # Ensure dependencies list exists
    for t in tasks:
        t.setdefault("dependencies", [])

    # Compute durations in days (minimum 1 day)
    durations: Dict[str, float] = {}
    for t in tasks:
        try:
            start = _parse_date(t.get("start", ""))
            finish = _parse_date(t.get("finish", ""))
            dur = (finish - start).days
            if dur <= 0:
                dur = 1
        except Exception:
            dur = 1
        durations[t["id"]] = dur

    # Build graph of predecessors and successors
    successors: Dict[str, List[str]] = {tid: [] for tid in task_map}
    predecessors: Dict[str, List[str]] = {tid: [] for tid in task_map}
    for t in tasks:
        for pred in t.get("dependencies", []):
            if pred in task_map:
                predecessors[t["id"]].append(pred)
                successors[pred].append(t["id"])

    # Topologically sort tasks
    from collections import deque
    no_pred = [tid for tid, preds in predecessors.items() if not preds]
    queue = deque(no_pred)
    topo_order: List[str] = []
    while queue:
        tid = queue.popleft()
        topo_order.append(tid)
        for succ in successors[tid]:
            predecessors[succ].remove(tid)
            if not predecessors[succ]:
                queue.append(succ)

    # Compute earliest start/finish times
    earliest_start: Dict[str, float] = {}
    earliest_finish: Dict[str, float] = {}
    for tid in topo_order:
        preds = task_map[tid].get("dependencies", [])
        if not preds:
            earliest_start[tid] = 0.0
        else:
            earliest_start[tid] = max(earliest_finish[p] for p in preds if p in earliest_finish)
        earliest_finish[tid] = earliest_start[tid] + durations[tid]

    project_duration = max(earliest_finish.values()) if earliest_finish else 0.0

    # Compute latest finish/start times
    latest_finish: Dict[str, float] = {}
    latest_start: Dict[str, float] = {}
    end_tasks = [tid for tid, succs in successors.items() if not succs]
    for tid in end_tasks:
        latest_finish[tid] = project_duration
        latest_start[tid] = project_duration - durations[tid]
    for tid in reversed(topo_order):
        if tid not in latest_finish:
            succs = successors[tid]
            latest_finish[tid] = min(latest_start[s] for s in succs)
            latest_start[tid] = latest_finish[tid] - durations[tid]

    # Compute slack and critical tasks
    slack: Dict[str, float] = {}
    critical_tasks: List[str] = []
    for tid in topo_order:
        es = earliest_start[tid]
        ls = latest_start[tid]
        slack_val = ls - es
        slack[tid] = slack_val
        if abs(slack_val) < 1e-6:
            critical_tasks.append(tid)

    per_task: Dict[str, Dict[str, float]] = {}
    for tid in topo_order:
        per_task[tid] = {
            "duration": durations[tid],
            "earliest_start": earliest_start[tid],
            "earliest_finish": earliest_finish[tid],
            "latest_start": latest_start[tid],
            "latest_finish": latest_finish[tid],
            "slack": slack[tid],
        }

    return {
        "tasks": per_task,
        "critical_path": critical_tasks,
        "project_duration": project_duration,
    }