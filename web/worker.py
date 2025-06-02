#!/usr/bin/env python3
"""
Redis Queue Worker for Newsletter Generator
Processes background tasks for newsletter generation
"""

import os
import sys
import redis
from rq import Worker, Queue, Connection

# Queue name used by Redis Queue
QUEUE_NAME = os.getenv("RQ_QUEUE", "default")

# Add current directory to path
sys.path.insert(0, os.path.dirname(__file__))

# Import task functions
from tasks import generate_newsletter_task

if __name__ == '__main__':
    # Get Redis connection from environment
    redis_url = os.environ.get('REDIS_URL', 'redis://localhost:6379/0')
    redis_conn = redis.from_url(redis_url)

    # Create queues
    queues = [Queue(QUEUE_NAME, connection=redis_conn)]
    
    # Start worker
    worker = Worker(queues, connection=redis_conn)
    print("Starting RQ worker...")
    worker.work()
