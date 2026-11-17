"""URL routes for the Agent app."""

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import AgentProfileViewSet, AgentRunListView, ExecuteAgentView

router = DefaultRouter()
router.register("profiles", AgentProfileViewSet, basename="agent-profile")

urlpatterns = [
    path("runs/", AgentRunListView.as_view(), name="agent-runs"),
    path("execute/", ExecuteAgentView.as_view(), name="agent-execute"),
    path("", include(router.urls)),
]

