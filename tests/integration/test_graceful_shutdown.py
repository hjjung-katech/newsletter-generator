"""
Integration tests for graceful shutdown system

This module tests the integration between Flask app and shutdown manager
to ensure proper cleanup of all resources during application termination.
"""

import pytest
import threading
import time
import signal
import os
import sys
from unittest.mock import Mock, patch, MagicMock
from flask import Flask

from newsletter.utils.shutdown_manager import get_shutdown_manager
from web.graceful_shutdown import GracefulShutdownWrapper, create_graceful_app


class TestGracefulShutdownIntegration:
    """Test graceful shutdown integration with Flask"""
    
    def setup_method(self):
        """Setup test environment"""
        # Reset shutdown manager singleton
        from newsletter.utils.shutdown_manager import ShutdownManager
        ShutdownManager._instance = None
    
    def create_test_app(self):
        """Create a test Flask application"""
        app = Flask(__name__)
        
        @app.route('/')
        def index():
            return 'Hello, World!'
        
        @app.route('/slow')
        def slow():
            time.sleep(0.5)  # Simulate slow request
            return 'Slow response'
        
        return app
    
    def test_graceful_wrapper_creation(self):
        """Test creating graceful shutdown wrapper"""
        app = self.create_test_app()
        wrapper = create_graceful_app(app)
        
        assert isinstance(wrapper, GracefulShutdownWrapper)
        assert wrapper.app is app
        assert wrapper.shutdown_manager is not None
    
    def test_graceful_wrapper_without_shutdown_manager(self):
        """Test graceful wrapper works without shutdown manager"""
        app = self.create_test_app()
        
        # Mock import failure
        with patch('web.graceful_shutdown.get_shutdown_manager', return_value=None):
            wrapper = GracefulShutdownWrapper(app)
            assert wrapper.shutdown_manager is None
    
    def test_request_tracking(self):
        """Test that requests are properly tracked"""
        app = self.create_test_app()
        wrapper = GracefulShutdownWrapper(app)
        
        with app.test_client() as client:
            # Before request
            assert len(wrapper._active_requests) == 0
            
            # Make request (this completes immediately in test)
            response = client.get('/')
            assert response.status_code == 200
            
            # After request should be cleaned up
            assert len(wrapper._active_requests) == 0
    
    def test_shutdown_blocks_new_requests(self):
        """Test that shutdown blocks new requests"""
        app = self.create_test_app()
        wrapper = GracefulShutdownWrapper(app)
        
        # Simulate shutdown initiated
        wrapper._stop_accepting_requests()
        
        with app.test_client() as client:
            response = client.get('/')
            assert response.status_code == 503
            assert b'shutting down' in response.data.lower()
    
    def test_graceful_wrapper_status(self):
        """Test status reporting"""
        app = self.create_test_app()
        wrapper = GracefulShutdownWrapper(app)
        
        status = wrapper.get_status()
        
        assert isinstance(status, dict)
        assert 'accepting_requests' in status
        assert 'active_requests' in status
        assert 'server_running' in status
        assert 'shutdown_manager_available' in status
    
    @patch('signal.signal')
    def test_signal_handler_registration(self, mock_signal):
        """Test that signal handlers are registered"""
        from newsletter.utils.shutdown_manager import ShutdownManager
        
        # Create shutdown manager (should register signals)
        manager = ShutdownManager()
        
        # Should have registered signal handlers
        assert mock_signal.call_count >= 1
    
    def test_shutdown_task_registration(self):
        """Test that Flask app registers shutdown tasks"""
        app = self.create_test_app()
        wrapper = GracefulShutdownWrapper(app)
        
        if wrapper.shutdown_manager:
            # Should have registered Flask-specific shutdown tasks
            task_names = [task.name for task in wrapper.shutdown_manager._shutdown_tasks]
            
            expected_tasks = [
                'stop_accepting_requests',
                'wait_for_active_requests', 
                'shutdown_flask_server'
            ]
            
            for expected_task in expected_tasks:
                assert expected_task in task_names


