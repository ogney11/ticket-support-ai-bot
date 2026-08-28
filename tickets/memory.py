"""In-memory per-ticket conversation cache.

The database remains the source of truth; this cache reduces DB round trips
for recent context within short-lived ticket interactions.
"""

from collections import OrderedDict
from datetime import datetime, timedelta


class TicketMemory:
    def __init__(self, ttl_seconds: int = 600, max_entries: int = 1000):
        self.ttl = timedelta(seconds=ttl_seconds)
        self.max_entries = max_entries
        self._cache: OrderedDict[int, tuple[datetime, list]] = OrderedDict()

    def get(self, ticket_id: int):
        entry = self._cache.get(ticket_id)
        if not entry:
            return None
        ts, messages = entry
        if datetime.utcnow() - ts > self.ttl:
            self._cache.pop(ticket_id, None)
            return None
        return list(messages)

    def set(self, ticket_id: int, messages: list):
        self._cache[ticket_id] = (datetime.utcnow(), list(messages))
        self._cache.move_to_end(ticket_id)
        while len(self._cache) > self.max_entries:
            self._cache.popitem(last=False)

    def append(self, ticket_id: int, message):
        messages = self.get(ticket_id) or []
        messages.append(message)
        self.set(ticket_id, messages)

    def clear(self, ticket_id: int):
        self._cache.pop(ticket_id, None)
