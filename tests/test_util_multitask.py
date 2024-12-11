import os
import asyncio
from time import sleep

import pytest

from v2dl.utils import AsyncService, Task, ThreadingService

env = os.getenv("GITHUB_ACTIONS", "false")
WAIT_TIME = 1.0 if env != "false" else 0.1


def simple_add(a, b):
    return a + b


def failing_task():
    raise ValueError("Intentional error")


async def async_simple_add(a, b):
    await asyncio.sleep(0.0001)
    return a + b


async def async_failing_task():
    raise ValueError("Intentional async error")


@pytest.fixture
def threading_service(mock_logger):
    return ThreadingService(mock_logger, max_workers=2)


@pytest.fixture
def async_service(mock_logger):
    return AsyncService(mock_logger, max_workers=2)


def test_threading_add_single_task(threading_service):
    task = Task(task_id="task1", func=simple_add, args=(1, 2))

    threading_service.start()
    threading_service.add_task(task)
    sleep(WAIT_TIME)

    result = threading_service.get_result("task1")
    assert result == 3


def test_threading_add_multiple_tasks(threading_service):
    tasks = [Task(task_id=f"task{i}", func=simple_add, args=(i, i)) for i in range(3)]

    threading_service.start()
    threading_service.add_tasks(tasks)
    sleep(WAIT_TIME)

    results = threading_service.get_results()
    assert len(results) == 3
    assert results["task0"] == 0
    assert results["task1"] == 2
    assert results["task2"] == 4


def test_threading_handle_exception(threading_service):
    task = Task(task_id="failing_task", func=failing_task)

    threading_service.start()
    threading_service.add_task(task)
    sleep(WAIT_TIME)

    result = threading_service.get_result("failing_task")
    assert result is None
    threading_service.logger.error.assert_called_once()


@pytest.mark.asyncio
async def test_async_add_single_task(async_service):
    task = Task(task_id="async_task", func=async_simple_add, args=(3, 4))

    async_service.start()
    async_service.add_task(task)
    await asyncio.sleep(WAIT_TIME)

    result = async_service.get_result("async_task")
    assert result == 7


@pytest.mark.asyncio
async def test_async_add_multiple_tasks(async_service):
    tasks = [Task(task_id=f"task{i}", func=async_simple_add, args=(i, i)) for i in range(3)]

    async_service.start()
    async_service.add_tasks(tasks)
    await asyncio.sleep(WAIT_TIME)

    results = async_service.get_results()
    assert len(results) == 3
    assert results["task0"] == 0
    assert results["task1"] == 2
    assert results["task2"] == 4


@pytest.mark.asyncio
async def test_async_handle_exception(async_service):
    task = Task(task_id="async_failing_task", func=async_failing_task)

    async_service.start()
    async_service.add_task(task)
    await asyncio.sleep(WAIT_TIME)

    result = async_service.get_result("async_failing_task")
    assert result is None
    async_service.logger.error.assert_called_once()


def test_threading_add_task_starts_service(threading_service):
    assert not threading_service.is_running
    task = Task(task_id="task_start", func=simple_add, args=(1, 1))
    threading_service.add_task(task)
    assert threading_service.is_running


def test_threading_add_tasks_starts_service(threading_service):
    assert not threading_service.is_running
    tasks = [Task(task_id=f"task{i}", func=simple_add, args=(i, i)) for i in range(3)]
    threading_service.add_tasks(tasks)
    assert threading_service.is_running


def test_threading_get_results_with_max_results(threading_service):
    tasks = [Task(task_id=f"task{i}", func=simple_add, args=(i, i)) for i in range(5)]
    threading_service.start()
    threading_service.add_tasks(tasks)
    sleep(WAIT_TIME)

    results = threading_service.get_results(max_results=3)
    assert len(results) == 3
    assert "task0" in results and "task1" in results and "task2" in results
    remaining_results = threading_service.get_results()
    assert len(remaining_results) == 2
    assert "task3" in remaining_results and "task4" in remaining_results


def test_threading_stop(threading_service):
    tasks = [Task(task_id=f"task{i}", func=simple_add, args=(i, i)) for i in range(3)]
    threading_service.start()
    threading_service.add_tasks(tasks)
    sleep(WAIT_TIME)
    threading_service.stop()
    assert not threading_service.is_running
    assert threading_service.workers == []


@pytest.mark.asyncio
async def test_async_add_task_starts_service(async_service):
    assert not async_service.is_running
    task = Task(task_id="task_start", func=async_simple_add, args=(2, 2))
    async_service.add_task(task)
    await asyncio.sleep(0.0000001)  # DO NOT CHANGE
    assert async_service.is_running


@pytest.mark.asyncio
async def test_async_add_tasks_starts_service(async_service):
    assert not async_service.is_running
    tasks = [Task(task_id=f"task{i}", func=async_simple_add, args=(i, i)) for i in range(3)]
    async_service.add_tasks(tasks)
    await asyncio.sleep(0.0000001)  # DO NOT CHANGE
    assert async_service.is_running


@pytest.mark.asyncio
async def test_async_get_results_with_max_results(async_service):
    tasks = [Task(task_id=f"task{i}", func=async_simple_add, args=(i, i)) for i in range(5)]
    async_service.start()
    async_service.add_tasks(tasks)
    await asyncio.sleep(WAIT_TIME * 10)

    results = async_service.get_results(max_results=3)
    assert len(results) == 3
    assert "task0" in results and "task1" in results and "task2" in results
    remaining_results = async_service.get_results()
    assert len(remaining_results) == 2
    assert "task3" in remaining_results and "task4" in remaining_results


@pytest.mark.asyncio
async def test_async_service_stop(async_service):
    async_service.start()
    assert async_service.is_running
    assert async_service.thread is not None and async_service.thread.is_alive()

    async_service.stop()

    assert not async_service.is_running
    assert async_service.thread is None
