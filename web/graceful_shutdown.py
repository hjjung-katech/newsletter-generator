#!/usr/bin/env python3
"""
Graceful Shutdown Wrapper for Flask Application

This module provides a Flask application wrapper that integrates with the
ShutdownManager to ensure graceful application termination, especially
important for Windows exe environments.
"""

import logging
import threading
import time
import signal
import sys
import os
from typing import Optional, Callable, Any
from contextlib import contextmanager
from flask import Flask, request, g
import werkzeug.serving

# Import shutdown manager
try:
    from newsletter.utils.shutdown_manager import (
        get_shutdown_manager, 
        ShutdownPhase, 
        register_shutdown_task,
        is_shutdown_requested
    )
except ImportError:
    # Fallback if shutdown manager is not available
    print("[WARNING] ShutdownManager not available - graceful shutdown disabled")
    
    def get_shutdown_manager():
        return None
    
    class ShutdownPhase:
        STOPPING_NEW_REQUESTS = "stopping_new_requests"
        CLEANING_RESOURCES = "cleaning_resources"
    
    def register_shutdown_task(*args, **kwargs):
        return False
    
    def is_shutdown_requested():
        return False


logger = logging.getLogger(__name__)


class GracefulShutdownWrapper:
    """
    Wrapper for Flask application that provides graceful shutdown capabilities.
    
    Features:
    - Stops accepting new HTTP requests during shutdown
    - Waits for active requests to complete
    - Integrates with centralized ShutdownManager
    - Provides hooks for application-specific cleanup
    """
    
    def __init__(self, app: Flask, shutdown_timeout: float = 15.0):
        self.app = app
        self.shutdown_timeout = shutdown_timeout
        self.shutdown_manager = get_shutdown_manager()
        self._accepting_requests = True
        self._active_requests = set()
        self._request_counter_lock = threading.Lock()
        self._server_thread: Optional[threading.Thread] = None
        self._server = None
        
        # Register Flask-specific shutdown tasks
        if self.shutdown_manager:
            self._register_flask_shutdown_tasks()
        
        # Add Flask hooks
        self._setup_flask_hooks()
        
        logger.info("GracefulShutdownWrapper initialized")
    
    def _register_flask_shutdown_tasks(self):
        """Register Flask-specific shutdown tasks with the ShutdownManager"""
        
        # Phase 1: Stop accepting new requests
        register_shutdown_task(
            name="stop_accepting_requests",
            callback=self._stop_accepting_requests,
            phase=ShutdownPhase.STOPPING_NEW_REQUESTS,
            priority=10,  # High priority
            timeout=2.0
        )
        
        # Phase 2: Wait for active requests to complete (handled by ShutdownManager's wait phase)
        register_shutdown_task(
            name="wait_for_active_requests", 
            callback=self._wait_for_active_requests,
            phase=ShutdownPhase.WAITING_FOR_TASKS,
            priority=20,
            timeout=10.0
        )
        
        # Phase 3: Shutdown Flask server
        register_shutdown_task(
            name="shutdown_flask_server",
            callback=self._shutdown_flask_server,
            phase=ShutdownPhase.CLEANING_RESOURCES,
            priority=30,
            timeout=5.0
        )
        
        logger.debug("Flask shutdown tasks registered with ShutdownManager")
    
    def _setup_flask_hooks(self):
        """Setup Flask request hooks for tracking active requests"""
        
        @self.app.before_request
        def before_request():
            # Check if we're shutting down
            if not self._accepting_requests or is_shutdown_requested():
                logger.warning("Rejecting new request - application is shutting down")
                # Return a 503 Service Unavailable response
                from flask import Response
                return Response(
                    "Service temporarily unavailable - application is shutting down",
                    status=503,
                    headers={'Retry-After': '10'}
                )
            
            # Track this request
            request_id = id(request)
            with self._request_counter_lock:
                self._active_requests.add(request_id)
                g.request_id = request_id
            
            logger.debug(f"Started processing request {request_id}")
        
        @self.app.after_request
        def after_request(response):
            # Untrack this request
            request_id = getattr(g, 'request_id', None)
            if request_id:
                with self._request_counter_lock:
                    self._active_requests.discard(request_id)
                logger.debug(f"Completed processing request {request_id}")
            
            return response
        
        @self.app.teardown_request
        def teardown_request(exception):
            # Ensure request is untracked even if there was an exception
            request_id = getattr(g, 'request_id', None)
            if request_id:
                with self._request_counter_lock:
                    self._active_requests.discard(request_id)
                if exception:
                    logger.debug(f"Request {request_id} failed with exception: {exception}")
        
        logger.debug("Flask request hooks configured")
    
    def _stop_accepting_requests(self):
        """Stop accepting new HTTP requests"""
        logger.info("Stopping acceptance of new requests")
        self._accepting_requests = False
    
    def _wait_for_active_requests(self):
        """Wait for all active requests to complete"""
        logger.info("Waiting for active requests to complete...")
        
        start_time = time.time()
        timeout = 10.0  # 10 seconds to wait for requests
        
        while time.time() - start_time < timeout:
            with self._request_counter_lock:
                active_count = len(self._active_requests)
            
            if active_count == 0:
                logger.info("All active requests completed")
                return
            
            logger.debug(f"Waiting for {active_count} active requests to complete")
            time.sleep(0.1)
        
        # Timeout reached
        with self._request_counter_lock:
            remaining_count = len(self._active_requests)
        
        if remaining_count > 0:
            logger.warning(f"Timeout waiting for requests - {remaining_count} requests still active")
            # Log the request IDs for debugging
            with self._request_counter_lock:
                for req_id in self._active_requests:
                    logger.warning(f"  Active request: {req_id}")
        else:
            logger.info("All requests completed during wait period")
    
    def _shutdown_flask_server(self):
        """Shutdown the Flask development server"""
        if self._server:
            try:
                logger.info("Shutting down Flask server")
                
                # For werkzeug development server
                if hasattr(self._server, 'shutdown'):
                    self._server.shutdown()
                elif hasattr(self._server, 'server_close'):
                    self._server.server_close()
                
                logger.info("Flask server shutdown completed")
                
            except Exception as e:
                logger.error(f"Error shutting down Flask server: {e}")
        else:
            logger.debug("No Flask server to shutdown")
        
        # Force shutdown by calling os._exit as last resort
        def force_exit():
            import os
            import time
            time.sleep(1)  # Give other cleanup a chance
            logger.warning("Force exiting application")
            os._exit(0)  # Force exit without cleanup
        
        # Schedule force exit in background thread
        force_thread = threading.Thread(target=force_exit, daemon=True)
        force_thread.start()
    
    def run(self, host: str = '0.0.0.0', port: int = 8000, debug: bool = False, **options):
        """
        Run the Flask application with graceful shutdown support.
        
        This replaces the standard app.run() call and provides graceful shutdown.
        """
        
        if debug:
            logger.warning("Debug mode enabled - graceful shutdown may not work properly")
        
        # Configure logging for the server
        if not debug:
            # Reduce werkzeug logging noise in production
            werkzeug_logger = logging.getLogger('werkzeug')
            werkzeug_logger.setLevel(logging.WARNING)
        
        # Store server configuration
        self._host = host
        self._port = port
        self._debug = debug
        self._options = options
        
        logger.info(f"Starting Flask application on {host}:{port}")
        
        try:
            # Register this server thread with the shutdown manager
            if self.shutdown_manager:
                main_thread = threading.current_thread()
                self.shutdown_manager.register_thread("flask_main", main_thread)
            
            # Start the Flask application
            # Use threaded=True to handle multiple requests concurrently
            options.setdefault('threaded', True)
            options.setdefault('use_reloader', False)  # Disable reloader in production
            
            self.app.run(host=host, port=port, debug=debug, **options)
            
        except KeyboardInterrupt:
            logger.info("Received KeyboardInterrupt - initiating graceful shutdown")
            if self.shutdown_manager:
                self.shutdown_manager.shutdown()
        except Exception as e:
            logger.error(f"Flask application error: {e}", exc_info=True)
            raise
        finally:
            if self.shutdown_manager:
                self.shutdown_manager.unregister_thread("flask_main")
            logger.info("Flask application terminated")
    
    def get_status(self) -> dict:
        """Get current status of the graceful shutdown wrapper"""
        with self._request_counter_lock:
            active_requests = len(self._active_requests)
        
        return {
            "accepting_requests": self._accepting_requests,
            "active_requests": active_requests,
            "server_running": self._server is not None,
            "shutdown_manager_available": self.shutdown_manager is not None
        }
    
    @contextmanager
    def managed_resource(self, name: str, resource: Any, cleanup_func: Optional[Callable] = None):
        """
        Context manager for automatic resource registration and cleanup.
        
        Args:
            name: Name for the resource
            resource: The resource object
            cleanup_func: Optional cleanup function to call during shutdown
        """
        try:
            # Register cleanup if provided
            if cleanup_func and self.shutdown_manager:
                register_shutdown_task(
                    name=f"cleanup_{name}",
                    callback=cleanup_func,
                    phase=ShutdownPhase.CLEANING_RESOURCES,
                    priority=50
                )
            
            yield resource
            
        finally:
            # Resource cleanup happens automatically via shutdown tasks
            pass