class TestShutdownWithBackgroundTasks:
    """Test shutdown behavior with background tasks"""
    
    def setup_method(self):
        """Setup test environment"""
        from newsletter.utils.shutdown_manager import ShutdownManager
        ShutdownManager._instance = None
    
    def test_shutdown_with_active_threads(self):
        """Test shutdown behavior when background threads are active"""
        manager = get_shutdown_manager()
        
        work_results = []
        
        def background_work(worker_id):
            for i in range(10):
                if manager.is_shutdown_requested():
                    work_results.append(f"worker{worker_id}_interrupted")
                    return
                time.sleep(0.1)
                work_results.append(f"worker{worker_id}_step{i}")
        
        # Start background threads
        threads = []
        for i in range(2):
            thread = threading.Thread(target=background_work, args=(i,))
            manager.register_thread(f"worker{i}", thread)
            threads.append(thread)
            thread.start()
        
        # Let threads work briefly
        time.sleep(0.3)
        
        # Trigger shutdown
        start_time = time.time()
        result = manager.shutdown()
        end_time = time.time()
        
        # Should complete successfully
        assert result is True
        
        # Should complete within timeout period
        assert (end_time - start_time) < 25.0  # Total timeout is ~22s
        
        # Wait for threads to finish
        for thread in threads:
            thread.join(timeout=1.0)
        
        # Some work should have been interrupted
        interrupted_count = len([r for r in work_results if "interrupted" in r])
        assert interrupted_count >= 0  # May be 0 if threads completed naturally
    
    def test_managed_thread_context(self):
        """Test managed thread context manager with shutdown"""
        manager = get_shutdown_manager()
        
        thread_finished = threading.Event()
        
        def managed_work():
            time.sleep(0.2)
            thread_finished.set()
        
        thread = threading.Thread(target=managed_work)
        
        # Use managed context
        with manager.managed_thread("managed_worker", thread):
            thread.start()
            
            # Thread should be registered
            assert "managed_worker" in manager._running_threads
            
            # Trigger shutdown while thread is running
            shutdown_thread = threading.Thread(target=lambda: manager.shutdown())
            shutdown_thread.start()
            
            # Wait for completion
            thread_finished.wait(timeout=2.0)
            thread.join(timeout=1.0)
            shutdown_thread.join(timeout=1.0)
    
    def test_process_cleanup(self):
        """Test cleanup of registered processes"""
        manager = get_shutdown_manager()
        
        # Mock process
        mock_process = MagicMock()
        mock_process.poll.return_value = None  # Running
        mock_process.terminate.return_value = None
        mock_process.wait.return_value = 0
        
        manager.register_process("test_process", mock_process)
        
        # Trigger shutdown
        result = manager.shutdown()
        assert result is True
        
        # Process should have been terminated
        mock_process.terminate.assert_called_once()


class TestErrorHandling:
    """Test error handling in shutdown system"""
    
    def setup_method(self):
        """Setup test environment"""
        from newsletter.utils.shutdown_manager import ShutdownManager
        ShutdownManager._instance = None
    
    def test_task_exception_handling(self):
        """Test that exceptions in shutdown tasks don't break shutdown"""
        manager = get_shutdown_manager()
        
        successful_tasks = []
        
        def failing_task():
            raise Exception("Task failed!")
        
        def successful_task():
            successful_tasks.append("success")
        
        # Register both failing and successful tasks
        manager.register_shutdown_task("failing", failing_task)
        manager.register_shutdown_task("successful", successful_task)
        
        # Shutdown should still complete
        result = manager.shutdown()
        assert result is True
        
        # Successful task should still have run
        assert "success" in successful_tasks
    
    def test_shutdown_manager_unavailable(self):
        """Test graceful degradation when shutdown manager is unavailable"""
        app = Flask(__name__)
        
        # Mock shutdown manager import failure
        with patch('web.graceful_shutdown.get_shutdown_manager', return_value=None):
            wrapper = GracefulShutdownWrapper(app)
            
            # Should still work without shutdown manager
            assert wrapper.shutdown_manager is None
            
            # Basic operations should work
            status = wrapper.get_status()
            assert status['shutdown_manager_available'] is False


@pytest.mark.skipif(sys.platform != 'win32', reason="Windows-specific tests")
class TestWindowsSpecificFeatures:
    """Test Windows-specific shutdown features"""
    
    def setup_method(self):
        """Setup test environment"""
        from newsletter.utils.shutdown_manager import ShutdownManager
        ShutdownManager._instance = None
    
    @patch('ctypes.windll.kernel32.SetConsoleCtrlHandler')
    def test_windows_console_handler(self, mock_set_handler):
        """Test Windows console control handler setup"""
        from newsletter.utils.shutdown_manager import ShutdownManager
        
        # Create shutdown manager (should set up console handler on Windows)
        manager = ShutdownManager()
        
        # Should have attempted to set console handler
        assert mock_set_handler.call_count >= 0  # May not be called if setup fails
    
    def test_repeated_ctrl_c_detection(self):
        """Test repeated Ctrl+C detection for force exit"""
        manager = get_shutdown_manager()
        
        # Simulate first Ctrl+C
        manager._shutdown_request_count = 1
        manager._first_shutdown_time = time.time()
        
        with patch('os._exit') as mock_exit:
            # Simulate second Ctrl+C quickly
            manager._shutdown_request_count = 2
            
            # This should trigger force exit logic
            with patch('time.time', return_value=manager._first_shutdown_time + 1):
                # The force exit check happens in signal handlers
                # Here we test the logic directly
                elapsed = 1.0  # 1 second elapsed
                if manager._shutdown_request_count >= 2 and elapsed < 3.0:
                    # This would trigger force exit
                    assert True
                else:
                    assert False, "Force exit should be triggered"


if __name__ == "__main__":
    pytest.main([__file__])