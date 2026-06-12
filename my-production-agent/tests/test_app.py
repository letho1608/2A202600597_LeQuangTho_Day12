import os
import sys
from unittest.mock import patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

os.environ["AGENT_API_KEY"] = "test-key"
os.environ["ENVIRONMENT"] = "test"
os.environ["REDIS_URL"] = "redis://localhost:6379/0"
os.environ["LOG_LEVEL"] = "ERROR"

from fastapi.testclient import TestClient

from app.main import app
from app.config import settings
from app.rate_limiter import rate_limiter
from app.cost_guard import cost_guard
from utils.mock_llm import ask

client = TestClient(app)


def test_health_endpoint():
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "version" in data
    assert "uptime_seconds" in data


def test_ready_endpoint():
    response = client.get("/ready")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ready"


def test_root_endpoint():
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["app"] == settings.APP_NAME
    assert "endpoints" in data


def test_ask_without_auth():
    response = client.post("/ask", json={"question": "Hello", "user_id": "test"})
    assert response.status_code in [401, 422]


def test_ask_with_valid_auth():
    rate_limiter.requests.clear()
    response = client.post(
        "/ask",
        json={"question": "What is Docker?", "user_id": "test"},
        headers={"X-API-Key": "test-key"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "answer" in data
    assert data["model"] == settings.LLM_MODEL


def test_ask_invalid_question():
    response = client.post(
        "/ask",
        json={"question": "", "user_id": "test"},
        headers={"X-API-Key": "test-key"},
    )
    assert response.status_code == 422


def test_rate_limiter():
    rate_limiter.requests.clear()
    limiter = rate_limiter
    user_id = "rate_test_user"

    for i in range(limiter.max_requests):
        limiter.check(user_id)
    stats = limiter.get_stats(user_id)
    assert stats["current_count"] == limiter.max_requests
    assert stats["remaining"] == 0


def test_rate_limiter_exceeded():
    rate_limiter.requests.clear()
    limiter = rate_limiter
    user_id = "exceed_test_user"

    for i in range(limiter.max_requests):
        limiter.check(user_id)

    import pytest
    from fastapi import HTTPException

    with pytest.raises(HTTPException) as exc:
        limiter.check(user_id)
    assert exc.value.status_code == 429


def test_cost_guard_estimate():
    cost = cost_guard.estimate_cost()
    assert cost > 0
    assert cost < 1.0


def test_cost_guard_record():
    cost_guard._usage.clear()
    result = cost_guard.record_usage("test_user")
    assert result["input_tokens"] > 0
    assert result["cost"] > 0


def test_cost_guard_budget_check():
    cost_guard._usage.clear()
    cost_guard.check_budget("test_user")
    assert True


def test_mock_llm():
    response = ask("What is Docker?", delay=0)
    assert response is not None
    assert len(response) > 0


def test_mock_llm_keyword():
    response = ask("deploy my app", delay=0)
    assert "deploy" in response.lower() or "deployment" in response.lower()


def test_config_defaults():
    assert settings.PORT == 8000
    assert settings.APP_NAME == "AI Production Agent"
    assert settings.RATE_LIMIT_PER_MINUTE == 10


def test_metrics_endpoint():
    response = client.get(
        "/metrics",
        headers={"X-API-Key": "test-key"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "rate_limiting" in data
    assert "cost_guard" in data
