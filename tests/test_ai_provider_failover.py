"""Comprehensive Test Suite for JARVIS AI Provider Architecture & Safe Quota-Aware Failover.

Tests:
1. Primary Provider (Astra GPT-6) normal success path (Gemini not invoked).
2. Category A: Temporary Astra failure (500 / transient rate-limit) -> routes to Gemini, Astra not permanently disabled.
3. Category B: Astra Quota Exhaustion / Org Review (HTTP 429 insufficient_quota) -> transitions to DISABLED_QUOTA.
4. MANDATORY TEST: Second request after quota exhaustion makes EXACTLY ZERO network requests to Astra and routes directly to Gemini.
5. Category C: Astra Authentication Failure (HTTP 401) -> transitions to DISABLED_AUTH and bypasses Astra.
6. Total Cloud Failure: Astra and Gemini both fail -> Graceful fallback to offline MockProvider with zero crashes.
7. Manual Developer Reset: `/provider reset astra` command restores Astra status to AVAILABLE.
8. Structured Tool Calling Preservation: Function/tool schemas preserved across failover.
9. Live Error Classification: Validates Experiential Labs 429 response structure.
"""
import asyncio
import json
import os
import shutil
import tempfile
import time
from unittest.mock import AsyncMock, MagicMock, patch
import pytest

from backend.ai.providers import (
    AIProviderRouter,
    AstraAPIError,
    AstraProvider,
    BaseAIResponse,
    ErrorCategory,
    GeminiProvider,
    MockProvider,
    ProviderStatus,
    ToolCall,
)
from backend.core.config import Settings


@pytest.fixture
def temp_state_file():
    """Create a temporary state file for testing isolated provider router instances."""
    tmp_dir = tempfile.mkdtemp()
    state_path = os.path.join(tmp_dir, "test_astra_state.json")
    yield state_path
    shutil.rmtree(tmp_dir, ignore_errors=True)


@pytest.fixture
def mock_settings():
    """Mock settings with Astra primary and Gemini fallback."""
    s = MagicMock(spec=Settings)
    s.AI_PRIMARY_PROVIDER = "astra"
    s.AI_FALLBACK_PROVIDER = "gemini"
    s.AI_PROVIDER = "astra"
    s.ASTRA_API_KEY = "xpl_test_key"
    s.ASTRA_MODEL = "gpt-6-astra"
    s.ASTRA_BASE_URL = "https://api.experientiallabs.ai/v1"
    s.ASTRA_TIMEOUT_SECONDS = 5.0
    s.OPENAI_API_KEY = "xpl_test_key"
    s.AI_API_KEY = "gemini_test_key"
    s.AI_MODEL = "gemini-3.5-flash-lite"
    s.OPENROUTER_API_KEY = ""
    s.NEMOTRON_ENABLED = False
    return s


# =====================================================================
# TEST 1: Astra Normal Request Success
# =====================================================================
@pytest.mark.asyncio
async def test_astra_primary_success(mock_settings, temp_state_file):
    """Verify that when Astra succeeds, Gemini is NOT called and Astra status is AVAILABLE."""
    router = AIProviderRouter(settings=mock_settings, state_file_path=temp_state_file)

    # Mock Astra success
    expected_response = BaseAIResponse(content="Hello from GPT-6 Astra!", tool_calls=[])
    router.astra.generate_response = AsyncMock(return_value=expected_response)
    router.gemini.generate_response = AsyncMock()

    messages = [{"role": "user", "content": "Hello"}]
    res = await router.generate_response(messages)

    assert res.content == "Hello from GPT-6 Astra!"
    assert router.astra.generate_response.call_count == 1
    # Gemini must NOT be called
    assert router.gemini.generate_response.call_count == 0
    assert router.state.status == ProviderStatus.AVAILABLE
    assert router.state.consecutive_failures == 0
    assert router.state.successful_requests == 1


