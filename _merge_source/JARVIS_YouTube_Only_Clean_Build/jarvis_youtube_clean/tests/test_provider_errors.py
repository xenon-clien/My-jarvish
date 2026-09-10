from jarvis.ai.providers import _classify


def test_quota_is_persistent():
    et, retryable, persist = _classify(429, '{"error":{"type":"insufficient_quota"}}')
    assert et == "quota_exhausted" and not retryable and persist


def test_rate_limit_not_persistent():
    et, retryable, persist = _classify(429, 'rate limit exceeded, try again later')
    assert et == "rate_limited" and retryable and not persist


def test_server_error_retryable():
    et, retryable, persist = _classify(503, 'temporary unavailable')
    assert et == "server_error" and retryable and not persist
