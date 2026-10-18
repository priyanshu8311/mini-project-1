import threading
from collections import defaultdict
from datetime import UTC, datetime

from fastapi import Request
from starlette.exceptions import HTTPException


class SlidingWindowRateLimiter:
    """In-memory sliding window rate limiter by client IP address with bounded memory footprint."""

    def __init__(self, max_requests: int = 5, window_seconds: int = 60, max_keys: int = 2000):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.max_keys = max_keys
        self._requests: dict[str, list[float]] = defaultdict(list)
        self._lock = threading.Lock()

    def _prune_expired_locked(self, cutoff: float) -> None:
        """Evict stale keys to prevent memory exhaustion."""
        keys_to_remove = [k for k, ts in self._requests.items() if not any(t > cutoff for t in ts)]
        for k in keys_to_remove:
            self._requests.pop(k, None)

    def check(self, key: str) -> None:
        """Check if request exceeds rate limit and record the timestamp.

        Raises:
            HTTPException: 429 Too Many Requests if rate limit exceeded.
        """
        now = datetime.now(UTC).timestamp()
        cutoff = now - self.window_seconds

        with self._lock:
            # Memory safeguard: prune stale entries when capacity reaches threshold
            if len(self._requests) >= self.max_keys:
                self._prune_expired_locked(cutoff)

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
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        client_ip = forwarded.split(",")[0].strip()
    elif request.headers.get("cf-connecting-ip"):
        client_ip = request.headers["cf-connecting-ip"].strip()
    elif request.client:
        client_ip = request.client.host
    else:
        client_ip = "unknown"

    login_rate_limiter.check(client_ip)
