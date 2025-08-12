import asyncio
import functools
import logging
import time
from typing import Any, Callable

logger = logging.getLogger(__name__)


def time_it(func_name: str | None = None):
    """Decorator to time function execution"""

    def decorator(func: Callable) -> Callable:
        name = func_name or f"{func.__module__}.{func.__name__}"

        if asyncio.iscoroutinefunction(func):

            @functools.wraps(func)
            async def async_wrapper(*args, **kwargs) -> Any:
                start_time = time.time()
                try:
                    result = await func(*args, **kwargs)
                    elapsed = time.time() - start_time
                    logger.info(f"⏱️  {name} took {elapsed:.2f}s")
                    return result
                except Exception as e:
                    elapsed = time.time() - start_time
                    logger.error(f"⏱️  {name} failed after {elapsed:.2f}s: {e}")
                    raise

            return async_wrapper
        else:

            @functools.wraps(func)
            def sync_wrapper(*args, **kwargs) -> Any:
                start_time = time.time()
                try:
                    result = func(*args, **kwargs)
                    elapsed = time.time() - start_time
                    logger.info(f"⏱️  {name} took {elapsed:.2f}s")
                    return result
                except Exception as e:
                    elapsed = time.time() - start_time
                    logger.error(f"⏱️  {name} failed after {elapsed:.2f}s: {e}")
                    raise

            return sync_wrapper

    return decorator


class TimingContext:
    """Context manager for timing code blocks"""

    def __init__(self, name: str):
        self.name = name
        self.start_time = None

    def __enter__(self):
        self.start_time = time.time()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        elapsed = time.time() - self.start_time
        if exc_type is None:
            logger.info(f"⏱️  {self.name} took {elapsed:.2f}s")
        else:
            logger.error(f"⏱️  {self.name} failed after {elapsed:.2f}s: {exc_val}")


def log_timing(name: str):
    """Simple function to return a timing context manager"""
    return TimingContext(name)