# =====================================================================
# TEST 2: Temporary Failure (Category A)
# =====================================================================
@pytest.mark.asyncio
async def test_astra_temporary_failure_failover(mock_settings, temp_state_file):
    """Verify that transient 500/timeout degrades temporarily and falls back to Gemini without permanent disabling."""
    router = AIProviderRouter(settings=mock_settings, state_file_path=temp_state_file)

    # Astra raises temporary error (Category A)
    router.astra.generate_response = AsyncMock(
        side_effect=AstraAPIError(503, ErrorCategory.CATEGORY_A_TEMPORARY, "Service Unavailable")
    )
    # Gemini succeeds
    gemini_resp = BaseAIResponse(content="Hello from Gemini Standby Fallback!", tool_calls=[])
    router.gemini.generate_response = AsyncMock(return_value=gemini_resp)

    messages = [{"role": "user", "content": "Hello"}]
    res = await router.generate_response(messages)

    # Must return Gemini's response
    assert res.content == "Hello from Gemini Standby Fallback!"
    assert router.astra.generate_response.call_count == 1
    assert router.gemini.generate_response.call_count == 1

    # Astra must be TEMPORARILY_DEGRADED with retry-after backoff, NOT permanently disabled
    assert router.state.status == ProviderStatus.TEMPORARILY_DEGRADED
    assert router.state.retry_after > time.time()
    assert router.state.fallback_requests == 1


# =====================================================================
# TEST 3: Quota Exhaustion / Org Review (Category B)
# =====================================================================
@pytest.mark.asyncio
async def test_astra_quota_exhaustion_failover(mock_settings, temp_state_file):
    """Verify that HTTP 429 with insufficient_quota transitions to DISABLED_QUOTA and routes to Gemini."""
    router = AIProviderRouter(settings=mock_settings, state_file_path=temp_state_file)

    quota_err_text = (
        '{"error":{"message":"Your organization is under review to fight spam and can\'t use models right now.",'
        '"type":"insufficient_quota","param":null,"code":"org_under_review"}}'
    )
    cat, reason = router.astra.classify_error(429, quota_err_text)
    assert cat == ErrorCategory.CATEGORY_B_QUOTA_EXHAUSTED

    router.astra.generate_response = AsyncMock(
        side_effect=AstraAPIError(429, cat, reason)
    )
    gemini_resp = BaseAIResponse(content="Gemini fallback active due to quota limit", tool_calls=[])
    router.gemini.generate_response = AsyncMock(return_value=gemini_resp)

    messages = [{"role": "user", "content": "Plan my schedule"}]
    res = await router.generate_response(messages)

    assert res.content == "Gemini fallback active due to quota limit"
    assert router.astra.generate_response.call_count == 1
    assert router.gemini.generate_response.call_count == 1
    assert router.state.status == ProviderStatus.DISABLED_QUOTA

    # Verify state was persisted to disk
    with open(temp_state_file, "r", encoding="utf-8") as f:
        persisted = json.load(f)
    assert persisted["status"] == "DISABLED_QUOTA"


# =====================================================================
# TEST 4: MANDATORY ZERO-CALL BYPASS TEST AFTER QUOTA EXHAUSTION
# =====================================================================
@pytest.mark.asyncio
async def test_mandatory_zero_call_bypass_when_quota_disabled(mock_settings, temp_state_file):
    """MANDATORY TEST: When Astra status is DISABLED_QUOTA, subsequent requests MUST make

    EXACTLY ZERO calls to Astra and route directly to Gemini.
    """
    router = AIProviderRouter(settings=mock_settings, state_file_path=temp_state_file)

    # Pre-set state to DISABLED_QUOTA (simulating previous quota exhaustion)
    router.state.status = ProviderStatus.DISABLED_QUOTA
    router.state.reason = "Previous 429 insufficient_quota"
    router._save_state()

    # Setup spy mocks
    router.astra.generate_response = AsyncMock()
    router.gemini.generate_response = AsyncMock(
        return_value=BaseAIResponse(content="Direct Gemini fallback without touching Astra", tool_calls=[])
    )

    messages = [{"role": "user", "content": "What is the weather?"}]
    res = await router.generate_response(messages)

    # 1. Verify result returned from Gemini
    assert res.content == "Direct Gemini fallback without touching Astra"

    # 2. MANDATORY CHECK: Astra generate_response was called EXACTLY 0 TIMES
    assert router.astra.generate_response.call_count == 0, (
        f"CRITICAL FAILURE: Astra was called {router.astra.generate_response.call_count} times "
        f"even though status was DISABLED_QUOTA! Must make ZERO network requests."
    )

    # 3. Verify Gemini was called directly
    assert router.gemini.generate_response.call_count == 1

    # Send a second subsequent request to ensure permanent zero-call guarantee holds
    res2 = await router.generate_response(messages)
    assert router.astra.generate_response.call_count == 0
    assert router.gemini.generate_response.call_count == 2


