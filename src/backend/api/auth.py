"""Custom DRF authentication supporting user-generated API Secret Keys."""

from __future__ import annotations

from django.utils import timezone
from rest_framework import authentication, exceptions

from .models import SecretKey


class SecretKeyAuthentication(authentication.BaseAuthentication):
    """Authenticate requests via `X-Secret-Key` or `Authorization: Bearer sk_tblinc_...`."""

    def authenticate(self, request):
        raw_key = self._extract_secret_key(request)
        if not raw_key:
            return None

        key_hash = SecretKey.hash_secret(raw_key)
        secret_obj = SecretKey.objects.select_related("user").filter(key_hash=key_hash, is_active=True).first()
        if secret_obj is None or not secret_obj.user.is_active:
            raise exceptions.AuthenticationFailed("Invalid or revoked secret key.")

        SecretKey.objects.filter(pk=secret_obj.pk).update(last_used_at=timezone.now())
        return (secret_obj.user, secret_obj)

    def _extract_secret_key(self, request) -> str | None:
        header_key = (
            request.headers.get("X-API-Key")
            or request.headers.get("X-Secret-Key")
            or ""
        ).strip()
        if header_key:
            return header_key
        auth_header = (request.headers.get("Authorization") or "").strip()
        if auth_header.lower().startswith("bearer "):
            token = auth_header[7:].strip()
            if token.startswith(SecretKey.SECRET_PREFIX):
                return token
        return None

