#!/usr/bin/env python3
"""
Centralized Shutdown Manager for Newsletter Generator

This module provides a comprehensive shutdown management system that ensures
all background processes, threads, and resources are properly cleaned up
when the application terminates, especially in Windows exe environments.
"""

import threading
import time
import logging
import signal
import os
import sys
import atexit
from typing import Dict, List, Callable, Optional, Any
from enum import Enum
from dataclasses import dataclass, field
from contextlib import contextmanager


class ShutdownPhase(Enum):
    """Defines the phases of shutdown process"""
    STARTING = "starting"
    STOPPING_NEW_REQUESTS = "stopping_new_requests" 
    WAITING_FOR_TASKS = "waiting_for_tasks"
    CLEANING_RESOURCES = "cleaning_resources"
    FORCE_TERMINATING = "force_terminating"
    COMPLETED = "completed"


@dataclass
class ShutdownTask:
    """Represents a single shutdown task"""
    name: str
    callback: Callable
    phase: ShutdownPhase
    priority: int = 50  # Lower number = higher priority
    timeout: float = 5.0
    args: tuple = field(default_factory=tuple)
    kwargs: dict = field(default_factory=dict)
    completed: bool = False
    error: Optional[Exception] = None


class ShutdownManager:
    """
    Central shutdown manager that coordinates graceful application termination.
    
    Manages shutdown in phases:
    1. Stop accepting new requests (5s timeout)
    2. Wait for running tasks to complete (10s timeout)
    3. Clean up resources (5s timeout)
    4. Force terminate remaining processes (2s timeout)
    """
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if hasattr(self, '_initialized'):
            return
        
        self._initialized = True
        self._shutdown_tasks: List[ShutdownTask] = []
        self._running_threads: Dict[str, threading.Thread] = {}
        self._running_processes: Dict[str, Any] = {}
        self._shutdown_requested = False
        self._shutdown_completed = False
        self._current_phase = ShutdownPhase.STARTING
        self._lock = threading.RLock()
        self._logger = logging.getLogger(__name__)
        self._shutdown_request_count = 0
        self._first_shutdown_time = None
        
        # Safe logging wrapper to handle closed streams during test teardown
        self._safe_log = self._create_safe_logger()
        
        # Phase timeouts (seconds)
        self.phase_timeouts = {
            ShutdownPhase.STOPPING_NEW_REQUESTS: 5.0,
            ShutdownPhase.WAITING_FOR_TASKS: 10.0,
            ShutdownPhase.CLEANING_RESOURCES: 5.0,
            ShutdownPhase.FORCE_TERMINATING: 2.0
        }
        
        # Setup signal handlers and exit hooks
        self._setup_signal_handlers()
        self._setup_exit_hooks()
        
        self._safe_log.info("ShutdownManager initialized")
    
    def _create_safe_logger(self):
        """Create a safe logging wrapper that handles closed streams"""
        class SafeLogger:
            def __init__(self, logger):
                self._logger = logger
            
            def _safe_log(self, level, msg, *args, **kwargs):
                try:
                    getattr(self._logger, level)(msg, *args, **kwargs)
                except (ValueError, OSError, Exception):
                    # Stream closed during test teardown or any other logging error - safe to ignore
                    pass
            
            def info(self, msg, *args, **kwargs):
                self._safe_log('info', msg, *args, **kwargs)
            
            def warning(self, msg, *args, **kwargs):
                self._safe_log('warning', msg, *args, **kwargs)
            
            def error(self, msg, *args, **kwargs):
                self._safe_log('error', msg, *args, **kwargs)
            
            def debug(self, msg, *args, **kwargs):
                self._safe_log('debug', msg, *args, **kwargs)
        
        return SafeLogger(self._logger)
    
    def _setup_signal_handlers(self):
        """Setup signal handlers for graceful shutdown"""
        def signal_handler(signum, frame):
            signal_name = signal.Signals(signum).name if hasattr(signal, 'Signals') else str(signum)
            self._safe_log.info(f"Received signal {signal_name} ({signum})")
            
            with self._lock:
                self._shutdown_request_count += 1
                if self._first_shutdown_time is None:
                    self._first_shutdown_time = time.time()
                
                # If this is the second Ctrl+C within 3 seconds, force exit
                if self._shutdown_request_count >= 2:
                    elapsed = time.time() - self._first_shutdown_time
                    if elapsed < 3.0:
                        self._safe_log.warning(f"Second shutdown signal received within {elapsed:.1f}s - forcing exit")
                        import os
                        os._exit(1)
                
                # If shutdown is already completed but we're still getting signals, force exit
                if self._shutdown_completed:
                    self._safe_log.warning("Shutdown already completed but still receiving signals - forcing exit")
                    import os
                    os._exit(1)
            
            self.shutdown()
        
        # Handle common termination signals
        signals_to_handle = [signal.SIGINT, signal.SIGTERM]
        
        # Windows-specific signal handling
        if sys.platform.startswith('win'):
            try:
                # Add Windows-specific signals if available
                if hasattr(signal, 'SIGBREAK'):
                    signals_to_handle.append(signal.SIGBREAK)
                
                # Setup console control handler for Windows
                self._setup_windows_console_handler()
                    
            except Exception as e:
                self._safe_log.warning(f"Failed to setup Windows-specific signal handling: {e}")
        
        for sig in signals_to_handle:
            try:
                signal.signal(sig, signal_handler)
                self._safe_log.debug(f"Signal handler registered for {sig}")
            except (OSError, ValueError) as e:
                self._safe_log.warning(f"Could not register signal handler for {sig}: {e}")
    
    def _setup_windows_console_handler(self):
        """Setup Windows console control handler"""
        if not sys.platform.startswith('win'):
            return
            
        try:
            import ctypes
            from ctypes import wintypes
            
            kernel32 = ctypes.windll.kernel32
            
            def console_ctrl_handler(ctrl_type):
                """Handle Windows console control events"""
                ctrl_types = {
                    0: "CTRL_C_EVENT",
                    1: "CTRL_BREAK_EVENT", 
                    2: "CTRL_CLOSE_EVENT",
                    5: "CTRL_LOGOFF_EVENT",
                    6: "CTRL_SHUTDOWN_EVENT"
                }
                
                ctrl_name = ctrl_types.get(ctrl_type, f"UNKNOWN({ctrl_type})")
                self._safe_log.info(f"Windows console control event: {ctrl_name}")
                
                # Handle repeated Ctrl+C for force exit
                with self._lock:
                    self._shutdown_request_count += 1
                    if self._first_shutdown_time is None:
                        self._first_shutdown_time = time.time()
                    
                    # If this is the second Ctrl+C within 3 seconds, force exit
                    if self._shutdown_request_count >= 2:
                        elapsed = time.time() - self._first_shutdown_time
                        if elapsed < 3.0:
                            self._safe_log.warning(f"Second console event received within {elapsed:.1f}s - forcing exit")
                            import os
                            os._exit(1)
                    
                    # If shutdown is already completed but we're still getting signals, force exit
                    if self._shutdown_completed:
                        self._safe_log.warning("Shutdown already completed but still receiving console events - forcing exit")
                        import os
                        os._exit(1)
                
                # Start graceful shutdown
                self.shutdown()
                
                # Return True to indicate we handled the event
                return True
            
            # Define the handler function type
            HANDLER_ROUTINE = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.DWORD)
            handler = HANDLER_ROUTINE(console_ctrl_handler)
            
            # Register the handler
            if kernel32.SetConsoleCtrlHandler(handler, True):
                self._safe_log.debug("Windows console control handler registered successfully")
                # Keep a reference to prevent garbage collection
                self._console_handler = handler
            else:
                self._safe_log.warning("Failed to register Windows console control handler")
                
        except Exception as e:
            self._safe_log.warning(f"Could not setup Windows console handler: {e}")
    
    def _setup_exit_hooks(self):
        """Setup exit hooks for cleanup"""
        # Skip atexit registration during pytest to avoid logging errors during teardown
        import sys
        if "pytest" in sys.modules or os.getenv("TESTING") == "1":
            self._safe_log.debug("Skipping exit hooks registration in test mode")
            return
        
        atexit.register(self.shutdown)
        self._safe_log.debug("Exit hooks registered")
    
    def register_shutdown_task(
        self, 
        name: str, 
        callback: Callable, 
        phase: ShutdownPhase = ShutdownPhase.CLEANING_RESOURCES,
        priority: int = 50,
        timeout: float = 5.0,
        *args, 
        **kwargs
    ) -> bool:
        """
        Register a shutdown task to be executed during application termination.
        
        Args:
            name: Unique name for the task
            callback: Function to call during shutdown
            phase: Which shutdown phase to execute this task in
            priority: Task priority (lower number = higher priority)
            timeout: Maximum time to wait for task completion
            *args, **kwargs: Arguments to pass to the callback
            
        Returns:
            bool: True if task was registered successfully
        """
        with self._lock:
            if self._shutdown_requested:
                self._safe_log.warning(f"Cannot register task '{name}' - shutdown already requested")
                return False
            
            # Check for duplicate names
            if any(task.name == name for task in self._shutdown_tasks):
                self._safe_log.warning(f"Task '{name}' already registered")
                return False
            
            task = ShutdownTask(
                name=name,
                callback=callback, 
                phase=phase,
                priority=priority,
                timeout=timeout,
                args=args,
                kwargs=kwargs
            )
            
            self._shutdown_tasks.append(task)
            self._safe_log.debug(f"Registered shutdown task: {name} (phase: {phase.value}, priority: {priority})")
            return True
    
    def register_thread(self, name: str, thread: threading.Thread) -> bool:
        """Register a thread for tracking and graceful shutdown"""
        with self._lock:
            if self._shutdown_requested:
                self._safe_log.warning(f"Cannot register thread '{name}' - shutdown already requested")
                return False
                
            self._running_threads[name] = thread
            self._safe_log.debug(f"Registered thread: {name}")
            return True
    
    def unregister_thread(self, name: str) -> bool:
        """Unregister a thread (called when thread completes normally)"""
        with self._lock:
            if name in self._running_threads:
                del self._running_threads[name]
                self._safe_log.debug(f"Unregistered thread: {name}")
                return True
            return False
    
    def register_process(self, name: str, process: Any) -> bool:
        """Register a subprocess or process for tracking"""
        with self._lock:
            if self._shutdown_requested:
                self._safe_log.warning(f"Cannot register process '{name}' - shutdown already requested")
                return False
                
            self._running_processes[name] = process
            self._safe_log.debug(f"Registered process: {name}")
            return True
    
    def unregister_process(self, name: str) -> bool:
        """Unregister a process (called when process completes normally)"""
        with self._lock:
            if name in self._running_processes:
                del self._running_processes[name]
                self._safe_log.debug(f"Unregistered process: {name}")
                return True
            return False
    
    @contextmanager
    def managed_thread(self, name: str, thread: threading.Thread):
        """Context manager for automatic thread registration/cleanup"""
        try:
            self.register_thread(name, thread)
            yield thread
        finally:
            self.unregister_thread(name)
    
    @contextmanager 
    def managed_process(self, name: str, process: Any):
        """Context manager for automatic process registration/cleanup"""
        try:
            self.register_process(name, process)
            yield process
        finally:
            self.unregister_process(name)
    
    def is_shutdown_requested(self) -> bool:
        """Check if shutdown has been requested"""
        return self._shutdown_requested
    
    def is_shutdown_completed(self) -> bool:
        """Check if shutdown has completed"""
        return self._shutdown_completed
    
    def get_current_phase(self) -> ShutdownPhase:
        """Get the current shutdown phase"""
        return self._current_phase
    
    def shutdown(self, force: bool = False) -> bool:
        """
        Initiate graceful shutdown process.
        
        Args:
            force: If True, skip graceful phases and force immediate termination
            
        Returns:
            bool: True if shutdown completed successfully
        """
        with self._lock:
            if self._shutdown_completed:
                self._safe_log.debug("Shutdown already completed")
                return True
                
            if self._shutdown_requested and not force:
                self._safe_log.debug("Shutdown already in progress")
                return False
            
            self._shutdown_requested = True
            
        self._safe_log.info("=== GRACEFUL SHUTDOWN INITIATED ===")
        
        if force:
            self._safe_log.warning("Force shutdown requested - skipping graceful phases")
            return self._force_shutdown()
        
        try:
            # Execute shutdown phases in order
            phases = [
                ShutdownPhase.STOPPING_NEW_REQUESTS,
                ShutdownPhase.WAITING_FOR_TASKS, 
                ShutdownPhase.CLEANING_RESOURCES,
                ShutdownPhase.FORCE_TERMINATING
            ]
            
            for phase in phases:
                if not self._execute_phase(phase):
                    self._safe_log.error(f"Phase {phase.value} failed or timed out")
                    # Continue to next phase anyway
            
            self._current_phase = ShutdownPhase.COMPLETED
            self._shutdown_completed = True
            
            self._safe_log.info("=== GRACEFUL SHUTDOWN COMPLETED ===")
            return True
            
        except Exception as e:
            self._safe_log.error(f"Error during shutdown: {e}", exc_info=True)
            return self._force_shutdown()
    
    def _execute_phase(self, phase: ShutdownPhase) -> bool:
        """Execute all tasks in a specific shutdown phase"""
        self._current_phase = phase
        phase_timeout = self.phase_timeouts.get(phase, 5.0)
        
        self._safe_log.info(f"--- Starting phase: {phase.value} (timeout: {phase_timeout}s) ---")
        
        # Get tasks for this phase, sorted by priority
        phase_tasks = [task for task in self._shutdown_tasks if task.phase == phase and not task.completed]
        phase_tasks.sort(key=lambda t: t.priority)
        
        if not phase_tasks:
            self._safe_log.debug(f"No tasks registered for phase: {phase.value}")
            return True
        
        phase_start = time.time()
        
        for task in phase_tasks:
            remaining_time = phase_timeout - (time.time() - phase_start)
            
            if remaining_time <= 0:
                self._safe_log.warning(f"Phase {phase.value} timeout reached before task '{task.name}'")
                break
            
            task_timeout = min(task.timeout, remaining_time)
            success = self._execute_task(task, task_timeout)
            
            if not success:
                self._safe_log.warning(f"Task '{task.name}' failed or timed out")
                # Continue with remaining tasks
        
        # Special handling for waiting phase - check if threads/processes are done
        if phase == ShutdownPhase.WAITING_FOR_TASKS:
            self._wait_for_background_tasks(phase_timeout - (time.time() - phase_start))
        
        phase_duration = time.time() - phase_start
        self._safe_log.info(f"--- Completed phase: {phase.value} in {phase_duration:.2f}s ---")
        
        return True
    
    def _execute_task(self, task: ShutdownTask, timeout: float) -> bool:
        """Execute a single shutdown task with timeout"""
        self._safe_log.debug(f"Executing task: {task.name} (timeout: {timeout:.2f}s)")
        
        def run_task():
            try:
                task.callback(*task.args, **task.kwargs)
                task.completed = True
            except Exception as e:
                task.error = e
                self._safe_log.error(f"Error in shutdown task '{task.name}': {e}", exc_info=True)
        
        thread = threading.Thread(target=run_task, name=f"shutdown-{task.name}")
        thread.daemon = True
        thread.start()
        
        thread.join(timeout)
        
        if thread.is_alive():
            self._safe_log.warning(f"Task '{task.name}' timed out after {timeout:.2f}s")
            return False
        
        success = task.completed and task.error is None
        if success:
            self._safe_log.debug(f"Task '{task.name}' completed successfully")
        
        return success
    
    def _wait_for_background_tasks(self, timeout: float) -> bool:
        """Wait for all registered background threads and processes to complete"""
        self._safe_log.info("Waiting for background tasks to complete...")
        
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            with self._lock:
                # Check threads
                active_threads = []
                for name, thread in list(self._running_threads.items()):
                    if thread.is_alive():
                        active_threads.append(name)
                    else:
                        # Thread finished, remove from tracking
                        del self._running_threads[name]
                
                # Check processes  
                active_processes = []
                for name, process in list(self._running_processes.items()):
                    try:
                        if hasattr(process, 'poll') and process.poll() is None:
                            active_processes.append(name)
                        elif hasattr(process, 'is_alive') and process.is_alive():
                            active_processes.append(name)
                        else:
                            # Process finished, remove from tracking
                            del self._running_processes[name]
                    except Exception:
                        # Process might be invalid, remove it
                        del self._running_processes[name]
                
                if not active_threads and not active_processes:
                    self._safe_log.info("All background tasks completed")
                    return True
                
                self._safe_log.debug(f"Waiting for {len(active_threads)} threads and {len(active_processes)} processes")
            
            time.sleep(0.1)  # Small delay before checking again
        
        # Timeout reached
        with self._lock:
            if self._running_threads or self._running_processes:
                self._safe_log.warning(f"Timeout waiting for background tasks: "
                                    f"{len(self._running_threads)} threads, {len(self._running_processes)} processes still running")
                
                for name in self._running_threads:
                    self._safe_log.warning(f"  Thread still running: {name}")
                for name in self._running_processes:
                    self._safe_log.warning(f"  Process still running: {name}")
        
        return False
    
    def _force_shutdown(self) -> bool:
        """Force immediate shutdown of all processes and threads"""
        self._safe_log.warning("=== FORCE SHUTDOWN INITIATED ===")
        
        # Terminate all registered processes
        with self._lock:
            for name, process in list(self._running_processes.items()):
                try:
                    self._safe_log.info(f"Force terminating process: {name}")
                    if hasattr(process, 'terminate'):
                        process.terminate()
                        # Give process a chance to terminate gracefully
                        if hasattr(process, 'wait'):
                            try:
                                process.wait(timeout=1.0)
                            except Exception:
                                # Process didn't terminate, try to kill it
                                if hasattr(process, 'kill'):
                                    process.kill()
                except Exception as e:
                    self._safe_log.error(f"Error terminating process '{name}': {e}")
                finally:
                    del self._running_processes[name]
        
        # Force shutdown threads (can't really kill them, but we'll stop waiting)
        with self._lock:
            if self._running_threads:
                self._safe_log.warning(f"Cannot force terminate {len(self._running_threads)} threads - they will be abandoned")
                for name in self._running_threads:
                    self._safe_log.warning(f"  Abandoning thread: {name}")
                self._running_threads.clear()
        
        self._current_phase = ShutdownPhase.COMPLETED
        self._shutdown_completed = True
        
        self._safe_log.warning("=== FORCE SHUTDOWN COMPLETED ===")
        return True
    
    def get_status(self) -> Dict[str, Any]:
        """Get current shutdown manager status"""
        with self._lock:
            return {
                "shutdown_requested": self._shutdown_requested,
                "shutdown_completed": self._shutdown_completed,
                "current_phase": self._current_phase.value,
                "registered_tasks": len(self._shutdown_tasks),
                "completed_tasks": len([t for t in self._shutdown_tasks if t.completed]),
                "active_threads": len(self._running_threads),
                "active_processes": len(self._running_processes),
                "thread_names": list(self._running_threads.keys()),
                "process_names": list(self._running_processes.keys())
            }