# =====================================================================
# TEST 5: Category C: Invalid Auth (HTTP 401)
# =====================================================================
@pytest.mark.asyncio
async def test_astra_invalid_auth_failover(mock_settings, temp_state_file):
    """Verify that HTTP 401 invalid key transitions to DISABLED_AUTH and bypasses future calls."""
    router = AIProviderRouter(settings=mock_settings, state_file_path=temp_state_file)

    cat, reason = router.astra.classify_error(401, '{"error":{"message":"Invalid API key provided"}}')
    assert cat == ErrorCategory.CATEGORY_C_AUTH_INVALID

    router.astra.generate_response = AsyncMock(
        side_effect=AstraAPIError(401, cat, reason)
    )
    router.gemini.generate_response = AsyncMock(
        return_value=BaseAIResponse(content="Gemini fallback on auth failure", tool_calls=[])
    )

    res = await router.generate_response([{"role": "user", "content": "test auth"}])
    assert res.content == "Gemini fallback on auth failure"
    assert router.state.status == ProviderStatus.DISABLED_AUTH

    # Second call must make ZERO calls to Astra
    router.astra.generate_response.reset_mock()
    res2 = await router.generate_response([{"role": "user", "content": "test auth 2"}])
    assert router.astra.generate_response.call_count == 0
    assert res2.content == "Gemini fallback on auth failure"


# =====================================================================
# TEST 6: Total Cloud Failure -> MockProvider Graceful Fallback
# =====================================================================
@pytest.mark.asyncio
async def test_both_providers_fail_mock_fallback(mock_settings, temp_state_file):
    """Verify that if Astra and Gemini both fail, system safely degrades to MockProvider without crashing."""
    router = AIProviderRouter(settings=mock_settings, state_file_path=temp_state_file)

    # Astra fails
    router.astra.generate_response = AsyncMock(
        side_effect=AstraAPIError(500, ErrorCategory.CATEGORY_A_TEMPORARY, "Internal Server Error")
    )
    # Gemini fails
    router.gemini.generate_response = AsyncMock(
        side_effect=RuntimeError("Gemini API connection error")
    )

    # Offline query
    messages = [{"role": "user", "content": "time kya hai"}]
    res = await router.generate_response(messages)

    # Must return deterministic mock response, NO exception raised
    assert res is not None
    assert len(res.tool_calls) > 0
    assert res.tool_calls[0].name == "get_current_time"


