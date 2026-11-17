"""Root URL routing for Django backend, Djoser auth, domain apps, and Vue portal."""

import mimetypes
from pathlib import Path
import re
from django.contrib import admin
from django.conf import settings
from django.http import Http404, HttpResponse, StreamingHttpResponse
from django.urls import include, path, re_path
from django.views.generic.base import RedirectView
from django.views.static import serve as django_serve

from api.views import ApiRootIndexView, PortalHomeView, api_root_router

def ranged_media_serve(request, path, document_root=None):
    """Serve media artifacts with HTTP 206 Partial Content (byte-range) support for HTML5 video."""
    root = Path(document_root or settings.MEDIA_ROOT).resolve()
    file_path = (root / path).resolve()
    if not str(file_path).startswith(str(root)) or not file_path.is_file():
        raise Http404("Media file not found")

    content_type, _ = mimetypes.guess_type(str(file_path))
    content_type = content_type or "application/octet-stream"
    size = file_path.stat().st_size
    range_header = request.META.get("HTTP_RANGE")

    if not range_header:
        resp = django_serve(request, path, document_root=str(root))
        resp["Accept-Ranges"] = "bytes"
        return resp

    match = re.match(r"^bytes=(\d+)-(\d*)$", range_header.strip())
    if not match:
        resp = HttpResponse(status=416)
        resp["Content-Range"] = f"bytes */{size}"
        resp["Accept-Ranges"] = "bytes"
        return resp

    start = int(match.group(1))
    end = int(match.group(2)) if match.group(2) else size - 1
    if start >= size:
        resp = HttpResponse(status=416)
        resp["Content-Range"] = f"bytes */{size}"
        resp["Accept-Ranges"] = "bytes"
        return resp

    end = min(end, size - 1)
    chunk_len = end - start + 1

    def _stream_chunk(pos: int, remaining: int, buffer_size: int = 65536):
        with open(file_path, "rb") as fh:
            fh.seek(pos)
            while remaining > 0:
                to_read = min(buffer_size, remaining)
                data = fh.read(to_read)
                if not data:
                    break
                remaining -= len(data)
                yield data

    resp = StreamingHttpResponse(_stream_chunk(start, chunk_len), status=206, content_type=content_type)
    resp["Content-Range"] = f"bytes {start}-{end}/{size}"
    resp["Content-Length"] = str(chunk_len)
    resp["Accept-Ranges"] = "bytes"
    return resp

