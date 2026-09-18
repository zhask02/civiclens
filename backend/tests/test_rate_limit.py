"""Coverage for the Redis-backed public-report and operator request limits."""

from fastapi.testclient import TestClient
from starlette.requests import Request

from app.api import operator as operator_api
from app.api import reports as reports_api
from app.main import app
from app.services import rate_limit


class FakeRedis:
    """Small script-aware Redis fake; tests never require a running server."""

    def __init__(self):
        self.counts = {}
        self.calls = []
        self.ttl = 60

    def eval(self, script, key_count, key, window_seconds):
        assert key_count == 1
        self.calls.append((script, key, window_seconds))
        self.counts[key] = self.counts.get(key, 0) + 1
        return self.counts[key], self.ttl


class BrokenRedis:
    def eval(self, *args):
        raise ConnectionError("Redis is unavailable")


class FakeReportService:
    calls = 0

    def __init__(self, analysis_service):
        pass

    def submit(self, **kwargs):
        type(self).calls += 1
        return {"report_id": 1, "incident": {"id": 1}}


def _client_ip(host: str) -> Request:
    return Request({"type": "http", "client": (host, 12345), "headers": []})


def test_normalizes_ips_and_does_not_trust_forwarded_headers():
    request = Request({
        "type": "http",
        "client": ("2001:0db8::1", 12345),
        "headers": [(b"x-forwarded-for", b"198.51.100.9")],
    })
    assert rate_limit.normalized_client_ip(request) == "2001:db8::1"


def test_report_limiter_allows_limit_then_returns_429(monkeypatch):
    redis = FakeRedis()
    monkeypatch.setattr(rate_limit, "redis_client", redis)
    monkeypatch.setenv("CIVICLENS_REPORT_RATE_LIMIT", "2")
    request = _client_ip("203.0.113.2")

    rate_limit.limit_report_submission(request)
    rate_limit.limit_report_submission(request)

    try:
        rate_limit.limit_report_submission(request)
        assert False, "third request should be rate limited"
    except Exception as exc:
        assert exc.status_code == 429
        assert exc.headers["Retry-After"] == "60"
    assert redis.calls[0][1] == "rate:reports:ip:203.0.113.2"


def test_different_report_ips_have_independent_keys(monkeypatch):
    redis = FakeRedis()
    monkeypatch.setattr(rate_limit, "redis_client", redis)
    rate_limit.limit_report_submission(_client_ip("203.0.113.2"))
    rate_limit.limit_report_submission(_client_ip("203.0.113.3"))
    assert {call[1] for call in redis.calls} == {
        "rate:reports:ip:203.0.113.2",
        "rate:reports:ip:203.0.113.3",
    }


def test_report_counter_starts_a_new_window_after_redis_expiry(monkeypatch):
    redis = FakeRedis()
    monkeypatch.setattr(rate_limit, "redis_client", redis)
    monkeypatch.setenv("CIVICLENS_REPORT_RATE_LIMIT", "1")
    request = _client_ip("203.0.113.2")
    key = "rate:reports:ip:203.0.113.2"

    rate_limit.limit_report_submission(request)
    redis.counts.pop(key)  # Redis removes the key automatically at its TTL.
    rate_limit.limit_report_submission(request)


def test_redis_failure_is_explicitly_fail_open(monkeypatch):
    monkeypatch.setattr(rate_limit, "redis_client", BrokenRedis())
    rate_limit.limit_report_submission(_client_ip("203.0.113.2"))


def test_report_limit_runs_before_report_service(monkeypatch):
    redis = FakeRedis()
    redis.counts["rate:reports:ip:unknown"] = 20
    FakeReportService.calls = 0
    monkeypatch.setattr(rate_limit, "redis_client", redis)
    monkeypatch.setattr(reports_api, "ReportService", FakeReportService)

    response = TestClient(app).post(
        "/reports",
        data={"description": "Pothole", "latitude": "12.9", "longitude": "80.2"},
        files={"photo": ("pothole.jpg", b"image", "image/jpeg")},
    )

    assert response.status_code == 429
    assert FakeReportService.calls == 0


def test_operator_principal_keys_are_isolated_and_never_use_tokens(monkeypatch):
    redis = FakeRedis()
    monkeypatch.setattr(rate_limit, "redis_client", redis)
    monkeypatch.setenv("CIVICLENS_OPERATOR_RATE_LIMIT", "1")
    first = rate_limit.Principal(role="operator", name="first")
    second = rate_limit.Principal(role="operator", name="second")

    rate_limit._enforce(f"rate:operator:{first.name}", rate_limit.operator_rate_limit())
    rate_limit._enforce(f"rate:operator:{second.name}", rate_limit.operator_rate_limit())

    assert [call[1] for call in redis.calls] == ["rate:operator:first", "rate:operator:second"]
    assert all("Bearer" not in call[1] for call in redis.calls)