# =====================================================================
# TEST 7: Manual Developer Reset Command (/provider reset astra)
# =====================================================================
@pytest.mark.asyncio
async def test_manual_developer_reset(mock_settings, temp_state_file):
    """Verify that reset_astra_state() restores status to AVAILABLE and re-enables Astra calls."""
    router = AIProviderRouter(settings=mock_settings, state_file_path=temp_state_file)

    # Put into DISABLED_QUOTA
    router.state.status = ProviderStatus.DISABLED_QUOTA
    router.state.consecutive_failures = 5
    router.state.retry_after = 999999.0
    router._save_state()

    # Developer reset
    summary = router.reset_astra_state()
    assert summary["astra_status"] == "AVAILABLE"
    assert router.state.status == ProviderStatus.AVAILABLE
    assert router.state.consecutive_failures == 0
    assert router.state.retry_after == 0.0

    # Now verify Astra is called again on next request
    router.astra.generate_response = AsyncMock(
        return_value=BaseAIResponse(content="Astra is back online!", tool_calls=[])
    )
    router.gemini.generate_response = AsyncMock()

    res = await router.generate_response([{"role": "user", "content": "Are you back?"}])
    assert res.content == "Astra is back online!"
    assert router.astra.generate_response.call_count == 1


# =====================================================================
# TEST 8: Structured Tool Calling Preservation Across Failover
# =====================================================================
@pytest.mark.asyncio
async def test_structured_tool_calling_preservation_on_fallback(mock_settings, temp_state_file):
    """Verify that tool schemas are properly forwarded to Gemini and parsed tool calls are returned."""
    router = AIProviderRouter(settings=mock_settings, state_file_path=temp_state_file)

    # Astra fails with quota limit
    router.astra.generate_response = AsyncMock(
        side_effect=AstraAPIError(429, ErrorCategory.CATEGORY_B_QUOTA_EXHAUSTED, "Quota exceeded")
    )

    # Gemini returns structured function call
    gemini_tool_call = ToolCall(name="open_application", arguments={"app_name": "notepad"})
    gemini_resp = BaseAIResponse(content=None, tool_calls=[gemini_tool_call])
    router.gemini.generate_response = AsyncMock(return_value=gemini_resp)

    tool_schemas = [{
        "name": "open_application",
        "description": "Open a desktop application",
        "parameters": {"type": "object", "properties": {"app_name": {"type": "string"}}},
    }]

    messages = [{"role": "user", "content": "open notepad"}]
    res = await router.generate_response(messages, tools_schema=tool_schemas)

    # Verify Gemini received the exact tools schema
    router.gemini.generate_response.assert_called_once_with(messages, tool_schemas)
    assert len(res.tool_calls) == 1
    assert res.tool_calls[0].name == "open_application"
    assert res.tool_calls[0].arguments == {"app_name": "notepad"}


# =====================================================================
# TEST 9: Error Classifier Unit Tests
# =====================================================================
def test_error_classification_rules(mock_settings):
    """Verify precision of the Astra error classification engine across all categories."""
    astra = AstraProvider(mock_settings)

    # Category B: 429 with insufficient_quota / org_under_review
    cat_b1, _ = astra.classify_error(429, '{"error":{"type":"insufficient_quota","code":"org_under_review"}}')
    assert cat_b1 == ErrorCategory.CATEGORY_B_QUOTA_EXHAUSTED

    cat_b2, _ = astra.classify_error(429, 'You have exceeded your current quota, please check your plan and billing details.')
    assert cat_b2 == ErrorCategory.CATEGORY_B_QUOTA_EXHAUSTED

    # Category A: 429 concurrency limit (transient, without quota message)
    cat_a1, _ = astra.classify_error(429, 'Rate limit reached: 3 requests per minute. Try again in 10s.')
    assert cat_a1 == ErrorCategory.CATEGORY_A_TEMPORARY

    # Category A: 500, 502, 503
    cat_a2, _ = astra.classify_error(503, 'Service Unavailable')
    assert cat_a2 == ErrorCategory.CATEGORY_A_TEMPORARY

    # Category C: 401 Unauthorized
    cat_c, _ = astra.classify_error(401, 'Invalid API Key')
    assert cat_c == ErrorCategory.CATEGORY_C_AUTH_INVALID

    # Category D: 400 / 404 Model Not Found
    cat_d, _ = astra.classify_error(404, 'The model gpt-unknown does not exist')
    assert cat_d == ErrorCategory.CATEGORY_D_MODEL_CONFIG
