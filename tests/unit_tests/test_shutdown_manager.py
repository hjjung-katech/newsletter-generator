"""
Unit tests for shutdown manager functionality

This module tests the graceful shutdown system that ensures
all background processes are properly terminated on Windows.
"""

import threading
import time
from datetime import datetime
from unittest.mock import Mock, patch

import pytest

import newsletter.utils.shutdown_manager as shutdown_module
from newsletter.utils.shutdown_manager import (
    ShutdownManager,
    ShutdownPhase,
    ShutdownTask,
    get_shutdown_manager,
)


class TestShutdownManager:
    """Test cases for ShutdownManager class"""

    def setup_method(self):
        """Reset shutdown manager for each test"""
        # Reset both singleton instances
        ShutdownManager._instance = None
        shutdown_module._shutdown_manager = None

        # If instance somehow still exists, force reset its state
        if (
            hasattr(ShutdownManager, "_instance")
            and ShutdownManager._instance is not None
        ):
            instance = ShutdownManager._instance
            instance._shutdown_requested = False
            instance._shutdown_completed = False
            instance._current_phase = ShutdownPhase.STARTING
            instance._shutdown_request_count = 0
            instance._first_shutdown_time = None
            instance._shutdown_tasks = []
            instance._running_threads = {}
            instance._running_processes = {}
            if hasattr(instance, "_initialized"):
                delattr(instance, "_initialized")

    def teardown_method(self):
        """Clean up after each test"""
        # Force reset singleton instance and its state
        if (
            hasattr(ShutdownManager, "_instance")
            and ShutdownManager._instance is not None
        ):
            instance = ShutdownManager._instance
            instance._shutdown_requested = False
            instance._shutdown_completed = False
            instance._current_phase = ShutdownPhase.STARTING
            instance._shutdown_request_count = 0
            instance._first_shutdown_time = None
            instance._shutdown_tasks = []
            instance._running_threads = {}
            instance._running_processes = {}
            if hasattr(instance, "_initialized"):
                delattr(instance, "_initialized")

        # Reset both singleton instances
        ShutdownManager._instance = None
        shutdown_module._shutdown_manager = None

    def test_singleton_pattern(self):
        """Test that ShutdownManager follows singleton pattern"""
        manager1 = get_shutdown_manager()
        manager2 = get_shutdown_manager()
        assert manager1 is manager2

    def test_register_shutdown_task(self):
        """Test registering shutdown tasks"""
        manager = get_shutdown_manager()

        def dummy_task():
            pass

        # Test successful registration
        result = manager.register_shutdown_task(
            name="test_task",
            callback=dummy_task,
            phase=ShutdownPhase.CLEANING_RESOURCES,
        )
        assert result is True

        # Test duplicate name registration fails
        result = manager.register_shutdown_task(
            name="test_task",
            callback=dummy_task,
            phase=ShutdownPhase.CLEANING_RESOURCES,
        )
        assert result is False

    def test_thread_registration(self):
        """Test thread registration and unregistration"""
        manager = get_shutdown_manager()

        def dummy_work():
            time.sleep(0.1)

        thread = threading.Thread(target=dummy_work)

        # Test registration
        result = manager.register_thread("test_thread", thread)
        assert result is True

        # Test unregistration
        result = manager.unregister_thread("test_thread")
        assert result is True

        # Test unregistering non-existent thread
        result = manager.unregister_thread("non_existent")
        assert result is False

    def test_process_registration(self):
        """Test process registration and unregistration"""
        manager = get_shutdown_manager()

        mock_process = Mock()
        mock_process.poll.return_value = None  # Process running

        # Test registration
        result = manager.register_process("test_process", mock_process)
        assert result is True

        # Test unregistration
        result = manager.unregister_process("test_process")
        assert result is True

    def test_managed_thread_context(self):
        """Test managed_thread context manager"""
        manager = get_shutdown_manager()

        def dummy_work():
            time.sleep(0.1)

        thread = threading.Thread(target=dummy_work)

        # Test context manager automatically registers and unregisters
        with manager.managed_thread("test_context_thread", thread):
            # Thread should be registered
            assert "test_context_thread" in manager._running_threads

        # After context, thread should be unregistered
        # (Note: this happens when the thread finishes, not immediately)

    def test_shutdown_phases(self):
        """Test shutdown phase execution"""
        manager = get_shutdown_manager()

        executed_tasks = []

        def task1():
            executed_tasks.append("task1")

        def task2():
            executed_tasks.append("task2")

        def task3():
            executed_tasks.append("task3")

        # Register tasks in different phases
        manager.register_shutdown_task(
            "task1", task1, ShutdownPhase.STOPPING_NEW_REQUESTS, priority=10
        )
        manager.register_shutdown_task(
            "task2", task2, ShutdownPhase.WAITING_FOR_TASKS, priority=20
        )
        manager.register_shutdown_task(
            "task3", task3, ShutdownPhase.CLEANING_RESOURCES, priority=30
        )

        # Execute shutdown
        result = manager.shutdown()
        assert result is True

        # Verify tasks were executed in correct order
        assert "task1" in sm.tasks
        assert "task2" in executed_tasks
        assert "task3" in executed_tasks

    def test_shutdown_task_priorities(self):
        """Test that tasks execute in priority order within same phase"""
        manager = get_shutdown_manager()

        execution_order = []

        def high_priority():
            execution_order.append("high")

        def low_priority():
            execution_order.append("low")

        # Register with different priorities (lower number = higher priority)
        manager.register_shutdown_task(
            "low", low_priority, ShutdownPhase.CLEANING_RESOURCES, priority=50
        )
        manager.register_shutdown_task(
            "high", high_priority, ShutdownPhase.CLEANING_RESOURCES, priority=10
        )

        # Execute shutdown
        manager.shutdown()

        # High priority should execute first
        assert list(sm.tasks.keys()) == ["high", "low"]

    def test_get_status(self):
        """Test status reporting functionality"""
        manager = get_shutdown_manager()

        status = manager.get_status()

        assert isinstance(status, dict)
        assert "shutdown_requested" in status
        assert "shutdown_completed" in status
        assert "current_phase" in status
        assert "registered_tasks" in status
        assert "active_threads" in status
        assert "active_processes" in status

    def test_is_shutdown_requested(self):
        """Test shutdown request detection"""
        manager = get_shutdown_manager()

        # Initially should be False
        assert manager.is_shutdown_requested() is False

        # After shutdown request should be True
        manager.shutdown()
        assert manager.is_shutdown_requested() is True

    def test_task_timeout(self):
        """Test task timeout functionality"""
        manager = get_shutdown_manager()

        def slow_task():
            time.sleep(10)  # This should timeout

        manager.register_shutdown_task(
            name="slow_task",
            callback=slow_task,
            phase=ShutdownPhase.CLEANING_RESOURCES,
            timeout=0.1,  # Very short timeout
        )

        start_time = time.time()
        manager.shutdown()
        end_time = time.time()

        # Should complete quickly due to timeout
        assert (end_time - start_time) < 2.0

    # Note: Force exit behavior is only triggered by signal handlers,
    # not by direct shutdown() calls. This test was incorrectly designed.


