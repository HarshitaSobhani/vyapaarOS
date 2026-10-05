import pytest

from app.core.rate_limit import LoginThrottle, login_throttle

GOOD = {"email": "demo@vyapaaros.in", "password": "test-password-123"}
BAD = {"email": "demo@vyapaaros.in", "password": "wrong-password"}


class FakeClock:
    def __init__(self) -> None:
        self.now = 1000.0

    def __call__(self) -> float:
        return self.now


@pytest.fixture
def clock(monkeypatch):
    c = FakeClock()
    monkeypatch.setattr(login_throttle, "_clock", c)
    return c


def login(client, body):
    return client.post("/api/auth/login", json=body)


def test_repeated_failures_trigger_cooldown_with_same_generic_error(client, clock):
    first = login(client, BAD)
    for _ in range(login_throttle.max_failures - 1):
        assert login(client, BAD).status_code == 401
    throttled = login(client, BAD)
    assert throttled.status_code == 401 and throttled.json() == first.json()
    assert throttled.json()["error"]["message"] == "Incorrect email or password"


def test_correct_password_is_rejected_during_cooldown_then_works_after(client, clock):
    for _ in range(login_throttle.max_failures):
        login(client, BAD)
    during = login(client, GOOD)
    assert during.status_code == 401 and during.json()["error"]["code"] == "invalid_credentials"
    clock.now += login_throttle.cooldown_seconds + 1
    assert login(client, GOOD).status_code == 200


def test_cooldown_does_not_end_early(client, clock):
    for _ in range(login_throttle.max_failures):
        login(client, BAD)
    clock.now += login_throttle.cooldown_seconds - 5
    assert login(client, GOOD).status_code == 401


def test_other_emails_are_not_affected(client, clock):
    for _ in range(login_throttle.max_failures):
        login(client, BAD)
    other = login(client, {"email": "manager@vyapaaros.in", "password": GOOD["password"]})
    assert other.status_code == 200


def test_successful_login_resets_the_failure_count(client, clock):
    for _ in range(login_throttle.max_failures - 1):
        login(client, BAD)
    assert login(client, GOOD).status_code == 200
    for _ in range(login_throttle.max_failures - 1):
        login(client, BAD)
    assert login(client, GOOD).status_code == 200   # would be blocked if the earlier failures had carried over


def test_failures_outside_the_window_do_not_accumulate(client, clock):
    for _ in range(login_throttle.max_failures - 1):
        login(client, BAD)
    clock.now += login_throttle.window_seconds + 1
    login(client, BAD)
    assert login(client, GOOD).status_code == 200


def test_unknown_email_is_throttled_too_and_key_is_case_insensitive(client, clock):
    ghost = {"email": "ghost@vyapaaros.in", "password": "x"}
    for i in range(login_throttle.max_failures):
        login(client, {**ghost, "email": ghost["email"].upper() if i % 2 else ghost["email"]})
    assert login_throttle.is_blocked("testclient", "Ghost@vyapaaros.in")


def test_different_ip_has_its_own_budget():
    t = LoginThrottle(max_failures=2, clock=FakeClock())
    t.record_failure("1.1.1.1", "a@b.in")
    t.record_failure("1.1.1.1", "a@b.in")
    assert t.is_blocked("1.1.1.1", "a@b.in") and not t.is_blocked("2.2.2.2", "a@b.in")


def test_memory_is_bounded():
    t = LoginThrottle(max_failures=5, max_entries=50, clock=FakeClock())
    for i in range(500):
        t.record_failure(f"10.0.{i // 250}.{i % 250}", "a@b.in")
    assert len(t._entries) <= 50
