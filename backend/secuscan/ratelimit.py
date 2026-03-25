"""
Rate limiting for task execution
"""

from collections import defaultdict
from datetime import datetime, timedelta
from typing import Tuple, Dict, List
import asyncio


class RateLimiter:
    """Rate limiter for controlling task execution frequency"""
    
    def __init__(self):
        self.task_history: Dict[str, List[datetime]] = defaultdict(list)
        self.lock = asyncio.Lock()
    
    async def can_execute(
        self, 
        plugin_id: str, 
        max_per_hour: int = 50
    ) -> Tuple[bool, str]:
        """
        Check if a task can be executed based on rate limits.
        
        Args:
            plugin_id: Plugin identifier
            max_per_hour: Maximum tasks per hour for this plugin
        
        Returns:
            Tuple of (allowed, error_message)
        """
        async with self.lock:
            now = datetime.now()
            hour_ago = now - timedelta(hours=1)
            
            # Clean old entries
            self.task_history[plugin_id] = [
                ts for ts in self.task_history[plugin_id]
                if ts > hour_ago
            ]
            
            recent_count = len(self.task_history[plugin_id])
            
            if recent_count >= max_per_hour:
                return False, f"Rate limit exceeded: {recent_count}/{max_per_hour} per hour"
            
            # Record this execution
            self.task_history[plugin_id].append(now)
            return True, ""
    
    async def reset(self, plugin_id: str = None):
        """Reset rate limits for a plugin or all plugins"""
        async with self.lock:
            if plugin_id:
                self.task_history[plugin_id] = []
            else:
                self.task_history.clear()


class ConcurrentTaskLimiter:
    """Limits concurrent task execution"""
    
    def __init__(self, max_concurrent: int = 3):
        self.max_concurrent = max_concurrent
        self.running_tasks: List[str] = []
        self.lock = asyncio.Lock()
    
    async def acquire(self, task_id: str) -> Tuple[bool, str]:
        """
        Try to acquire a slot for task execution.
        
        Args:
            task_id: Task identifier
        
        Returns:
            Tuple of (acquired, error_message)
        """
        async with self.lock:
            if len(self.running_tasks) >= self.max_concurrent:
                return False, f"Maximum concurrent tasks ({self.max_concurrent}) reached"
            
            self.running_tasks.append(task_id)
            return True, ""
    
    async def release(self, task_id: str):
        """Release a task slot"""
        async with self.lock:
            if task_id in self.running_tasks:
                self.running_tasks.remove(task_id)
    
    async def get_available_slots(self) -> int:
        """Get number of available execution slots"""
        async with self.lock:
            return self.max_concurrent - len(self.running_tasks)


# Global instances
rate_limiter = RateLimiter()
concurrent_limiter = ConcurrentTaskLimiter()
