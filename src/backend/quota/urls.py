"""URL routes for quota app."""

from django.urls import path

from .views import ConsumeQuotaView, MyQuotaView, QuotaLogsView

urlpatterns = [
    path("me/", MyQuotaView.as_view(), name="quota-me"),
    path("consume/", ConsumeQuotaView.as_view(), name="quota-consume"),
    path("logs/", QuotaLogsView.as_view(), name="quota-logs"),
]