# Global instance
_shutdown_manager: Optional[ShutdownManager] = None


def get_shutdown_manager() -> ShutdownManager:
    """Get the global shutdown manager instance"""
    global _shutdown_manager
    if _shutdown_manager is None:
        _shutdown_manager = ShutdownManager()
    return _shutdown_manager


# Convenience functions for common operations
def register_shutdown_task(*args, **kwargs) -> bool:
    """Register a shutdown task using the global manager"""
    return get_shutdown_manager().register_shutdown_task(*args, **kwargs)


def register_thread(name: str, thread: threading.Thread) -> bool:
    """Register a thread using the global manager"""
    return get_shutdown_manager().register_thread(name, thread)


def register_process(name: str, process: Any) -> bool:
    """Register a process using the global manager"""  
    return get_shutdown_manager().register_process(name, process)


def is_shutdown_requested() -> bool:
    """Check if shutdown has been requested"""
    return get_shutdown_manager().is_shutdown_requested()


def shutdown(force: bool = False) -> bool:
    """Initiate graceful shutdown"""
    return get_shutdown_manager().shutdown(force=force)


def managed_thread(name: str, thread: threading.Thread):
    """Context manager for automatic thread registration"""
    return get_shutdown_manager().managed_thread(name, thread)


def managed_process(name: str, process: Any):
    """Context manager for automatic process registration"""
    return get_shutdown_manager().managed_process(name, process)