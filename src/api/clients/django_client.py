"""Async httpx bridge between FastAPI inference service and Django control plane."""

from __future__ import annotations

import httpx


class QuotaDeductionError(Exception):
    """Raised when Django rejects an operation due to insufficient quota."""

    def __init__(self, status_code: int, detail: str) -> None:
        super().__init__(detail)
        self.status_code = status_code
        self.detail = detail


class DjangoClient:
    """Async httpx client handling user quota verification and transaction sync."""

    def __init__(
        self,
        base_url: str,
        internal_api_key: str,
        timeout: float = 10.0,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.internal_api_key = internal_api_key
        self._client = httpx.AsyncClient(base_url=self.base_url, timeout=timeout)

    async def close(self) -> None:
        """Close the underlying httpx connection pool."""
        await self._client.aclose()

    async def consume_quota(
        self,
        authorization: str | None,
        credits: int,
        model_tier: str,
        task_type: str,
        endpoint: str,
        latency_ms: float = 0.0,
        api_key: str | None = None,
    ) -> dict[str, object] | None:
        """Charge user quota via Django when a Bearer token or API Key is supplied."""
        if not authorization and not api_key:
            return None
        headers = {
            "X-Internal-Key": self.internal_api_key,
        }
        if authorization:
            headers["Authorization"] = authorization
        if api_key:
            headers["X-API-Key"] = api_key
        payload = {
            "credits": credits,
            "model_tier": model_tier,
            "task_type": task_type,
            "endpoint": endpoint,
            "latency_ms": latency_ms,
        }
        try:
            response = await self._client.post("/api/quota/consume/", json=payload, headers=headers)
        except httpx.HTTPError:
            # Allow standalone inference if Django control plane is offline
            return None

        if response.status_code in (401, 402, 403, 429):
            detail = response.json().get("detail", "Quota or auth check failed.")
            raise QuotaDeductionError(status_code=response.status_code, detail=str(detail))
        if response.is_success:
            return response.json()
        return None

