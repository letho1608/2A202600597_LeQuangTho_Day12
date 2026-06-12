import time
from collections import defaultdict, deque

from fastapi import HTTPException, status

from app.config import settings


class RateLimiter:
    def __init__(self, max_requests: int = 10, window_seconds: int = 60):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.requests: dict[str, deque] = defaultdict(deque)

    def check(self, user_id: str):
        now = time.time()
        window_start = now - self.window_seconds

        user_requests = self.requests[user_id]
        while user_requests and user_requests[0] < window_start:
            user_requests.popleft()

        if len(user_requests) >= self.max_requests:
            retry_after = int(user_requests[0] + self.window_seconds - now)
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail={
                    "error": "rate_limit_exceeded",
                    "message": f"Rate limit exceeded. Max {self.max_requests} requests per {self.window_seconds} seconds.",
                    "retry_after_seconds": retry_after,
                },
                headers={"Retry-After": str(retry_after)},
            )

        user_requests.append(now)

    def get_stats(self, user_id: str) -> dict:
        now = time.time()
        window_start = now - self.window_seconds

        user_requests = self.requests[user_id]
        while user_requests and user_requests[0] < window_start:
            user_requests.popleft()

        return {
            "user_id": user_id,
            "current_count": len(user_requests),
            "max_allowed": self.max_requests,
            "remaining": max(0, self.max_requests - len(user_requests)),
            "window_seconds": self.window_seconds,
        }


rate_limiter = RateLimiter(
    max_requests=settings.RATE_LIMIT_PER_MINUTE,
    window_seconds=60,
)


async def check_rate_limit(user_id: str = None) -> None:
    rate_limiter.check(user_id or "anonymous")
