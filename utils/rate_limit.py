import time
from collections import defaultdict


class RateLimiter:
    def __init__(self, per_user: int = 5, per_ticket: int = 10, window: int = 60):
        self.per_user = per_user
        self.per_ticket = per_ticket
        self.window = window
        self.user_requests: defaultdict[int, list[float]] = defaultdict(list)
        self.ticket_requests: defaultdict[int, list[float]] = defaultdict(list)

    def allow(self, user_id: int, ticket_id: int) -> bool:
        now = time.time()
        self.user_requests[user_id] = [
            t for t in self.user_requests[user_id] if now - t < self.window
        ]
        self.ticket_requests[ticket_id] = [
            t for t in self.ticket_requests[ticket_id] if now - t < self.window
        ]
        if len(self.user_requests[user_id]) >= self.per_user:
            return False
        if len(self.ticket_requests[ticket_id]) >= self.per_ticket:
            return False
        self.user_requests[user_id].append(now)
        self.ticket_requests[ticket_id].append(now)
        return True
