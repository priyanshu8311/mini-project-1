import threading
from collections import defaultdict
from datetime import UTC, datetime

from fastapi import Request
from starlette.exceptions import HTTPException


class SlidingWindowRateLimiter:
    """In-memory sliding window rate limiter by client IP address."""

    def __init__(self, max_requests: int = 5, window_seconds: int = 60):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._requests: dict[str, list[float]] = defaultdict(list)
        self._lock = threading.Lock()

    def check(self, key: str) -> None:
        """Check if request exceeds rate limit and record the timestamp.

        Raises:
            HTTPException: 429 Too Many Requests if rate limit exceeded.
        """
        now = datetime.now(UTC).timestamp()
        cutoff = now - self.window_seconds

        with self._lock:
            # Evict timestamps older than the sliding window
            timestamps = [ts for ts in self._requests[key] if ts > cutoff]
            if len(timestamps) >= self.max_requests:
                oldest_timestamp = timestamps[0]
                retry_after = max(1, int(oldest_timestamp + self.window_seconds - now))
                raise HTTPException(
                    status_code=429,
                    detail=f"Too many login attempts. Please try again in {retry_after} seconds.",
                    headers={"Retry-After": str(retry_after)},
                )

            timestamps.append(now)
            self._requests[key] = timestamps

    def reset(self, key: str | None = None) -> None:
        """Clear rate limit history (useful for tests)."""
        with self._lock:
            if key:
                self._requests.pop(key, None)
            else:
                self._requests.clear()


# Default singleton instance for login endpoint: 5 requests per 60 seconds
login_rate_limiter = SlidingWindowRateLimiter(max_requests=5, window_seconds=60)


def enforce_login_rate_limit(request: Request) -> None:
    """FastAPI dependency to enforce rate limiting on unauthenticated login."""
    client_ip = request.client.host if request.client else "unknown"
    login_rate_limiter.check(client_ip)
