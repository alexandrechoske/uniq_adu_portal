"""
Retry utilities to make Supabase calls resilient to transient errors like
"Server disconnected" or timeouts without changing existing behavior.

Usage:
    from services.retry_utils import run_with_retries
    result = run_with_retries('logos-clientes', lambda: supabase_admin.table(...).execute())
"""

from typing import Callable, Tuple, Type, Any, Optional
import time


def run_with_retries(label: str,
                     func: Callable[[], Any],
                     max_attempts: int = 3,
                     base_delay_seconds: float = 0.75,
                     retry_exceptions: Tuple[Type[BaseException], ...] = (Exception,),
                     should_retry: Optional[Callable[[BaseException], bool]] = None) -> Any:
    """Run a callable with small exponential backoff retries.

    - label: short label for logs
    - func: no-arg callable that executes the operation and returns the result
    - max_attempts: total attempts including the first
    - base_delay_seconds: initial delay; grows linearly per attempt
    - retry_exceptions: tuple of exception types to catch and retry
    - should_retry: optional predicate to further filter retryable errors
    """
    attempt = 1
    last_exc: Optional[BaseException] = None
    while attempt <= max_attempts:
        try:
            return func()
        except retry_exceptions as exc:  # type: ignore
            last_exc = exc
            msg = str(exc)
            retry_allowed = True if should_retry is None else should_retry(exc)
            print(f"[RETRY] {label} attempt {attempt}/{max_attempts} failed: {msg}")
            if not retry_allowed or attempt == max_attempts:
                break
            delay = base_delay_seconds * attempt
            try:
                time.sleep(delay)
            except Exception:
                pass
            attempt += 1
    # Exhausted retries
    if last_exc:
        raise last_exc
    raise RuntimeError(f"{label} failed without exception but returned no result")
