"""Shared httpx client bridge connecting Django backend to FastAPI inference service."""

from __future__ import annotations

from typing import Any
import httpx
from django.conf import settings


class FastAPIBridgeError(Exception):
    """Raised when the FastAPI service returns an error or is unreachable."""

    def __init__(self, status_code: int, detail: str) -> None:
        super().__init__(detail)
        self.status_code = status_code
        self.detail = detail


class FastAPIBridge:
    """Synchronous httpx gateway helper used by Django views and Agent runner."""

    def __init__(self, base_url: str | None = None, timeout: float = 30.0) -> None:
        self.base_url = (base_url or settings.FASTAPI_BASE_URL).rstrip("/")
        self.timeout = timeout

    def _headers(self, auth_header: str | None = None) -> dict[str, str]:
        headers = {"X-Internal-Key": settings.INTERNAL_API_KEY}
        if auth_header:
            headers["Authorization"] = auth_header
        return headers

    def get_json(self, path: str, auth_header: str | None = None) -> Any:
        """Perform a GET request against FastAPI and return parsed JSON."""
        url = f"{self.base_url}{path}"
        try:
            with httpx.Client(timeout=self.timeout) as client:
                res = client.get(url, headers=self._headers(auth_header))
        except httpx.HTTPError as exc:
            raise FastAPIBridgeError(503, f"FastAPI service unavailable: {exc}") from exc

        if not res.is_success:
            raise FastAPIBridgeError(res.status_code, res.text)
        return res.json()

    def post_json(
        self,
        path: str,
        payload: dict[str, Any],
        auth_header: str | None = None,
    ) -> Any:
        """Perform a POST request against FastAPI and return parsed JSON."""
        url = f"{self.base_url}{path}"
        try:
            with httpx.Client(timeout=self.timeout) as client:
                res = client.post(url, json=payload, headers=self._headers(auth_header))
        except httpx.HTTPError as exc:
            raise FastAPIBridgeError(503, f"FastAPI service unavailable: {exc}") from exc

        if not res.is_success:
            try:
                detail = res.json().get("detail", res.text)
            except ValueError:
                detail = res.text
            raise FastAPIBridgeError(res.status_code, str(detail))
        return res.json()

