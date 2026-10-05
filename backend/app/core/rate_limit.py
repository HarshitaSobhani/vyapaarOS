"""In-memory throttle for repeated failed logins. No external service.

State is per process (the API runs as a single uvicorn worker) and is lost on restart, which only
ever resets a cooldown early. Keyed by (client IP, email) so one person mistyping does not lock out
everyone else, and one attacker cannot lock out an account from every address.
"""
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass


@dataclass
class _Entry:
    failures: int = 0
    window_start: float = 0.0
    blocked_until: float = 0.0


class LoginThrottle:
    def __init__(self, max_failures: int = 5, window_seconds: int = 600, cooldown_seconds: int = 300,
                 max_entries: int = 10_000, clock: Callable[[], float] = time.monotonic) -> None:
        self.max_failures = max_failures
        self.window_seconds = window_seconds
        self.cooldown_seconds = cooldown_seconds
        self.max_entries = max_entries
        self._clock = clock
        self._entries: dict[tuple[str, str], _Entry] = {}
        self._lock = threading.Lock()

    @staticmethod
    def _key(ip: str, email: str) -> tuple[str, str]:
        return ip, email.strip().lower()

    def is_blocked(self, ip: str, email: str) -> bool:
        with self._lock:
            entry = self._entries.get(self._key(ip, email))
            return entry is not None and entry.blocked_until > self._clock()

    def record_failure(self, ip: str, email: str) -> None:
        now = self._clock()
        with self._lock:
            if len(self._entries) >= self.max_entries:
                self._prune(now)
            entry = self._entries.setdefault(self._key(ip, email), _Entry(window_start=now))
            if now - entry.window_start > self.window_seconds:
                entry.failures, entry.window_start = 0, now
            entry.failures += 1
            if entry.failures >= self.max_failures:
                entry.blocked_until = now + self.cooldown_seconds
                entry.failures, entry.window_start = 0, now

    def record_success(self, ip: str, email: str) -> None:
        with self._lock:
            self._entries.pop(self._key(ip, email), None)

    def reset(self) -> None:
        with self._lock:
            self._entries.clear()

    def _prune(self, now: float) -> None:
        stale = [k for k, e in self._entries.items()
                 if e.blocked_until <= now and now - e.window_start > self.window_seconds]
        for k in stale:
            del self._entries[k]
        if len(self._entries) >= self.max_entries:  # still full: drop the oldest windows
            for k, _ in sorted(self._entries.items(), key=lambda kv: kv[1].window_start)[: self.max_entries // 10]:
                del self._entries[k]


login_throttle = LoginThrottle()
