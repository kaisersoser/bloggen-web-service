# flake8: noqa
import json
import os
import sys
import types
from datetime import datetime, timedelta
from types import SimpleNamespace

import pytest

CURRENT_DIR = os.path.dirname(__file__)
SRC_DIR = os.path.abspath(os.path.join(CURRENT_DIR, ".."))
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)

from core.task_manager import TaskManager, BlogStatus
from core.resource_cleanup import cleanup_manager, CleanupReason


class FakeAcquireContext:
    def __init__(self, connection):
        self._connection = connection

    async def __aenter__(self):
        return self._connection

    async def __aexit__(self, exc_type, exc, tb):
        return False


class FakePool:
    def __init__(self, connection):
        self._connection = connection

    def acquire(self):
        return FakeAcquireContext(self._connection)


class FakeConnection:
    def __init__(self, rows):
        self._rows = rows

    async def fetch(self, _query, *params):
        if len(params) == 3:
            statuses, cutoff, limit = params
            filtered = [
                row
                for row in self._rows
                if row["status"] in statuses and row["updated_at"] < cutoff
            ]
            return filtered[:limit]

        if len(params) == 2:
            statuses, limit = params
            filtered = [row for row in self._rows if row["status"] in statuses]
            return filtered[:limit]

        raise ValueError("Unexpected parameters for fetch")


class BufferStub:
    def __init__(self):
        self.stopped = []
        self.cleanup_calls = 0

    async def stop_buffering(self, task_id: str) -> None:
        self.stopped.append(task_id)

    async def cleanup_expired_buffers(self) -> int:
        self.cleanup_calls += 1
        return 0


class FakeRedisClient:
    def __init__(self, entries):
        self.entries = entries
        self.deleted = []

    async def scan_iter(self, match="*", count=None):
        del match, count
        for key in list(self.entries.keys()):
            yield key

    async def get(self, key):
        return self.entries.get(key)

    async def delete(self, *keys):
        for key in keys:
            self.deleted.append(key)
            self.entries.pop(key, None)
        return len(keys)


@pytest.mark.asyncio
async def test_expire_stale_incomplete_tasks_marks_old_tasks_failed(monkeypatch):
    tm = TaskManager()
    tm.configure_cleanup(stale_incomplete_minutes=60, max_cleanup_batch=5)

    buffer = BufferStub()
    tm.set_message_buffer(buffer)

    now = datetime.utcnow()
    rows = [
        {
            "id": "expired-in-progress",
            "user_id": "user-123",
            "status": BlogStatus.IN_PROGRESS.value,
            "updated_at": now - timedelta(hours=2),
        },
        {
            "id": "recent-in-progress",
            "user_id": "user-123",
            "status": BlogStatus.IN_PROGRESS.value,
            "updated_at": now - timedelta(minutes=10),
        },
    ]

    fake_pool = FakePool(FakeConnection(rows))

    async def fake_get_db_connection():
        return fake_pool

    monkeypatch.setattr(tm, "_get_db_connection", fake_get_db_connection)

    failed_tasks = []

    async def fake_fail_task(self, task_id, error_message):
        failed_tasks.append((task_id, error_message))

    monkeypatch.setattr(tm, "fail_task", types.MethodType(fake_fail_task, tm))

    cleanup_calls = []

    async def fake_cleanup_task(task_id, reason):
        cleanup_calls.append((task_id, reason))

    monkeypatch.setattr(cleanup_manager, "cleanup_task", fake_cleanup_task)

    await tm.run_cleanup_cycle()

    assert failed_tasks == [("expired-in-progress", "Task expired due to inactivity")]
    assert buffer.stopped == ["expired-in-progress"]
    assert buffer.cleanup_calls == 1
    assert cleanup_calls == [("expired-in-progress", CleanupReason.TIMEOUT)]

    stats = tm.get_cleanup_stats()
    assert stats["cycles"] == 1
    assert stats["expired_tasks"] == 1
    assert stats["redis_keys_removed"] == 0
    assert stats["buffers_pruned"] == 0


@pytest.mark.asyncio
async def test_cleanup_redis_status_cache_removes_old_entries(monkeypatch):
    tm = TaskManager()
    tm.configure_cleanup(stale_completed_minutes=1, max_cleanup_batch=10)

    async def fake_expire(self):
        return None

    monkeypatch.setattr(
        tm, "_expire_stale_incomplete_tasks", types.MethodType(fake_expire, tm)
    )

    now = datetime.utcnow()
    entries = {
        "task_status:recent": json.dumps(
            {"updated_at": (now - timedelta(seconds=30)).isoformat()}
        ),
        "task_status:old": json.dumps(
            {"updated_at": (now - timedelta(minutes=5)).isoformat()}
        ),
        "task_status:invalid": "not-json",
    }
    redis_client = FakeRedisClient(entries)
    tm.set_message_buffer(None)
    tm.set_redis_manager(SimpleNamespace(redis_client=redis_client))

    await tm.run_cleanup_cycle()

    assert set(redis_client.deleted) == {"task_status:old", "task_status:invalid"}
    assert "task_status:recent" in redis_client.entries

    stats = tm.get_cleanup_stats()
    assert stats["cycles"] == 1
    assert stats["redis_keys_removed"] == 2  # old + invalid


class FakeRedisManager:
    def __init__(self):
        self.redis_client = object()
        self.cached = []

    async def cache_task_status(self, task_id, task_state, ttl):
        self.cached.append((task_id, task_state, ttl))


@pytest.mark.asyncio
async def test_warm_cache_from_database_populates_redis(monkeypatch):
    tm = TaskManager()
    tm.configure_cleanup(max_cleanup_batch=2)

    now = datetime.utcnow()
    rows = [
        {
            "id": "queued-task",
            "user_id": "user-1",
            "topic": "Topic A",
            "instructions": "",
            "status": BlogStatus.QUEUED.value,
            "progress": 0,
            "current_step": "Queued for processing",
            "error": None,
            "content": None,
            "hero_image_url": None,
            "created_at": now - timedelta(minutes=5),
            "updated_at": now - timedelta(minutes=5),
        },
        {
            "id": "running-task",
            "user_id": "user-2",
            "topic": "Topic B",
            "instructions": "",
            "status": BlogStatus.IN_PROGRESS.value,
            "progress": 30,
            "current_step": "Researching",
            "error": None,
            "content": None,
            "hero_image_url": None,
            "created_at": now - timedelta(minutes=30),
            "updated_at": now - timedelta(minutes=1),
        },
    ]

    fake_pool = FakePool(FakeConnection(rows))

    async def fake_get_db_connection():
        return fake_pool

    monkeypatch.setattr(tm, "_get_db_connection", fake_get_db_connection)

    redis_manager = FakeRedisManager()
    tm.set_redis_manager(redis_manager)

    result = await tm.warm_cache_from_database()

    assert result == {"total": 2, "queued": 1, "in_progress": 1}
    assert len(redis_manager.cached) == 2
    for task_id, task_state, ttl in redis_manager.cached:
        assert task_id in {"queued-task", "running-task"}
        assert "status" in task_state
        assert ttl == tm._redis_status_ttl
