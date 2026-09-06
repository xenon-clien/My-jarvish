# Astra Gateway Error Classification & Circuit Breaker Logic
## Operational Taxonomy for Safe Failover & Quota Management

**Date**: 2026-09-06  
**Module**: `backend/ai/providers.py` (`AstraProvider.classify_error`, `AIProviderRouter`)  
**Gateway**: Experiential Labs OpenAI-Compatible Gateway (`https://api.experientiallabs.ai/v1`)  

---

## 1. Classification Taxonomy

The system enforces a strict 4-category taxonomy to avoid the dangerous pitfall of treating all HTTP 429s identically:

```
                          ┌───────────────────────────┐
                          │   Astra Gateway Response  │
                          └─────────────┬─────────────┘
                                        │
           ┌────────────────────────────┼────────────────────────────┐
           │                            │                            │
           ▼                            ▼                            ▼
   [Category A: Temp]          [Category B: Quota]          [Category C: Auth]
   • 500, 502, 503, 504        • 429 with:                  • 401 Unauthorized
   • Timeout / ConnectErr        - "insufficient_quota"     • Invalid API Key
   • 429 concurrency only        - "org_under_review"
                                 - "quota" / "billing"
           │                            │                            │
           ▼                            ▼                            ▼
   Status:                      Status:                      Status:
   TEMPORARILY_DEGRADED         DISABLED_QUOTA               DISABLED_AUTH
   Backoff: 30 seconds          Action: ZERO calls on        Action: ZERO calls on
   Fallback: Gemini             subsequent turns;            subsequent turns;
                                Fallback: Gemini             Fallback: Gemini
```

---

## 2. Category Details & Invariants

### 2.1 Category A: Temporary Degradation (`CATEGORY_A_TEMPORARY`)
- **HTTP Status Codes**: 500, 502, 503, 504.
- **Client Exceptions**: `httpx.TimeoutException`, `httpx.ConnectError`, `httpx.NetworkError`.
- **Transient Rate Limits**: HTTP 429 where the response body does **not** contain quota/review keywords (e.g. standard RPM/TPM concurrency spike: *"Rate limit reached: 3 requests per minute. Try again in 10s.*").
- **Circuit Breaker Action**:
  - Sets `state.status = ProviderStatus.TEMPORARILY_DEGRADED`.
  - Sets backoff: `retry_after = time.time() + 30.0` (or `Retry-After` header value).
  - Astra is **NOT** permanently disabled.
  - Automatically falls back to Google Gemini for the current turn.
  - After 30 seconds, the router probes Astra again.

### 2.2 Category B: Quota Exhaustion & Account Review (`CATEGORY_B_QUOTA_EXHAUSTED`)
- **Signatures Detected**:
  - `insufficient_quota`
  - `org_under_review`
  - `under review`
  - `exceeded your current quota`
  - `exceeded your balance`
  - `billing`
  - `credit limit`
- **Empirical Live Signature**:
  ```json
  {
    "error": {
      "message": "Your organization is under review to fight spam and can't use models right now. If you believe this is a mistake, use the \"This is a mistake\" button on the in-app banner to appeal.",
      "type": "insufficient_quota",
      "param": null,
      "code": "org_under_review"
    }
  }
  ```
- **Circuit Breaker Action**:
  - Sets `state.status = ProviderStatus.DISABLED_QUOTA`.
  - Persists state immediately to `logs/ai/astra_state.json`.
  - Logs `[CRITICAL]` alert.
  - **MANDATORY INVARIANT**: All subsequent requests bypass Astra with **0 network requests**.
  - Direct execution of Google Gemini standby fallback.

### 2.3 Category C: Authentication & Access Revocation (`CATEGORY_C_AUTH_INVALID`)
- **HTTP Status Codes**: 401 Unauthorized, 403 Forbidden (without quota explanation).
- **Keywords**: `invalid api key`, `unauthorized`, `authentication`.
- **Circuit Breaker Action**:
  - Sets `state.status = ProviderStatus.DISABLED_AUTH`.
  - Persists state to `logs/ai/astra_state.json`.
  - Bypasses Astra on subsequent requests directly to Google Gemini.

### 2.4 Category D: Model & Request Configuration (`CATEGORY_D_MODEL_CONFIG`)
- **HTTP Status Codes**: 400 Bad Request, 404 Model Not Found.
- **Empirical Discovery**:
  - Parameter `temperature` is rejected by `gpt-6-astra` route (`"The parameter 'temperature' is not supported by this model route"`).
  - Resolved by omitting `temperature` from the Astra payload.
- **Circuit Breaker Action**:
  - Logs warning, falls back to Google Gemini without permanently locking the provider.

---

## 3. Administrative Reset Specification

When quota is restored or account review clears, the operator restores live routing via:
- CLI command: `/provider reset astra` (or `/provider reset`)
- Python API: `ai_provider_router.reset_astra_state()`

Reset Actions:
1. State transitioned to `AVAILABLE`.
2. `consecutive_failures` reset to 0.
3. `retry_after` reset to 0.0.
4. Reason recorded: `"Manual reset by administrator / command"`.
5. Disk file `logs/ai/astra_state.json` synchronized.
