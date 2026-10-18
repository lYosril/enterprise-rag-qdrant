"""
Resilient LLM client for OpenAI-compatible chat completion APIs.

Reliability rules:
- Retries only transient failures (HTTP 429 rate limit, 5xx gateway/server errors, timeouts).
- Permanent 4xx errors (e.g. 400 Bad Request, 401 Unauthorized) are not retried.
- Employs exponential backoff with bounded attempts.
- Never fabricates an answer on failure; raises controlled errors and increments failure metrics.
- Masks authorization headers and does not log sensitive data.
"""

import time
import requests
from app.core.config import settings
from app.core.logging_config import logger
from app.core.metrics import LLM_ERRORS
from app.core.observability import LLM_LATENCY, LLM_TOKENS_TOTAL


class LLMClientError(RuntimeError):
    """Raised when an LLM request fails permanently or retries are exhausted."""
    pass


TRANSIENT_STATUS_CODES = {429, 500, 502, 503, 504}


def chat_completion(
    messages: list[dict],
    max_retries: int = 3,
    initial_backoff_sec: float = 0.5,
    return_usage: bool = False,
):
    """
    Execute a chat completion request with resilient retries for transient errors.

    Parameters
    ----------
    messages : list[dict]
        OpenAI-format messages list [{"role": ..., "content": ...}].
    max_retries : int
        Maximum retry attempts for transient errors (default 3).
    initial_backoff_sec : float
        Base backoff delay in seconds.
    return_usage : bool
        When True, return a ``(content, usage)`` tuple instead of just the
        content string. ``usage`` is the provider usage dictionary (may be
        empty). Defaults to False so existing callers are unaffected.

    Returns
    -------
    str | tuple[str, dict]
        Grounded answer content stripped of leading/trailing whitespace, and
        optionally the token usage dictionary.
    """
    url = f"{settings.llm_base_url.rstrip('/')}/chat/completions"
    headers = {
        "Authorization": f"Bearer {settings.llm_api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": settings.llm_model,
        "temperature": 0,
        "messages": messages,
    }

    last_exception: Exception | None = None

    for attempt in range(max_retries):
        try:
            with LLM_LATENCY.time():
                response = requests.post(
                    url,
                    headers=headers,
                    json=payload,
                    timeout=(5, settings.agent_llm_timeout_seconds),
                )

            # Check status
            if response.status_code in TRANSIENT_STATUS_CODES:
                logger.warning(
                    "llm_transient_error",
                    status_code=response.status_code,
                    attempt=attempt + 1,
                    max_retries=max_retries,
                )
                if attempt < max_retries - 1:
                    sleep_time = initial_backoff_sec * (2 ** attempt)
                    time.sleep(sleep_time)
                    continue
                response.raise_for_status()

            # Permanent 4xx or unexpected status codes
            response.raise_for_status()

            data = response.json()
            choices = data.get("choices", [])
            if not choices:
                LLM_ERRORS.inc()
                raise LLMClientError("LLM returned no choices")

            content = choices[0].get("message", {}).get("content")
            if not isinstance(content, str) or not content.strip():
                LLM_ERRORS.inc()
                raise LLMClientError("LLM returned an empty answer")

            # Record token usage metrics if available
            usage = data.get("usage") or {}
            if pt := usage.get("prompt_tokens"):
                LLM_TOKENS_TOTAL.labels(kind="prompt").inc(pt)
            if ct := usage.get("completion_tokens"):
                LLM_TOKENS_TOTAL.labels(kind="completion").inc(ct)

            if return_usage:
                return content.strip(), usage
            return content.strip()

        except (requests.Timeout, requests.ConnectionError) as exc:
            last_exception = exc
            logger.warning(
                "llm_network_timeout",
                error_type=type(exc).__name__,
                attempt=attempt + 1,
                max_retries=max_retries,
            )
            if attempt < max_retries - 1:
                sleep_time = initial_backoff_sec * (2 ** attempt)
                time.sleep(sleep_time)
                continue
            break

        except requests.HTTPError as exc:
            last_exception = exc
            status = exc.response.status_code if exc.response is not None else None
            # Do not retry non-transient 4xx client errors
            if status and 400 <= status < 500 and status != 429:
                LLM_ERRORS.inc()
                logger.error(
                    "llm_client_permanent_error",
                    status_code=status,
                )
                raise LLMClientError(f"Permanent LLM client error: HTTP {status}") from exc
            if attempt >= max_retries - 1:
                break

        except Exception as exc:
            last_exception = exc
            LLM_ERRORS.inc()
            logger.exception("llm_unexpected_error", error=str(exc))
            raise LLMClientError(f"Unexpected LLM error: {exc}") from exc

    LLM_ERRORS.inc()
    raise LLMClientError(
        f"LLM request failed after {max_retries} attempts: {last_exception}"
    ) from last_exception