def _portal_patterns(prefix: str = "", name_prefix: str = "portal", *, include_root: bool = True) -> list:
    """Build Django portal deep-link URL patterns under an optional prefix (e.g. '' or 'control/')."""
    p = prefix.lstrip("/")
    routes = []
    if include_root:
        routes.append(path(f"{p}", PortalHomeView.as_view(), {"section": "overview"}, name=f"{name_prefix}-home"))
    routes.extend([
        path(f"{p}overview/", PortalHomeView.as_view(), {"section": "overview"}, name=f"{name_prefix}-overview"),
        path(f"{p}studio/", PortalHomeView.as_view(), {"section": "studio"}, name=f"{name_prefix}-studio"),
        path(f"{p}studio/<slug:task>/", PortalHomeView.as_view(), {"section": "studio"}, name=f"{name_prefix}-studio-task"),
        path(f"{p}settings/", PortalHomeView.as_view(), {"section": "settings"}, name=f"{name_prefix}-settings"),
        path(f"{p}settings/<slug:tab>/", PortalHomeView.as_view(), {"section": "settings"}, name=f"{name_prefix}-settings-tab"),
        path(f"{p}billing/", PortalHomeView.as_view(), {"section": "settings", "tab": "billing"}, name=f"{name_prefix}-billing"),
        path(f"{p}keys/", PortalHomeView.as_view(), {"section": "settings", "tab": "keys"}, name=f"{name_prefix}-keys"),
        path(f"{p}api-keys/", PortalHomeView.as_view(), {"section": "settings", "tab": "keys"}, name=f"{name_prefix}-api-keys"),
        path(f"{p}agents/", PortalHomeView.as_view(), {"section": "settings", "tab": "agents"}, name=f"{name_prefix}-agents"),
        path(f"{p}profiles/", PortalHomeView.as_view(), {"section": "settings", "tab": "profiles"}, name=f"{name_prefix}-profiles"),
        path(f"{p}transactions/", PortalHomeView.as_view(), {"section": "settings", "tab": "transactions"}, name=f"{name_prefix}-transactions"),
        path(f"{p}users/", PortalHomeView.as_view(), {"section": "admin", "admin_tab": "users"}, name=f"{name_prefix}-users"),
        path(f"{p}mfs/", PortalHomeView.as_view(), {"section": "admin", "admin_tab": "mfs"}, name=f"{name_prefix}-mfs"),
        path(f"{p}invoices/", PortalHomeView.as_view(), {"section": "admin", "admin_tab": "invoices"}, name=f"{name_prefix}-invoices"),
        path(f"{p}billings/", PortalHomeView.as_view(), {"section": "admin", "admin_tab": "invoices"}, name=f"{name_prefix}-billings"),
        path(f"{p}admin-transactions/", PortalHomeView.as_view(), {"section": "admin", "admin_tab": "transactions"}, name=f"{name_prefix}-admin-transactions"),
        path(f"{p}admin-control/", PortalHomeView.as_view(), {"section": "admin", "admin_tab": "mfs"}, name=f"{name_prefix}-admin-control"),
        path(f"{p}training/", PortalHomeView.as_view(), {"section": "training"}, name=f"{name_prefix}-training"),
    ])
    if p:
        routes.extend([
            path(f"{p}admin/", PortalHomeView.as_view(), {"section": "admin", "admin_tab": "mfs"}, name=f"{name_prefix}-admin"),
            path(f"{p}admin/<slug:admin_tab>/", PortalHomeView.as_view(), {"section": "admin"}, name=f"{name_prefix}-admin-tab"),
        ])
    return routes


urlpatterns = [
    # Top-level API Root Router (DRF interactive browseable API & JSON directory)
    re_path(r"^api/?$", api_root_router, name="api-root"),
    path("api/", api_root_router, name="api-root-slash"),
    path("favicon.ico", RedirectView.as_view(url="/static/img/tblinc-ai-icon.svg", permanent=False)),
    # Django Admin site (must be before portal root patterns)
    path("admin/", admin.site.urls),
    # Root `/` serves Login & Sign Up auth gateway (redirects to /control/ once authenticated)
    path("", PortalHomeView.as_view(), {"section": "auth", "mode": "login"}, name="portal-home"),
    path("login/", PortalHomeView.as_view(), {"section": "auth", "mode": "login"}, name="portal-login"),
    path("register/", PortalHomeView.as_view(), {"section": "auth", "mode": "register"}, name="portal-register"),
    # Django Portal URL routes (root subpaths + /control/ prefix)
    *_portal_patterns("", "portal", include_root=False),
    *_portal_patterns("control/", "portal-control"),
    # Djoser auth + JWT endpoints
    path("api/auth/", include("djoser.urls")),
    path("api/auth/", include("djoser.urls.jwt")),
    # Domain REST apps
    path("api/billing/", include("billing.urls")),
    path("api/transactions/", include("transactions.urls")),
    path("api/quota/", include("quota.urls")),
    path("api/agent/", include("Agent.urls")),
    # FastAPI gateway & portal dashboard
    path("api/v1/", include("api.urls")),
    # Media artifacts serving (generated images/videos with byte-range streaming)
    re_path(r"^media/generated/(?P<path>.*)$", ranged_media_serve, {"document_root": settings.MEDIA_ROOT}),
    re_path(r"^media/(?P<path>.*)$", ranged_media_serve, {"document_root": settings.MEDIA_ROOT}),
]

