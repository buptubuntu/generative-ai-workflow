"""Async/sync bridge utilities.

Provides safe mechanisms for running async code from sync contexts,
handling existing event loops (e.g., in Jupyter notebooks or nested loops).
"""

from __future__ import annotations

import asyncio
from collections.abc import Coroutine
from typing import Any, TypeVar

T = TypeVar("T")


def run_sync(coro: Coroutine[Any, Any, T]) -> T:
    """Run a coroutine synchronously, handling existing event loops.

    Uses asyncio.run() when no loop is running, or creates a new thread
    with its own event loop when called from within an async context.

    Args:
        coro: Coroutine to execute.

    Returns:
        The coroutine's return value.

    Raises:
        RuntimeError: If unable to create or use an event loop.
    """
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        # No running loop — safe to use asyncio.run()
        return asyncio.run(coro)

    # Already inside an event loop (e.g., Jupyter, nested sync call).
    # Run in a separate thread with its own event loop.
    import concurrent.futures
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(_run_in_new_loop, coro)
        return future.result()


def _run_in_new_loop(coro: Coroutine[Any, Any, T]) -> T:
    """Execute a coroutine in a brand-new event loop (for thread isolation)."""
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()