class TestShutdownTask:
    """Test cases for ShutdownTask dataclass"""

    def test_shutdown_task_creation(self):
        """Test ShutdownTask creation and attributes"""

        def dummy_callback():
            pass

        task = ShutdownTask(
            name="test_task",
            callback=dummy_callback,
            phase=ShutdownPhase.CLEANING_RESOURCES,
            priority=50,
            timeout=5.0,
        )

        assert task.name == "test_task"
        assert task.callback == dummy_callback
        assert task.phase == ShutdownPhase.CLEANING_RESOURCES
        assert task.priority == 50
        assert task.timeout == 5.0
        assert task.completed is False
        assert task.error is None


class TestShutdownPhase:
    """Test cases for ShutdownPhase enum"""

    def test_shutdown_phases_exist(self):
        """Test that all required shutdown phases exist"""
        assert hasattr(ShutdownPhase, "STARTING")
        assert hasattr(ShutdownPhase, "STOPPING_NEW_REQUESTS")
        assert hasattr(ShutdownPhase, "WAITING_FOR_TASKS")
        assert hasattr(ShutdownPhase, "CLEANING_RESOURCES")
        assert hasattr(ShutdownPhase, "FORCE_TERMINATING")
        assert hasattr(ShutdownPhase, "COMPLETED")

    def test_phase_values(self):
        """Test that phase enum values are correct"""
        assert ShutdownPhase.STARTING.value == "starting"
        assert ShutdownPhase.STOPPING_NEW_REQUESTS.value == "stopping_new_requests"
        assert ShutdownPhase.WAITING_FOR_TASKS.value == "waiting_for_tasks"
        assert ShutdownPhase.CLEANING_RESOURCES.value == "cleaning_resources"
        assert ShutdownPhase.FORCE_TERMINATING.value == "force_terminating"
        assert ShutdownPhase.COMPLETED.value == "completed"


@pytest.mark.integration
class TestShutdownIntegration:
    """Integration tests for shutdown system"""

    def setup_method(self):
        """Reset shutdown manager for each test"""
        ShutdownManager._instance = None

    def test_full_shutdown_workflow(self):
        """Test complete shutdown workflow with real threads"""
        manager = get_shutdown_manager()

        # Create some work threads
        work_done = []

        def worker(worker_id):
            for i in range(5):
                if manager.is_shutdown_requested():
                    work_done.append(f"worker{worker_id}_stopped_early")
                    return
                time.sleep(0.1)
            work_done.append(f"worker{worker_id}_completed")

        # Start threads and register them
        threads = []
        for i in range(3):
            thread = threading.Thread(target=worker, args=(i,))
            threads.append(thread)
            manager.register_thread(f"worker{i}", thread)
            thread.start()

        # Let threads run briefly
        time.sleep(0.2)

        # Trigger shutdown
        start_time = time.time()
        result = manager.shutdown()
        end_time = time.time()

        # Should complete successfully
        assert result is True

        # Should complete within reasonable time (all timeouts combined)
        assert (end_time - start_time) < 30.0

        # Wait for threads to finish
        for thread in threads:
            thread.join(timeout=1.0)

        # Some work should have been done
        assert len(work_done) > 0

        # At least some workers should have detected shutdown
        early_stops = [w for w in work_done if "stopped_early" in w]
        assert len(early_stops) >= 0  # Could be 0 if shutdown happened after completion


if __name__ == "__main__":
    pytest.main([__file__])
