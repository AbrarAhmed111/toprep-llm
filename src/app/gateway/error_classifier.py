"""
Error Classifier for LLM Gateway Fallback.
Maps HTTP exception status codes and provider error strings into actionable recovery decisions.
"""

from typing import Tuple


class ErrorClassifier:
    """Classifies provider exceptions into retryable vs non-retryable categories."""

    @staticmethod
    def is_retryable(error: Exception) -> Tuple[bool, str]:
        """
        Determines if an error should trigger failover to another deployment.

        Returns:
            (is_retryable, reason_code)
        """
        err_msg = str(error).lower()

        # Check for 404 model or endpoint not found (decommissioned model / deprecated endpoint)
        if "404" in err_msg or "not found" in err_msg or "model_not_found" in err_msg:
            return True, "model_or_endpoint_not_found"

        # Check for retryable rate-limits and quotas
        if "429" in err_msg or "rate limit" in err_msg or "quota" in err_msg or "resource exhausted" in err_msg:
            return True, "rate_limit_or_quota"

        # Check for server-side provider failures
        if any(code in err_msg for code in ["500", "502", "503", "504", "internal server error", "service unavailable"]):
            return True, "provider_server_error"

        # Check for network & timeout transient failures
        if any(term in err_msg for term in ["timeout", "timed out", "connection reset", "connection refused", "network error", "connecterror"]):
            return True, "network_or_timeout"

        # Check for authentication errors (invalid API key)
        if "401" in err_msg or "unauthorized" in err_msg or "invalid api key" in err_msg or "authentication" in err_msg:
            return False, "invalid_api_key"

        # Client syntax or invalid parameter errors (400)
        if "400" in err_msg or "bad request" in err_msg or "invalid_request_error" in err_msg:
            return False, "bad_request"

        # Default fallback: Treat unknown errors as potentially recoverable via another provider
        return True, "unknown_error"