def create_graceful_app(app: Flask, **kwargs) -> GracefulShutdownWrapper:
    """
    Factory function to create a graceful shutdown wrapper for a Flask app.
    
    Args:
        app: Flask application instance
        **kwargs: Additional arguments passed to GracefulShutdownWrapper
        
    Returns:
        GracefulShutdownWrapper instance
    """
    return GracefulShutdownWrapper(app, **kwargs)


# Monkey patch werkzeug to handle shutdown signals better
def _patch_werkzeug_server():
    """Patch werkzeug server to handle shutdown signals more gracefully"""
    try:
        import werkzeug.serving
        
        # Store original make_server function
        original_make_server = werkzeug.serving.make_server
        
        def patched_make_server(*args, **kwargs):
            server = original_make_server(*args, **kwargs)
            
            # Add custom signal handling
            def shutdown_handler(signum, frame):
                logger.info(f"Server received signal {signum} - starting graceful shutdown")
                if get_shutdown_manager():
                    get_shutdown_manager().shutdown()
                
                # Call original shutdown
                if hasattr(server, 'shutdown'):
                    server.shutdown()
            
            # Only set signal handlers if we're in the main thread
            if threading.current_thread() is threading.main_thread():
                try:
                    signal.signal(signal.SIGINT, shutdown_handler)
                    signal.signal(signal.SIGTERM, shutdown_handler)
                except ValueError:
                    # Signal only works in main thread
                    pass
            
            return server
        
        # Apply the patch
        werkzeug.serving.make_server = patched_make_server
        logger.debug("Werkzeug server patched for graceful shutdown")
        
    except Exception as e:
        logger.warning(f"Could not patch werkzeug server: {e}")


# Apply werkzeug patch on import
_patch_werkzeug_server()


# Convenience function for simple usage
def run_with_graceful_shutdown(app: Flask, **kwargs):
    """
    Simple function to run a Flask app with graceful shutdown.
    
    Usage:
        from web.graceful_shutdown import run_with_graceful_shutdown
        run_with_graceful_shutdown(app, host='0.0.0.0', port=8000)
    """
    wrapper = create_graceful_app(app)
    wrapper.run(**kwargs)